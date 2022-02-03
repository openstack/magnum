set +x
. /etc/sysconfig/heat-params
set -ex

CHART_NAME="metrics-server"

if [ "$(echo ${METRICS_SERVER_ENABLED} | tr '[:upper:]' '[:lower:]')" = "true" ]; then
    echo "Writing ${CHART_NAME} config"

    HELM_CHART_DIR="/srv/magnum/kubernetes/helm/magnum"
    mkdir -p ${HELM_CHART_DIR}

    cat << EOF >> ${HELM_CHART_DIR}/requirements.yaml
- name: ${CHART_NAME}
  version: ${METRICS_SERVER_CHART_TAG}
  repository: https://kubernetes-sigs.github.io/metrics-server/
EOF

    cat << EOF >> ${HELM_CHART_DIR}/values.yaml
metrics-server:
  image:
    repository: ${CONTAINER_INFRA_PREFIX:-k8s.gcr.io/metrics-server/}metrics-server
  resources:
    requests:
      cpu: 100m
      memory: 200Mi
  args:
    - --kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname
EOF
fi
