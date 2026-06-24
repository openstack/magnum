#!/bin/bash

HEAT_PARAMS=/etc/sysconfig/heat-params
LOG_FILE=/var/log/magnum-ca-rotate.log
CURRENT_STEP=init
rotation_work_dir=""
rotation_id=""
run_ca_rotation=false

is_true() {
    [ "$(echo "${1:-false}" | tr '[:upper:]' '[:lower:]')" = "true" ]
}

if [ -f "${HEAT_PARAMS}" ]; then
    set +x
    . "${HEAT_PARAMS}"

    rotation_id="${ca_rotation_id_input:-${CA_ROTATION_ID:-}}"
    if [ -n "${rotation_id}" ] && \
       ! is_true "${IS_UPGRADE:-false}" && \
       ! is_true "${IS_RESIZE:-false}"; then
        run_ca_rotation=true
    fi
fi

if [ "${run_ca_rotation}" = "true" ]; then

echo "START: rotate CA certs on master"

mkdir -p "$(dirname "${LOG_FILE}")"
touch "${LOG_FILE}"
chmod 600 "${LOG_FILE}"

log() {
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    printf '%s [master] %s\n' "${timestamp}" "$1" | tee -a "${LOG_FILE}"
}

on_exit() {
    rc=$?
    if [ "${rc}" -eq 0 ]; then
        log "EXIT rc=0 step=${CURRENT_STEP}"
        if [ -n "${rotation_work_dir}" ] && [ -d "${rotation_work_dir}" ]; then
            rm -rf "${rotation_work_dir}"
        fi
    else
        log "EXIT rc=${rc} step=${CURRENT_STEP}"
        if [ -n "${rotation_work_dir}" ] && [ -d "${rotation_work_dir}" ]; then
            log "staged rotation data kept at ${rotation_work_dir}"
        fi
    fi
}

trap on_exit EXIT

set -eu -o pipefail

# Keep xtrace in the node-local log file instead of Heat deployment
# stdout/stderr so successful runs don't generate oversized signal payloads.
exec 9>>"${LOG_FILE}"
export BASH_XTRACEFD=9
set -x

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

service_account_key="${kube_service_account_key_input:-${KUBE_SERVICE_ACCOUNT_KEY:-}}"
service_account_private_key="${kube_service_account_private_key_input:-${KUBE_SERVICE_ACCOUNT_PRIVATE_KEY:-}}"
ca_key="${ca_key_input:-${CA_KEY:-}}"
cert_dir=/etc/kubernetes/certs
etcd_cert_dir=/etc/etcd/certs
admin_kubeconfig=/etc/kubernetes/admin.conf
rotation_state_file=/var/lib/magnum/last_ca_rotation_id

current_rotation_id=""
if [ -f "${rotation_state_file}" ]; then
    current_rotation_id=$(cat "${rotation_state_file}")
fi

log "loaded heat params rotation_id=${rotation_id:-empty} current_rotation_id=${current_rotation_id:-empty}"

update_heat_param() {
    param_key="$1"
    param_value="$2"

    sed -i "/^${param_key}=/d" "${HEAT_PARAMS}"
    printf '%s="%s"\n' "${param_key}" "${param_value}" >> "${HEAT_PARAMS}"
}

wait_for_api() {
    for _attempt in $(seq 1 30); do
        if kubectl get namespace >/dev/null 2>&1; then
            return 0
        fi
        sleep 5
    done
    return 1
}

wait_for_control_plane_services() {
    for _attempt in $(seq 1 60); do
        all_active=1
        for service in \
            etcd kube-apiserver kube-controller-manager \
            kube-scheduler kubelet kube-proxy; do
            if ! $ssh_cmd systemctl is-active --quiet "${service}"; then
                all_active=0
                break
            fi
        done
        if [ "${all_active}" -eq 1 ]; then
            return 0
        fi
        sleep 5
    done
    return 1
}

assert_file_exists() {
    file_path="$1"

    if [ ! -s "${file_path}" ]; then
        log "Expected file missing or empty: ${file_path}"
        exit 1
    fi
}

