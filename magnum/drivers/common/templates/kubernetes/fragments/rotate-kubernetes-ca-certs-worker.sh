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

echo "START: rotate CA certs on worker"

mkdir -p "$(dirname "${LOG_FILE}")"
touch "${LOG_FILE}"
chmod 600 "${LOG_FILE}"

log() {
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    printf '%s [worker] %s\n' "${timestamp}" "$1" | tee -a "${LOG_FILE}"
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
cert_dir=/etc/kubernetes/certs
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

HOSTNAME=$(cat /etc/hostname | head -1)
rm -rf "${rotation_work_dir}"
mkdir -p "${staged_cert_dir}"
mkdir -p "$(dirname "${rotation_state_file}")"
log "prepared staged worker certificate directories"

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
subjectAltName = IP:${KUBE_NODE_IP},DNS:${INSTANCE_NAME},DNS:${HOSTNAME}
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=clientAuth,serverAuth
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

CURRENT_STEP=generate_certificates
log "generating worker certificates"
generate_certificates kubelet "${staged_cert_dir}/kubelet.conf" "${staged_cert_dir}"
generate_certificates proxy "${staged_cert_dir}/proxy.conf" "${staged_cert_dir}"

for required_file in \
    ca.crt kubelet.conf proxy.conf kubelet.crt kubelet.key \
    proxy.crt proxy.key; do
    assert_file_exists "${staged_cert_dir}/${required_file}"
done

CURRENT_STEP=permissions
chmod 550 "${staged_cert_dir}"
chmod 440 "${staged_cert_dir}/kubelet.key"
chmod 440 "${staged_cert_dir}/proxy.key"
log "prepared staged worker certificate permissions"

CURRENT_STEP=replace_certificates
replace_managed_files "${staged_cert_dir}" "${cert_dir}" \
    ca.crt kubelet.conf kubelet.crt kubelet.key proxy.conf proxy.crt \
    proxy.key
$ssh_cmd chmod 550 "${cert_dir}"
$ssh_cmd chmod 440 "${cert_dir}/kubelet.key"
$ssh_cmd chmod 440 "${cert_dir}/proxy.key"
log "replaced live worker certificate files from staging"

CURRENT_STEP=restart_services
for service in kubelet kube-proxy; do
    log "restart service ${service}"
    $ssh_cmd systemctl restart "${service}"
done

CURRENT_STEP=update_state
update_heat_param KUBE_SERVICE_ACCOUNT_KEY "${service_account_key}"
update_heat_param KUBE_SERVICE_ACCOUNT_PRIVATE_KEY "${service_account_private_key}"
update_heat_param CA_ROTATION_ID "${rotation_id}"
printf '%s' "${rotation_id}" > "${rotation_state_file}"
chmod 600 "${rotation_state_file}"
log "updated heat params and persisted rotation state"

echo "END: rotate CA certs on worker"
fi

# Restore default shell settings so that subsequent fragments in the
# concatenated upgrade_kubernetes_config script are not affected by the
# strict -eu -o pipefail that this rotation block enabled.
set +e +u +o pipefail
fi
