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
  repository: https://charts.helm.sh/stable
EOF

    cat << EOF >> ${HELM_CHART_DIR}/values.yaml
metrics-server:
  image:
    repository: ${CONTAINER_INFRA_PREFIX:-gcr.io/google_containers/}metrics-server-${ARCH}
  args:
    - --kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname
EOF
fi
