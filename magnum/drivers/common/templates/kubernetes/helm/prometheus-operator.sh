set +x
. /etc/sysconfig/heat-params
set -ex

CHART_NAME="prometheus-operator"

if [ "$(echo ${MONITORING_ENABLED} | tr '[:upper:]' '[:lower:]')" = "true" ]; then
    echo "Writing ${CHART_NAME} config"

    HELM_CHART_DIR="/srv/magnum/kubernetes/helm/magnum"
    mkdir -p ${HELM_CHART_DIR}

    cat << EOF >> ${HELM_CHART_DIR}/requirements.yaml
- name: ${CHART_NAME}
  version: ${PROMETHEUS_OPERATOR_CHART_TAG}
  repository: https://prometheus-community.github.io/helm-charts
EOF

    # Calculate resources needed to run the Prometheus Monitoring Solution
    # MAX_NODE_COUNT so we can have metrics even if cluster scales
    PROMETHEUS_SERVER_CPU=$(expr 128 + 7 \* ${MAX_NODE_COUNT} )
    PROMETHEUS_SERVER_RAM=$(expr 256 + 40 \* ${MAX_NODE_COUNT})

    # Because the PVC and Prometheus use different scales for the volume size
    # conversion is needed. The prometheus-monitoring value (in GB) is the conversion
    # with a ratio of (1 GiB = 1.073741824 GB) and then rounded to int

    MONITORING_RETENTION_SIZE_GB=$(echo | awk "{print int(${MONITORING_RETENTION_SIZE}*1.073741824)}")
    APP_GRAFANA_PERSISTENT_STORAGE="false"
    if [ "${MONITORING_STORAGE_CLASS_NAME}" != "" ]; then
        APP_GRAFANA_PERSISTENT_STORAGE="true"
    fi

    # Create services for grafana/prometheus/alermanager
    APP_INGRESS_PATH_APPEND=""
    APP_INGRESS_ANNOTATIONS=""
    APP_INGRESS_ROUTE_ANNOTATIONS=""
    APP_INGRESS_BASIC_AUTH_ANNOTATIONS=""
    if [ "${INGRESS_CONTROLLER}" == "nginx" ]; then
        APP_INGRESS_PATH_APPEND="(/|$)(.*)"
        APP_INGRESS_ANNOTATIONS=$(cat << EOF
        nginx.ingress.kubernetes.io/ssl-redirect: "true"
        nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
EOF
        )
        APP_INGRESS_ROUTE_ANNOTATIONS=$(cat << 'EOF'
        nginx.ingress.kubernetes.io/rewrite-target: /$2
EOF
        )
        if [ "${CLUSTER_BASIC_AUTH_SECRET}" != "" ]; then
            APP_INGRESS_BASIC_AUTH_ANNOTATIONS=$(cat << EOF
        nginx.ingress.kubernetes.io/auth-type: basic
        nginx.ingress.kubernetes.io/auth-secret: ${CLUSTER_BASIC_AUTH_SECRET}
EOF
            )
        fi #END BASIC AUTH
    elif [ "${INGRESS_CONTROLLER}" == "traefik" ]; then
        APP_INGRESS_ANNOTATIONS=$(cat << EOF
        traefik.ingress.kubernetes.io/frontend-entry-points: https
        traefik.ingress.kubernetes.io/protocol: http
EOF
        )
        APP_INGRESS_ROUTE_ANNOTATIONS=$(cat << EOF
        traefik.ingress.kubernetes.io/rule-type: PathPrefixStrip
EOF
        )
        if [ "${CLUSTER_BASIC_AUTH_SECRET}" != "" ]; then
            APP_INGRESS_BASIC_AUTH_ANNOTATIONS=$(cat << EOF
        ingress.kubernetes.io/auth-type: basic
        ingress.kubernetes.io/auth-secret: ${CLUSTER_BASIC_AUTH_SECRET}
EOF
            )
        fi #END BASIC AUTH
    fi

    # Validate if communication node <-> master is secure or insecure
    PROTOCOL="https"
    INSECURE_SKIP_VERIFY="False"
    if [ "$TLS_DISABLED" = "True" ]; then
        PROTOCOL="http"
        INSECURE_SKIP_VERIFY="True"
    fi
    # FIXME: Force protocol to http as we don't want to use the cluster certs
    USE_HTTPS="False"

    if [ "$(echo ${VERIFY_CA} | tr '[:upper:]' '[:lower:]')" == "false" ]; then
        INSECURE_SKIP_VERIFY="True"
    fi

    cat << EOF >> ${HELM_CHART_DIR}/values.yaml