generate_certificates() {
    cert_name="$1"
    cert_config="$2"
    target_dir="$3"
    cert_path="${target_dir}/${cert_name}.crt"
    csr_path="${target_dir}/${cert_name}.csr"
    key_path="${target_dir}/${cert_name}.key"

    $ssh_cmd openssl genrsa -out "${key_path}" 4096
    chmod 400 "${key_path}"
    $ssh_cmd openssl req -new -days 1000 \
        -key "${key_path}" \
        -out "${csr_path}" \
        -reqexts req_ext \
        -config "${cert_config}"

    csr_req=$(python -c "import json; fp = open('${csr_path}'); print(json.dumps({'cluster_uuid': '$CLUSTER_UUID', 'csr': fp.read()})); fp.close()")
    curl ${verify_ca_opt} -s -X POST \
        -H "X-Auth-Token: ${user_token}" \
        -H "OpenStack-API-Version: container-infra latest" \
        -H "Content-Type: application/json" \
        -d "${csr_req}" \
        "${MAGNUM_URL}/certificates" | python -c 'import sys, json; print(json.load(sys.stdin)["pem"])' > "${cert_path}"

    rm -f "${csr_path}"
}

replace_managed_files() {
    source_dir="$1"
    target_dir="$2"
    shift 2

    mkdir -p "${target_dir}"
    for managed_file in "$@"; do
        rm -f "${target_dir}/${managed_file}"
    done

    cp -a "${source_dir}/." "${target_dir}/"
}

if [ "${rotation_id}" = "${current_rotation_id}" ]; then
    log "CA rotation ${rotation_id} already applied, skipping"
elif [ -z "${service_account_key}" ] || [ -z "${service_account_private_key}" ]; then
    log "Missing service account key material for CA rotation"
    exit 1
elif [ "${TLS_DISABLED}" = "True" ]; then
    log "TLS is disabled, skipping CA rotation"
else

rotation_root=/var/lib/magnum/ca-rotation
rotation_work_dir="${rotation_root}/${rotation_id}"
staged_cert_dir="${rotation_work_dir}/kubernetes-certs"
staged_etcd_cert_dir="${rotation_work_dir}/etcd-certs"
staged_admin_kubeconfig="${rotation_work_dir}/admin.conf"
staged_ca_cert="${staged_cert_dir}/ca.crt"

CURRENT_STEP=metadata
if [ "${VERIFY_CA}" = "True" ]; then
    verify_ca_opt=""
else
    verify_ca_opt="-k"
fi

if [ -z "${KUBE_NODE_IP:-}" ]; then
    KUBE_NODE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
fi

sans="IP:${KUBE_NODE_IP}"

if [ -z "${KUBE_NODE_PUBLIC_IP:-}" ]; then
    KUBE_NODE_PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
fi

if [ -n "${KUBE_NODE_PUBLIC_IP:-}" ]; then
    sans="${sans},IP:${KUBE_NODE_PUBLIC_IP}"
fi

if [ "${KUBE_NODE_PUBLIC_IP:-}" != "${KUBE_API_PUBLIC_ADDRESS:-}" ] && \
   [ -n "${KUBE_API_PUBLIC_ADDRESS:-}" ]; then
    sans="${sans},IP:${KUBE_API_PUBLIC_ADDRESS}"
fi

if [ "${KUBE_NODE_IP}" != "${KUBE_API_PRIVATE_ADDRESS:-}" ] && \
   [ -n "${KUBE_API_PRIVATE_ADDRESS:-}" ]; then
    sans="${sans},IP:${KUBE_API_PRIVATE_ADDRESS}"
fi

if [ -n "${MASTER_HOSTNAME:-}" ]; then
    sans="${sans},DNS:${MASTER_HOSTNAME}"
fi

if [ -n "${ETCD_LB_VIP:-}" ]; then
    sans="${sans},IP:${ETCD_LB_VIP}"
fi

