set +x
. /etc/sysconfig/heat-params
set -ex

# This configuration depends on helm installed prometheus-operator.
CHART_NAME="prometheus-adapter"

if [ "$(echo ${MONITORING_ENABLED} | tr '[:upper:]' '[:lower:]')" = "true" ] && \
   [ "$(echo ${PROMETHEUS_ADAPTER_ENABLED} | tr '[:upper:]' '[:lower:]')" = "true" ]; then
    echo "Writing ${CHART_NAME} config"

    HELM_CHART_DIR="/srv/magnum/kubernetes/helm/magnum"
    mkdir -p ${HELM_CHART_DIR}

    cat << EOF >> ${HELM_CHART_DIR}/requirements.yaml
- name: ${CHART_NAME}
  version: ${PROMETHEUS_ADAPTER_CHART_TAG}
  repository: https://prometheus-community.github.io/helm-charts
EOF

    cat << EOF >> ${HELM_CHART_DIR}/values.yaml
prometheus-adapter:
  image:
    repository: ${CONTAINER_INFRA_PREFIX:-docker.io/directxman12/}k8s-prometheus-adapter-${ARCH}
  priorityClassName: "system-cluster-critical"
  prometheus:
    url: http://web.tcp.prometheus-prometheus.kube-system.svc.cluster.local
  resources:
    requests:
      cpu: 150m
      memory: 400Mi
  rules:
    existing: ${PROMETHEUS_ADAPTER_CONFIGMAP}
  # tls:
  #   enable: true
  #   ca: |-
  #     # Public CA file that signed the APIService
  #   key: |-
  #     # Private key of the APIService
  #   certificate: |-
  #     # Public key of the APIService
EOF
fi