prometheus-operator:

  defaultRules:
    rules:
      #TODO: To enable this we need firstly take care of exposing certs
      etcd: false

  alertmanager:
    ingress:
      enabled: ${MONITORING_INGRESS_ENABLED}
      annotations:
        kubernetes.io/ingress.class: ${INGRESS_CONTROLLER}
${APP_INGRESS_ANNOTATIONS}
${APP_INGRESS_ROUTE_ANNOTATIONS}
${APP_INGRESS_BASIC_AUTH_ANNOTATIONS}
      ## Hosts must be provided if Ingress is enabled.
      hosts:
      - ${CLUSTER_ROOT_DOMAIN_NAME}
      paths:
      - /alertmanager${APP_INGRESS_PATH_APPEND}
      ## TLS configuration for Alertmanager Ingress
      ## Secret must be manually created in the namespace
      tls: []
      # - secretName: alertmanager-general-tls
      #   hosts:
      #   - alertmanager.example.com
    alertmanagerSpec:
      image:
        repository: ${CONTAINER_INFRA_PREFIX:-quay.io/prometheus/}alertmanager
      logFormat: json
      externalUrl: https://${CLUSTER_ROOT_DOMAIN_NAME}/alertmanager
      # routePrefix: /alertmanager
      # resources:
      #   requests:
      #     cpu: 100m
      #     memory: 256Mi
      priorityClassName: "system-cluster-critical"

  grafana:
    image:
      repository: ${CONTAINER_INFRA_PREFIX:-grafana/}grafana
    #enabled: ${ENABLE_GRAFANA}
    sidecar:
      image: ${CONTAINER_INFRA_PREFIX:-kiwigrid/}k8s-sidecar:0.1.99
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
    adminPassword: ${GRAFANA_ADMIN_PASSWD}
    ingress:
      enabled: ${MONITORING_INGRESS_ENABLED}
      annotations:
        kubernetes.io/ingress.class: ${INGRESS_CONTROLLER}