sans="${sans},IP:127.0.0.1"
KUBE_SERVICE_IP=$(echo "${PORTAL_NETWORK_CIDR}" | awk 'BEGIN{FS="[./]"; OFS="."}{print $1,$2,$3,$4 + 1}')
sans="${sans},IP:${KUBE_SERVICE_IP}"
sans="${sans},DNS:kubernetes,DNS:kubernetes.default,DNS:kubernetes.default.svc,DNS:kubernetes.default.svc.cluster.local"

rm -rf "${rotation_work_dir}"
mkdir -p "${staged_cert_dir}" "${staged_etcd_cert_dir}"
mkdir -p "$(dirname "${rotation_state_file}")"
log "prepared staged certificate directories"

CURRENT_STEP=keystone_token
auth_json=$(cat <<EOF
{
    "auth": {
        "identity": {
            "methods": [
                "password"
            ],
            "password": {
                "user": {
                    "id": "${TRUSTEE_USER_ID}",
                    "password": "${TRUSTEE_PASSWORD}"
                }
            }
        },
        "scope": {
            "OS-TRUST:trust": {
                "id": "${TRUST_ID}"
            }
        }
    }
}
EOF
)

user_token=$(curl ${verify_ca_opt} -s -i -X POST \
    -H "Content-Type: application/json" \
    -d "${auth_json}" \
    "${AUTH_URL}/auth/tokens" | grep -i X-Subject-Token | awk '{print $2}' | tr -d '[[:space:]]')

if [ -z "${user_token}" ]; then
    log "Failed to obtain a Keystone token for CA rotation"
    exit 1
fi
log "obtained Keystone token"

CURRENT_STEP=fetch_cluster_ca
curl ${verify_ca_opt} -s -X GET \
    -H "X-Auth-Token: ${user_token}" \
    -H "OpenStack-API-Version: container-infra latest" \
    "${MAGNUM_URL}/certificates/${CLUSTER_UUID}" | python -c 'import sys, json; print(json.load(sys.stdin)["pem"])' > "${staged_ca_cert}"
assert_file_exists "${staged_ca_cert}"
log "fetched cluster CA certificate"

CURRENT_STEP=write_openssl_configs
cat > "${staged_cert_dir}/server.conf" <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions     = req_ext
prompt = no
[req_distinguished_name]
CN = kubernetes
[req_ext]
subjectAltName = ${sans}
extendedKeyUsage = clientAuth,serverAuth
EOF

cat > "${staged_cert_dir}/proxy.conf" <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions     = req_ext
prompt = no
[req_distinguished_name]
CN = system:kube-proxy
O=system:node-proxier
OU=OpenStack/Magnum
C=US
ST=TX
L=Austin
[req_ext]
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=clientAuth
EOF

cat > "${staged_cert_dir}/scheduler.conf" <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions     = req_ext
prompt = no
[req_distinguished_name]
CN = system:kube-scheduler
O=system:kube-scheduler
OU=OpenStack/Magnum
C=US
ST=TX
L=Austin
[req_ext]
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=clientAuth,serverAuth
EOF

cat > "${staged_cert_dir}/controller.conf" <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions     = req_ext
prompt = no
[req_distinguished_name]
CN = system:kube-controller-manager
O=system:kube-controller-manager
OU=OpenStack/Magnum
C=US
ST=TX
L=Austin
[req_ext]
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=clientAuth,serverAuth
EOF

cat > "${staged_cert_dir}/kubelet.conf" <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions     = req_ext
prompt = no
[req_distinguished_name]
CN = system:node:${INSTANCE_NAME}
O=system:nodes
OU=OpenStack/Magnum
C=US
ST=TX
L=Austin
[req_ext]
subjectAltName = ${sans}
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=clientAuth,serverAuth
EOF

cat > "${staged_cert_dir}/admin.conf" <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions     = req_ext
prompt = no
[req_distinguished_name]
CN = admin
O = system:masters
OU=OpenStack/Magnum
C=US
ST=TX
L=Austin
[req_ext]
extendedKeyUsage= clientAuth
EOF

