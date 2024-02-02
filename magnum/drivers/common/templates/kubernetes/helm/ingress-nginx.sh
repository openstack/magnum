set +x
. /etc/sysconfig/heat-params
set -ex

CHART_NAME="ingress-nginx"

if [ "$(echo ${INGRESS_CONTROLLER} | tr '[:upper:]' '[:lower:]')" = "nginx" ]; then
    echo "Writing ${CHART_NAME} config"

    HELM_CHART_DIR="/srv/magnum/kubernetes/helm/magnum"
    mkdir -p ${HELM_CHART_DIR}

    cat << EOF >> ${HELM_CHART_DIR}/requirements.yaml
- name: ${CHART_NAME}
  version: ${NGINX_INGRESS_CONTROLLER_CHART_TAG}
  repository: https://kubernetes.github.io/ingress-nginx
EOF

    cat << EOF >> ${HELM_CHART_DIR}/values.yaml
nginx-ingress:
  controller:
    name: controller
    image:
      repository: ${CONTAINER_INFRA_PREFIX:-quay.io/kubernetes-ingress-controller/}nginx-ingress-controller
      tag: ${NGINX_INGRESS_CONTROLLER_TAG}
      pullPolicy: IfNotPresent
    config: {}
    headers: {}
    hostNetwork: true
    dnsPolicy: ClusterFirst
    daemonset:
      useHostPort: true
      hostPorts:
        http: 80
        https: 443
        stats: 18080
    defaultBackendService: ""
    electionID: ingress-controller-leader
    ingressClass: nginx
    podLabels: {}
    publishService:
      enabled: false
      pathOverride: ""
    scope:
      enabled: false
      namespace: ""   # defaults to .Release.Namespace
    extraArgs:
      enable-ssl-passthrough: ""
    extraEnvs: []
    kind: DaemonSet
    updateStrategy: {}
    minReadySeconds: 0
    tolerations: []
    affinity: {}
    nodeSelector:
      role: ${INGRESS_CONTROLLER_ROLE}
    livenessProbe:
      failureThreshold: 3
      initialDelaySeconds: 10
      periodSeconds: 10
      successThreshold: 1
      timeoutSeconds: 1
      port: 10254
    readinessProbe:
      failureThreshold: 3
      initialDelaySeconds: 10
      periodSeconds: 10
      successThreshold: 1
      timeoutSeconds: 1
      port: 10254
    podAnnotations: {}
    replicaCount: 1
    minAvailable: 1
    resources:
      requests:
        cpu: 200m
        memory: 256Mi
    autoscaling:
      enabled: false
    customTemplate:
      configMapName: ""
      configMapKey: ""
    service:
      annotations: {}
      labels: {}
      clusterIP: ""
      externalIPs: []
      loadBalancerIP: ""
      loadBalancerSourceRanges: []
      enableHttp: true
      enableHttps: true
      externalTrafficPolicy: ""
      healthCheckNodePort: 0
      targetPorts:
        http: http
        https: https
      type: NodePort
      nodePorts:
        http: "32080"
        https: "32443"
    extraContainers: []
    extraVolumeMounts: []
    extraVolumes: []
    extraInitContainers: []
    stats:
      enabled: false
      service:
        annotations: {}
        clusterIP: ""
        externalIPs: []
        loadBalancerIP: ""
        loadBalancerSourceRanges: []
        servicePort: 18080
        type: ClusterIP
    metrics:
      enabled: ${MONITORING_ENABLED}
      service:
        annotations: {}
        clusterIP: ""
        externalIPs: []
        loadBalancerIP: ""
        loadBalancerSourceRanges: []
        servicePort: 9913
        type: ClusterIP
      serviceMonitor:
        enabled: ${MONITORING_ENABLED}
        namespace: kube-system
    lifecycle: {}
    priorityClassName: "system-node-critical"
  revisionHistoryLimit: 10
  defaultBackend:
    enabled: true
    name: default-backend
    image:
      repository: ${CONTAINER_INFRA_PREFIX:-k8s.gcr.io/}defaultbackend
      tag: "1.4"
      pullPolicy: IfNotPresent
    extraArgs: {}
    port: 8080
    tolerations: []
    affinity: {}
    podLabels: {}
    nodeSelector: {}
    podAnnotations: {}
    replicaCount: 1
    minAvailable: 1
    resources:
      requests:
        cpu: 10m
        memory: 20Mi
    service:
      annotations: {}
      clusterIP: ""
      externalIPs: []
      loadBalancerIP: ""
      loadBalancerSourceRanges: []
      servicePort: 80
      type: ClusterIP
    priorityClassName: "system-cluster-critical"
  rbac:
    create: true
  podSecurityPolicy:
    enabled: false
  serviceAccount:
    create: true
    name:
  imagePullSecrets: []
  tcp: {}
  udp: {}
EOF
fi