${APP_INGRESS_ANNOTATIONS}
      ## Hostnames.
      ## Must be provided if Ingress is enable.
      hosts:
      - ${CLUSTER_ROOT_DOMAIN_NAME}
      path: /grafana${APP_INGRESS_PATH_APPEND}
      ## TLS configuration for grafana Ingress
      ## Secret must be manually created in the namespace
      tls: []
      # - secretName: grafana-general-tls
      #   hosts:
      #   - grafana.example.com
    persistence:
      enabled: ${APP_GRAFANA_PERSISTENT_STORAGE}
      storageClassName: ${MONITORING_STORAGE_CLASS_NAME}
      size: 1Gi
    grafana.ini:
      server:
        domain: ${CLUSTER_ROOT_DOMAIN_NAME}
        root_url: https://${CLUSTER_ROOT_DOMAIN_NAME}/grafana
        serve_from_sub_path: true
      paths:
        data: /var/lib/grafana/data
        logs: /var/log/grafana
        plugins: /var/lib/grafana/plugins
        provisioning: /etc/grafana/provisioning
      analytics:
        check_for_updates: true
      log:
        mode: console
      log.console:
        format: json
      grafana_net:
        url: https://grafana.net
    plugins:
    - grafana-piechart-panel

  kubeApiServer:
    tlsConfig:
      insecureSkipVerify: "False"

  kubelet:
    serviceMonitor:
      https: "True"

  kubeControllerManager:
    ## If your kube controller manager is not deployed as a pod, specify IPs it can be found on
    endpoints: ${KUBE_MASTERS_PRIVATE}
    ## If using kubeControllerManager.endpoints only the port and targetPort are used
    service:
      port: 10252
      targetPort: 10252
      # selector:
      #   component: kube-controller-manager
    serviceMonitor:
      ## Enable scraping kube-controller-manager over https.
      ## Requires proper certs (not self-signed) and delegated authentication/authorization checks
      https: ${USE_HTTPS}
      # Skip TLS certificate validation when scraping
      insecureSkipVerify: null
      # Name of the server to use when validating TLS certificate
      serverName: null

  coreDns:
    enabled: true
    service:
      port: 9153
      targetPort: 9153
      selector:
        k8s-app: kube-dns

  kubeEtcd:
    ## If your etcd is not deployed as a pod, specify IPs it can be found on
    endpoints: ${KUBE_MASTERS_PRIVATE}
    ## Etcd service. If using kubeEtcd.endpoints only the port and targetPort are used
    service:
      port: 2379
      targetPort: 2379
      # selector:
      #   component: etcd
    ## Configure secure access to the etcd cluster by loading a secret into prometheus and
    ## specifying security configuration below. For example, with a secret named etcd-client-cert
    serviceMonitor:
      scheme: https
      insecureSkipVerify: true
      caFile: /etc/prometheus/secrets/etcd-certificates/ca.crt
      certFile: /etc/prometheus/secrets/etcd-certificates/kubelet.crt
      keyFile: /etc/prometheus/secrets/etcd-certificates/kubelet.key

  kubeScheduler:
    ## If your kube scheduler is not deployed as a pod, specify IPs it can be found on
    endpoints: ${KUBE_MASTERS_PRIVATE}
    ## If using kubeScheduler.endpoints only the port and targetPort are used
    service:
      port: 10251
      targetPort: 10251
      # selector:
      #   component: kube-scheduler
    serviceMonitor:
      ## Enable scraping kube-scheduler over https.
      ## Requires proper certs (not self-signed) and delegated authentication/authorization checks
      https: ${USE_HTTPS}
      ## Skip TLS certificate validation when scraping
      insecureSkipVerify: null
      ## Name of the server to use when validating TLS certificate
      serverName: null

  # kubeProxy:
  #   ## If your kube proxy is not deployed as a pod, specify IPs it can be found on
  #   endpoints: [] # masters + minions
  #   serviceMonitor:
  #     ## Enable scraping kube-proxy over https.
  #     ## Requires proper certs (not self-signed) and delegated authentication/authorization checks
  #     https: ${USE_HTTPS}

  kube-state-metrics:
    priorityClassName: "system-cluster-critical"
    resources:
      #Guaranteed
      limits:
        cpu: 50m
        memory: 64M

  prometheus-node-exporter:
    priorityClassName: "system-node-critical"
    resources:
      #Guaranteed
      limits:
        cpu: 20m
        memory: 20M
    extraArgs:
      - --collector.filesystem.ignored-mount-points=^/(dev|proc|sys|var/lib/docker/.+)($|/)
      - --collector.filesystem.ignored-fs-types=^(autofs|binfmt_misc|cgroup|configfs|debugfs|devpts|devtmpfs|fusectl|hugetlbfs|mqueue|overlay|proc|procfs|pstore|rpc_pipefs|securityfs|sysfs|tracefs)$
    sidecars: []
    ##  - name: nvidia-dcgm-exporter
    ##    image: nvidia/dcgm-exporter:1.4.3

  prometheusOperator:
    priorityClassName: "system-cluster-critical"
    tlsProxy:
      image:
        repository: ${CONTAINER_INFRA_PREFIX:-squareup/}ghostunnel
    admissionWebhooks:
      patch:
        image:
          repository: ${CONTAINER_INFRA_PREFIX:-jettech/}kube-webhook-certgen
        priorityClassName: "system-cluster-critical"

    resources: {}
    # requests:
    #   cpu: 5m
    #   memory: 10Mi
    logFormat: json
    image:
      repository: ${CONTAINER_INFRA_PREFIX:-quay.io/coreos/}prometheus-operator
    configmapReloadImage:
      repository: ${CONTAINER_INFRA_PREFIX:-quay.io/coreos/}configmap-reload
    prometheusConfigReloaderImage:
      repository: ${CONTAINER_INFRA_PREFIX:-quay.io/coreos/}prometheus-config-reloader
    hyperkubeImage:
      repository: ${CONTAINER_INFRA_PREFIX:-k8s.gcr.io/}hyperkube

  prometheus:
    ingress:
      enabled: ${MONITORING_INGRESS_ENABLED}
      annotations:
        kubernetes.io/ingress.class: ${INGRESS_CONTROLLER}