CURRENT_STEP=generate_certificates
log "generating master certificates"
generate_certificates server "${staged_cert_dir}/server.conf" "${staged_cert_dir}"
generate_certificates kubelet "${staged_cert_dir}/kubelet.conf" "${staged_cert_dir}"
generate_certificates admin "${staged_cert_dir}/admin.conf" "${staged_cert_dir}"
generate_certificates proxy "${staged_cert_dir}/proxy.conf" "${staged_cert_dir}"
generate_certificates controller "${staged_cert_dir}/controller.conf" "${staged_cert_dir}"
generate_certificates scheduler "${staged_cert_dir}/scheduler.conf" "${staged_cert_dir}"

CURRENT_STEP=write_key_material
echo -e "${service_account_key}" > "${staged_cert_dir}/service_account.key"
echo -e "${service_account_private_key}" > "${staged_cert_dir}/service_account_private.key"

if [ -n "${ca_key}" ]; then
    echo -e "${ca_key}" > "${staged_cert_dir}/ca.key"
    chmod 400 "${staged_cert_dir}/ca.key"
fi

for required_file in \
    ca.crt server.conf proxy.conf scheduler.conf controller.conf \
    kubelet.conf admin.conf server.crt server.key kubelet.crt kubelet.key \
    admin.crt admin.key proxy.crt proxy.key controller.crt controller.key \
    scheduler.crt scheduler.key service_account.key \
    service_account_private.key; do
    assert_file_exists "${staged_cert_dir}/${required_file}"
done

CURRENT_STEP=permissions
if ! $ssh_cmd id etcd >/dev/null 2>&1; then
    $ssh_cmd useradd -s "/sbin/nologin" --system etcd
fi

if ! $ssh_cmd id kube >/dev/null 2>&1; then
    $ssh_cmd useradd -s "/sbin/nologin" --system kube
fi

$ssh_cmd groupadd kube_etcd -f
$ssh_cmd usermod -a -G kube_etcd etcd
$ssh_cmd usermod -a -G kube_etcd kube
$ssh_cmd chmod 550 "${staged_cert_dir}"
$ssh_cmd chown -R kube:kube_etcd "${staged_cert_dir}"
$ssh_cmd chmod 440 "${staged_cert_dir}/server.key"
$ssh_cmd chmod 440 "${staged_cert_dir}/proxy.key"
$ssh_cmd chmod 440 "${staged_cert_dir}/controller.key"
$ssh_cmd chmod 440 "${staged_cert_dir}/scheduler.key"
$ssh_cmd chmod 440 "${staged_cert_dir}/kubelet.key"
$ssh_cmd cp -a "${staged_cert_dir}/." "${staged_etcd_cert_dir}/"
$ssh_cmd chmod 550 "${staged_etcd_cert_dir}"
$ssh_cmd chown -R kube:kube_etcd "${staged_etcd_cert_dir}"
log "prepared staged certificate permissions"

CURRENT_STEP=write_kubeconfig
cat > "${staged_admin_kubeconfig}" <<EOF
apiVersion: v1
clusters:
- cluster:
    certificate-authority: ${cert_dir}/ca.crt
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
    client-certificate: ${cert_dir}/admin.crt
    client-key: ${cert_dir}/admin.key
EOF
chmod 600 "${staged_admin_kubeconfig}"

CURRENT_STEP=replace_certificates
replace_managed_files "${staged_cert_dir}" "${cert_dir}" \
    ca.crt ca.key server.conf server.crt server.key proxy.conf proxy.crt \
    proxy.key scheduler.conf scheduler.crt scheduler.key controller.conf \
    controller.crt controller.key kubelet.conf kubelet.crt kubelet.key \
    admin.conf admin.crt admin.key service_account.key \
    service_account_private.key
