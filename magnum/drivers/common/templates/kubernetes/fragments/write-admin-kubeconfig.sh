#!/bin/sh

set +x
. /etc/sysconfig/heat-params
set -x

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

CERT_DIR=/etc/kubernetes/certs
BASH_RC_FILE=/etc/bashrc

# root kubeconfig
ADMIN_KUBECONFIG=/etc/kubernetes/admin.conf

upsert_bash_export() {
    var_name="$1"
    var_value="$2"
    shell_file="$3"
    escaped_value=$(printf "%s" "$var_value" | sed "s/'/'\\\\''/g")

    if [ ! -f "${shell_file}" ]; then
        touch "${shell_file}"
    fi

    sed -i "/^export ${var_name}=/d" "${shell_file}"
    printf "export %s='%s'\n" "${var_name}" "${escaped_value}" >> "${shell_file}"
}

if [ "$(echo $NODEGROUP_ROLE | tr '[:upper:]' '[:lower:]')" == "master" ]; then
    # Prepare master kubeconfig content
    config_content=$(cat << EOF
apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: $(cat ${CERT_DIR}/ca.crt | base64 | tr -d '\n')
    server: https://127.0.0.1:${KUBE_API_PORT}
  name: ${CLUSTER_UUID}
contexts:
- context:
    cluster: ${CLUSTER_UUID}
    user: admin
  name: default
current-context: default
kind: Config
preferences: {}
users:
- name: admin
  user:
    as-user-extra: {}
    client-certificate-data: $(cat ${CERT_DIR}/admin.crt | base64 | tr -d '\n')
    client-key-data: $(cat ${CERT_DIR}/admin.key | base64 | tr -d '\n')
EOF
)
else
    # Check if required worker certificates exist
    if [ ! -f "${CERT_DIR}/kubelet.crt" ] || [ ! -f "${CERT_DIR}/kubelet.key" ]; then
        echo "Required worker certificates not found in ${CERT_DIR}"
        exit 1
    fi

    KUBE_PROTOCOL="https"
    if [ "$TLS_DISABLED" = "True" ]; then
        KUBE_PROTOCOL="http"
    fi

    KUBE_MASTER_URI="$KUBE_PROTOCOL://$KUBE_MASTER_IP:$KUBE_API_PORT"
    
    # Prepare worker kubeconfig content
    config_content=$(cat << EOF
apiVersion: v1
clusters:
- cluster:
    certificate-authority: ${CERT_DIR}/ca.crt
    server: ${KUBE_MASTER_URI}
  name: kubernetes
contexts:
- context:
    cluster: kubernetes
    user: system:node:${INSTANCE_NAME}
  name: default
current-context: default
kind: Config
preferences: {}
users:
- name: system:node:${INSTANCE_NAME}
  user:
    as-user-extra: {}
    client-certificate: ${CERT_DIR}/kubelet.crt
    client-key: ${CERT_DIR}/kubelet.key
EOF
)
fi

# Write to temporary file first
echo "$config_content" > ${ADMIN_KUBECONFIG}.tmp

# Move to final location if different or doesn't exist
if [ ! -f ${ADMIN_KUBECONFIG} ] || ! $ssh_cmd cmp -s ${ADMIN_KUBECONFIG}.tmp ${ADMIN_KUBECONFIG}; then
    mv ${ADMIN_KUBECONFIG}.tmp ${ADMIN_KUBECONFIG}
    chown root:root ${ADMIN_KUBECONFIG}
    chmod 600 ${ADMIN_KUBECONFIG}
else
    rm ${ADMIN_KUBECONFIG}.tmp
fi

# Keep a single canonical KUBECONFIG export for interactive root shells.
upsert_bash_export "KUBECONFIG" "${ADMIN_KUBECONFIG}" "${BASH_RC_FILE}"

export KUBECONFIG=${ADMIN_KUBECONFIG}
$ssh_cmd mkdir -p $HOME/.kube
$ssh_cmd cp -f ${ADMIN_KUBECONFIG} $HOME/.kube/config