${APP_INGRESS_ANNOTATIONS}
${APP_INGRESS_ROUTE_ANNOTATIONS}
${APP_INGRESS_BASIC_AUTH_ANNOTATIONS}
      ## Hostnames.
      ## Must be provided if Ingress is enabled.
      hosts:
      - ${CLUSTER_ROOT_DOMAIN_NAME}
      paths:
      - /prometheus${APP_INGRESS_PATH_APPEND}
      ## TLS configuration for Prometheus Ingress
      ## Secret must be manually created in the namespace
      tls: []
        # - secretName: prometheus-general-tls
        #   hosts:
        #     - prometheus.example.com
    serviceMonitor:
      ## scheme: HTTP scheme to use for scraping. Can be used with tlsConfig for example if using istio mTLS.
      scheme: ""
      ## tlsConfig: TLS configuration to use when scraping the endpoint. For example if using istio mTLS.
      ## Of type: https://github.com/coreos/prometheus-operator/blob/master/Documentation/api.md#tlsconfig
      tlsConfig: {}
      bearerTokenFile:
    prometheusSpec:
      scrapeInterval: ${MONITORING_INTERVAL_SECONDS}s
      scrapeInterval: 30s
      evaluationInterval: 30s
      image:
        repository: ${CONTAINER_INFRA_PREFIX:-quay.io/prometheus/}prometheus
      retention: 14d
      externalLabels:
        cluster_uuid: ${CLUSTER_UUID}
      externalUrl: https://${CLUSTER_ROOT_DOMAIN_NAME}/prometheus
      ## Secrets is a list of Secrets in the same namespace as the Prometheus object, which shall be mounted into the Prometheus Pods.
      ## The Secrets are mounted into /etc/prometheus/secrets/. Secrets changes after initial creation of a Prometheus object are not
      ## reflected in the running Pods. To change the secrets mounted into the Prometheus Pods, the object must be deleted and recreated
      ## with the new list of secrets.
      # secrets:
      # - etcd-certificates
      # - kube-controller-manager-certificates
      # - kube-scheduler-certificates
      # - kube-proxy-manager-certificates
      retention: ${MONITORING_RETENTION_DAYS}d
      retentionSize: ${MONITORING_RETENTION_SIZE_GB}GB
      logFormat: json
      #routePrefix: /prometheus
      resources:
        requests:
          cpu: ${PROMETHEUS_SERVER_CPU}m
          memory: ${PROMETHEUS_SERVER_RAM}M
      priorityClassName: "system-cluster-critical"
EOF

    #######################
    # Set up definitions for persistent storage using k8s storageClass
    if [ "${MONITORING_STORAGE_CLASS_NAME}" != "" ]; then
        cat << EOF >> ${HELM_CHART_DIR}/values.yaml
      storageSpec:
        volumeClaimTemplate:
          spec:
            storageClassName: ${MONITORING_STORAGE_CLASS_NAME}
            accessModes: ["ReadWriteMany"]
            resources:
              requests:
                storage: ${MONITORING_RETENTION_SIZE}Gi
EOF
    fi #END PERSISTENT STORAGE CONFIG

    #######################
    # Set up definitions for ingress objects

    # Ensure name conformity
    INGRESS_CONTROLLER=$(echo ${INGRESS_CONTROLLER} | tr '[:upper:]' '[:lower:]')
    if [ "${INGRESS_CONTROLLER}" == "nginx" ]; then
        :
    elif [ "${INGRESS_CONTROLLER}" == "traefik" ]; then
        cat << EOF >> ${HELM_CHART_DIR}/values.yaml
    additionalServiceMonitors:
    - name: prometheus-traefik-metrics
      selector:
        matchLabels:
          k8s-app: traefik
      namespaceSelector:
        matchNames:
        - kube-system
      endpoints:
      - path: /metrics
        port: metrics
EOF
    fi #END INGRESS

    if [ "$(echo ${AUTO_SCALING_ENABLED} | tr '[:upper:]' '[:lower:]')" == "true" ]; then
        cat << EOF >> ${HELM_CHART_DIR}/values.yaml
    additionalPodMonitors:
    - name: prometheus-cluster-autoscaler
      podMetricsEndpoints:
      - port: metrics
        scheme: http
      namespaceSelector:
        matchNames:
        - kube-system
      selector:
        matchLabels:
          app: cluster-autoscaler
EOF
    fi #END AUTOSCALING
fi
