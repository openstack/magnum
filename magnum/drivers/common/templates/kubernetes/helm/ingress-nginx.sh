#!/bin/bash

. /etc/sysconfig/heat-params

set -ex

step="nginx-ingress"
printf "Starting to run ${step}\n"

### Configuration
###############################################################################
CHART_NAME="nginx-ingress"

if [ "$(echo ${INGRESS_CONTROLLER} | tr '[:upper:]' '[:lower:]')" = "nginx" ]; then

HELM_MODULE_CONFIG_FILE="/srv/magnum/kubernetes/helm/${CHART_NAME}.yaml"
[ -f ${HELM_MODULE_CONFIG_FILE} ] || {
    echo "Writing File: ${HELM_MODULE_CONFIG_FILE}"
    mkdir -p $(dirname ${HELM_MODULE_CONFIG_FILE})
    cat << EOF > ${HELM_MODULE_CONFIG_FILE}
---
kind: ConfigMap
apiVersion: v1
metadata:
  name: ${CHART_NAME}-config
  namespace: magnum-tiller
  labels:
    app: helm
data:
  install-${CHART_NAME}.sh: |
    #!/bin/bash
    set -e
    set -x
    mkdir -p \${HELM_HOME}
    cp /etc/helm/* \${HELM_HOME}

    # HACK - Force wait because of bug https://github.com/helm/helm/issues/5170
    until helm init --client-only --wait
    do
        sleep 5s
    done
    helm repo update

    if [[ \$(helm history ${CHART_NAME} | grep ${CHART_NAME}) ]]; then
        echo "${CHART_NAME} already installed on server. Continue..."
        exit 0
    else
        helm install stable/${CHART_NAME} --namespace kube-system --name ${CHART_NAME} --version ${NGINX_INGRESS_CONTROLLER_CHART_TAG} --values /opt/magnum/install-${CHART_NAME}-values.yaml
    fi

  install-${CHART_NAME}-values.yaml:  |
    controller:
      name: controller
      image:
        repository: ${CONTAINER_INFRA_PREFIX:-quay.io/kubernetes-ingress-controller/}nginx-ingress-controller
        tag: ${NGINX_INGRESS_CONTROLLER_TAG}
        pullPolicy: IfNotPresent
        runAsUser: 33
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
          additionalLabels:
            release: prometheus-operator
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
---
apiVersion: batch/v1
kind: Job
metadata:
  name: install-${CHART_NAME}-job
  namespace: magnum-tiller
spec:
  backoffLimit: 10
  template:
    spec:
      serviceAccountName: tiller
      containers:
      - name: config-helm
        image: ${CONTAINER_INFRA_PREFIX:-docker.io/openstackmagnum/}helm-client:${HELM_CLIENT_TAG}
        command:
        - bash
        args:
        - /opt/magnum/install-${CHART_NAME}.sh
        env:
        - name: HELM_HOME
          value: /helm_home
        - name: TILLER_NAMESPACE
          value: magnum-tiller
        - name: HELM_TLS_ENABLE
          value: "true"
        volumeMounts:
        - name: install-${CHART_NAME}-config
          mountPath: /opt/magnum/
        - mountPath: /etc/helm
          name: helm-client-certs
      restartPolicy: Never
      volumes:
      - name: install-${CHART_NAME}-config
        configMap:
          name: ${CHART_NAME}-config
      - name: helm-client-certs
        secret:
          secretName: helm-client-secret
EOF
}
fi

printf "Finished running ${step}\n"