replace_managed_files "${staged_etcd_cert_dir}" "${etcd_cert_dir}" \
    ca.crt ca.key server.conf server.crt server.key proxy.conf proxy.crt \
    proxy.key scheduler.conf scheduler.crt scheduler.key controller.conf \
    controller.crt controller.key kubelet.conf kubelet.crt kubelet.key \
    admin.conf admin.crt admin.key service_account.key \
    service_account_private.key
$ssh_cmd chmod 550 "${cert_dir}"
$ssh_cmd chown -R kube:kube_etcd "${cert_dir}"
$ssh_cmd chmod 440 "${cert_dir}/server.key"
$ssh_cmd chmod 440 "${cert_dir}/proxy.key"
$ssh_cmd chmod 440 "${cert_dir}/controller.key"
$ssh_cmd chmod 440 "${cert_dir}/scheduler.key"
$ssh_cmd chmod 440 "${cert_dir}/kubelet.key"
$ssh_cmd chmod 550 "${etcd_cert_dir}"
$ssh_cmd chown -R kube:kube_etcd "${etcd_cert_dir}"
mv "${staged_admin_kubeconfig}" "${admin_kubeconfig}"
$ssh_cmd chmod 600 "${admin_kubeconfig}"
log "replaced live certificate files from staging"

export KUBECONFIG="${admin_kubeconfig}"
$ssh_cmd mkdir -p /root/.kube
$ssh_cmd cp -f "${admin_kubeconfig}" /root/.kube/config
log "updated admin kubeconfig"

CURRENT_STEP=restart_services
for service in etcd kube-apiserver kube-controller-manager kube-scheduler kubelet kube-proxy; do
    log "restart service ${service}"
    $ssh_cmd systemctl restart "${service}"
done

CURRENT_STEP=wait_for_services
if ! wait_for_control_plane_services; then
    log "Control plane services did not become active after CA rotation"
    exit 1
fi
log "control plane services are active after restart"

api_ready=0
CURRENT_STEP=wait_for_api
if wait_for_api; then
    api_ready=1
    log "Kubernetes API is ready after restart"
elif [ "${NUMBER_OF_MASTERS:-1}" -gt 1 ]; then
    log "Kubernetes API is not ready yet on this HA master; continuing so remaining masters can rotate"
else
    log "Kubernetes API did not become ready after CA rotation"
    exit 1
fi

CURRENT_STEP=patch_workloads
if [ "${api_ready}" -eq 1 ]; then
    rotation_patch=$(printf '{"spec":{"template":{"metadata":{"annotations":{"ca-rotation":"%s"}}}}}' "${rotation_id}")

    for namespace in $(kubectl get namespace -o jsonpath='{.items[*].metadata.name}'); do
        for name in $(kubectl get deployments -n "${namespace}" -o jsonpath='{.items[*].metadata.name}'); do
            kubectl patch deployment -n "${namespace}" "${name}" -p "${rotation_patch}"
        done
        for name in $(kubectl get daemonset -n "${namespace}" -o jsonpath='{.items[*].metadata.name}'); do
            kubectl patch daemonset -n "${namespace}" "${name}" -p "${rotation_patch}"
        done
    done

    log "patched workloads to roll pods"
else
    log "Skipping workload patching because Kubernetes API is not ready on this master yet"
fi

CURRENT_STEP=update_state
update_heat_param KUBE_SERVICE_ACCOUNT_KEY "${service_account_key}"
update_heat_param KUBE_SERVICE_ACCOUNT_PRIVATE_KEY "${service_account_private_key}"
update_heat_param CA_ROTATION_ID "${rotation_id}"
if [ -n "${ca_key}" ]; then
    update_heat_param CA_KEY "${ca_key}"
fi
printf '%s' "${rotation_id}" > "${rotation_state_file}"
chmod 600 "${rotation_state_file}"
log "updated heat params and persisted rotation state"

echo "END: rotate CA certs on master"
fi

# Restore default shell settings so that subsequent fragments in the
# concatenated upgrade_kubernetes_config script are not affected by the
# strict -eu -o pipefail that this rotation block enabled.
set +e +u +o pipefail
fi
