#!/bin/bash

# Exit on error
set -e

set +x
. /etc/sysconfig/heat-params
set -x

echo "configuring kubernetes (master)"

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

version_gt() { test "$(printf '%s\n' "$@" | sort -V | head -n 1)" != "$1"; }
version_lt() { test "$(printf '%s\n' "$@" | sort -V | head -n 1)" = "$1"; }

# Setup proxy if defined
for PROXY in HTTP_PROXY HTTPS_PROXY NO_PROXY; do
    if [ -n "${!PROXY}" ]; then
        export ${PROXY}="${!PROXY}"
    fi
done

# Setup network driver
if [ "$NETWORK_DRIVER" = "flannel" ]; then
    $ssh_cmd mkdir -p /opt/cni/bin
    cni_plugin_path="/srv/magnum/kubernetes/cni"
    $ssh_cmd mkdir -p ${cni_plugin_path}
    
    # Download and install CNI plugins if not present or if checksum differs
    cni_tgz="${cni_plugin_path}/cni-plugins-linux-amd64-${FLANNEL_CNI_TAG}.tgz"
    if [ ! -f "${cni_tgz}" ] || ! $ssh_cmd sha256sum -c "${cni_tgz}.sha256" &>/dev/null; then
        $ssh_cmd curl --retry 5 --retry-delay 10 -L \
            https://github.com/containernetworking/plugins/releases/download/${FLANNEL_CNI_TAG}/cni-plugins-linux-amd64-${FLANNEL_CNI_TAG}.tgz \
            -o "${cni_tgz}.tmp"
        $ssh_cmd mv "${cni_tgz}.tmp" "${cni_tgz}"
        $ssh_cmd curl -L \
            https://github.com/containernetworking/plugins/releases/download/${FLANNEL_CNI_TAG}/cni-plugins-linux-amd64-${FLANNEL_CNI_TAG}.tgz.sha256 \
            -o "${cni_tgz}.sha256"
    fi
    
    # Extract CNI plugins
    $ssh_cmd tar -C /opt/cni/bin -xzf ${cni_tgz}
    $ssh_cmd chmod +x /opt/cni/bin/*
fi

# Configure network settings
if [ "$NETWORK_DRIVER" = "calico" ]; then
    if ! grep -q "net.ipv4.conf.all.rp_filter = 1" /etc/sysctl.conf; then
        echo "net.ipv4.conf.all.rp_filter = 1" >> /etc/sysctl.conf
        $ssh_cmd sysctl -p
    fi
    
    if [ "$(systemctl is-active NetworkManager.service)" = "active" ]; then
        CALICO_NM=/etc/NetworkManager/conf.d/calico.conf
        if [ ! -f ${CALICO_NM} ]; then
            echo "Writing File: $CALICO_NM"
            mkdir -p $(dirname ${CALICO_NM})
            cat << EOF > ${CALICO_NM}
[keyfile]
unmanaged-devices=interface-name:cali*;interface-name:tunl*
EOF
            systemctl restart NetworkManager
        fi
    fi
elif [ "$NETWORK_DRIVER" = "flannel" ]; then
    $ssh_cmd modprobe -a vxlan br_netfilter
    if [ ! -f /etc/modules-load.d/flannel.conf ]; then
        cat <<EOF > /etc/modules-load.d/flannel.conf
vxlan
br_netfilter
EOF
    fi
fi

# Configure sysctl settings if not already set
if [ ! -f /etc/sysctl.d/k8s_custom.conf ]; then
    cat <<EOF > /etc/sysctl.d/k8s_custom.conf
net.ipv4.conf.default.rp_filter=2
net.ipv4.conf.*.rp_filter=2
net.ipv4.conf.all.promote_secondaries = 1
net.ipv4.conf.*.accept_source_route = 1
net.ipv4.ip_unprivileged_port_start = 0
net.ipv4.ping_group_range = 0 2147483647
EOF
    $ssh_cmd sysctl --system
fi

# Create kubernetes directories
mkdir -p /srv/magnum/kubernetes/

# Write kubernetes config files
for config in config apiserver controller-manager scheduler proxy; do
    config_file="/etc/kubernetes/${config}"
    config_content=""
    
    case "${config}" in
        "config")
            config_content="KUBE_LOG_LEVEL=\"--v=2\""
            ;;
        "apiserver")
            config_content=$(cat << EOF
KUBE_ETCD_SERVERS="--etcd-servers=http://127.0.0.1:2379,http://127.0.0.1:4001"
KUBE_SERVICE_ADDRESSES="--service-cluster-ip-range=10.254.0.0/16"
KUBE_API_ARGS=""
EOF
)
            ;;
        "controller-manager")
            config_content="KUBE_CONTROLLER_MANAGER_ARGS=\"--authorization-always-allow-paths=/healthz,/readyz,/livez,/metrics\""
            ;;
        "scheduler")
            config_content="KUBE_SCHEDULER_ARGS=\"--authorization-always-allow-paths=/healthz,/readyz,/livez,/metrics\""
            ;;
        "proxy")
            config_content="KUBE_PROXY_ARGS=\"\""
            ;;
    esac
    
    # Write config file if it doesn't exist or content differs
    if [ ! -f "${config_file}" ] || [ "$(cat ${config_file})" != "${config_content}" ]; then
        echo "${config_content}" > "${config_file}.tmp"
        mv "${config_file}.tmp" "${config_file}"
    fi
done

if [ "$(echo $USE_PODMAN | tr '[:upper:]' '[:lower:]')" == "true" ]; then
    # Function to safely write a file via ssh
    write_file_via_ssh() {
        local target_file="$1"
        local content="$2"
        local tmp_file="${target_file}.tmp"
        
        # Create parent directory
        $ssh_cmd mkdir -p "$(dirname ${target_file})"
        
        # Write content to temp file
        printf '%s' "$content" | $ssh_cmd "cat > ${tmp_file}"
        
        # Compare with existing file if it exists
        if $ssh_cmd test -f "${target_file}"; then
            if ! $ssh_cmd cmp -s "${tmp_file}" "${target_file}"; then
                $ssh_cmd mv "${tmp_file}" "${target_file}"
                return 0  # File was updated
            else
                $ssh_cmd rm -f "${tmp_file}"
                return 1  # No update needed
            fi
        else
            $ssh_cmd mv "${tmp_file}" "${target_file}"
            return 0  # New file created
        fi
    }

    # Define services and their configurations
    declare -A services=(
        ["kube-apiserver"]="[Unit]
Description=kube-apiserver
After=network.target
[Service]
EnvironmentFile=/etc/sysconfig/heat-params
EnvironmentFile=/etc/kubernetes/config
EnvironmentFile=/etc/kubernetes/apiserver
ExecStartPre=/bin/mkdir -p /etc/kubernetes/
ExecStartPre=-/usr/bin/podman rm kube-apiserver
ExecStart=/bin/bash -c '/usr/bin/podman run --name kube-apiserver \\
    --net host \\
    --volume /etc/kubernetes:/etc/kubernetes:ro,z \\
    --volume /usr/lib/os-release:/etc/os-release:ro \\
    --volume /etc/ssl/certs:/etc/ssl/certs:ro \\
    --volume /run:/run \\
    --volume /etc/pki/tls/certs:/usr/share/ca-certificates:ro \\
    \${CONTAINER_INFRA_PREFIX:-registry.k8s.io/}kube-apiserver-\${ARCH}:\${KUBE_TAG} \\
    kube-apiserver \\
    \$KUBE_LOG_LEVEL \$KUBE_ETCD_SERVERS \$KUBE_API_ADDRESS \$KUBE_SERVICE_ADDRESSES \$KUBE_API_ARGS'
ExecStop=-/usr/bin/podman stop kube-apiserver
Delegate=yes
KillMode=process
Restart=always
RestartSec=10
TimeoutStartSec=10min
[Install]
WantedBy=multi-user.target"

        ["kube-controller-manager"]="[Unit]
Description=kube-controller-manager
After=network.target kube-apiserver.service
[Service]
EnvironmentFile=/etc/sysconfig/heat-params
EnvironmentFile=/etc/kubernetes/config
EnvironmentFile=/etc/kubernetes/controller-manager
ExecStartPre=/bin/mkdir -p /etc/kubernetes/
ExecStartPre=-/usr/bin/podman rm kube-controller-manager
ExecStart=/bin/bash -c '/usr/bin/podman run --name kube-controller-manager \\
    --net host \\
    --volume /etc/kubernetes:/etc/kubernetes:ro,z \\
    --volume /usr/lib/os-release:/etc/os-release:ro \\
    --volume /etc/ssl/certs:/etc/ssl/certs:ro \\
    --volume /run:/run \\
    --volume /etc/pki/tls/certs:/usr/share/ca-certificates:ro \\
    \${CONTAINER_INFRA_PREFIX:-registry.k8s.io/}kube-controller-manager-\${ARCH}:\${KUBE_TAG} \\
    kube-controller-manager \\
    --secure-port=0 \\
    \$KUBE_LOG_LEVEL \$KUBE_MASTER \$KUBE_CONTROLLER_MANAGER_ARGS'
ExecStop=-/usr/bin/podman stop kube-controller-manager
Delegate=yes
KillMode=process
Restart=always
RestartSec=10
TimeoutStartSec=10min
[Install]
WantedBy=multi-user.target"

        ["kube-scheduler"]="[Unit]
Description=kube-scheduler
After=network.target kube-apiserver.service
[Service]
EnvironmentFile=/etc/sysconfig/heat-params
EnvironmentFile=/etc/kubernetes/config
EnvironmentFile=/etc/kubernetes/scheduler
ExecStartPre=/bin/mkdir -p /etc/kubernetes/
ExecStartPre=-/usr/bin/podman rm kube-scheduler
ExecStart=/bin/bash -c '/usr/bin/podman run --name kube-scheduler \\
    --net host \\
    --volume /etc/kubernetes:/etc/kubernetes:ro,z \\
    --volume /usr/lib/os-release:/etc/os-release:ro \\
    --volume /etc/ssl/certs:/etc/ssl/certs:ro \\
    --volume /run:/run \\
    --volume /etc/pki/tls/certs:/usr/share/ca-certificates:ro \\
    \${CONTAINER_INFRA_PREFIX:-registry.k8s.io/}kube-scheduler-\${ARCH}:\${KUBE_TAG} \\
    kube-scheduler \\
    \$KUBE_LOG_LEVEL \$KUBE_MASTER \$KUBE_SCHEDULER_ARGS'
ExecStop=-/usr/bin/podman stop kube-scheduler
Delegate=yes
KillMode=process
Restart=always
RestartSec=10
TimeoutStartSec=10min
[Install]
WantedBy=multi-user.target"

        ["kubelet"]="[Unit]
Description=Kubelet
After=network.target containerd.service
Wants=containerd.service
[Service]
EnvironmentFile=/etc/sysconfig/heat-params
EnvironmentFile=/etc/kubernetes/config
EnvironmentFile=-/etc/kubernetes/kubelet.env
ExecStartPre=/bin/mkdir -p /etc/kubernetes/cni/net.d
ExecStartPre=/bin/mkdir -p /etc/kubernetes/manifests
ExecStartPre=/bin/mkdir -p /var/lib/calico
ExecStartPre=/bin/mkdir -p /var/lib/containerd
ExecStartPre=/bin/mkdir -p /var/lib/docker
ExecStartPre=/bin/mkdir -p /var/lib/kubelet/volumeplugins
ExecStartPre=/bin/mkdir -p /opt/cni/bin
ExecStart=/usr/local/bin/kubelet \\
    \$KUBE_LOG_LEVEL \$KUBE_LOGTOSTDERR \$KUBELET_API_SERVER \$KUBELET_ADDRESS \$KUBELET_HOSTNAME \$KUBELET_ARGS
Delegate=yes
KillMode=process
Restart=always
RestartSec=10
TimeoutStartSec=10min
[Install]
WantedBy=multi-user.target"

        ["kube-proxy"]="[Unit]
Description=kube-proxy
After=network.target
[Service]
EnvironmentFile=/etc/sysconfig/heat-params
EnvironmentFile=/etc/kubernetes/config
EnvironmentFile=/etc/kubernetes/proxy
ExecStartPre=/bin/mkdir -p /etc/kubernetes/
ExecStartPre=-/usr/bin/podman rm kube-proxy
ExecStart=/bin/bash -c '/usr/bin/podman run --name kube-proxy \\
    --privileged \\
    --net host \\
    --volume /etc/kubernetes:/etc/kubernetes:ro,z \\
    --volume /usr/lib/os-release:/etc/os-release:ro \\
    --volume /etc/ssl/certs:/etc/ssl/certs:ro \\
    --volume /run:/run \\
    --volume /sys/fs/cgroup:/sys/fs/cgroup \\
    --volume /lib/modules:/lib/modules:ro \\
    --volume /etc/pki/tls/certs:/usr/share/ca-certificates:ro \\
    \${CONTAINER_INFRA_PREFIX:-registry.k8s.io/}kube-proxy-\${ARCH}:\${KUBE_TAG} \\
    kube-proxy \\
    \$KUBE_LOG_LEVEL \$KUBE_MASTER \$KUBE_PROXY_ARGS'
ExecStop=-/usr/bin/podman stop kube-proxy
Delegate=yes
KillMode=process
Restart=always
RestartSec=10
TimeoutStartSec=10min
[Install]
WantedBy=multi-user.target"
    )

    # Write service files and track if any were updated
    updated=0
    for service in "${!services[@]}"; do
        service_file="/etc/systemd/system/${service}.service"
        if write_file_via_ssh "${service_file}" "${services[$service]}"; then
            updated=1
        fi
    done

    # Only reload systemd if any files were updated
    if [ "$updated" -eq 1 ]; then
        $ssh_cmd "if [ -d /run/systemd/system ]; then systemctl daemon-reload || true; fi"
    fi
else
    _prefix=${CONTAINER_INFRA_PREFIX:-docker.io/openstackmagnum/}
    _addtl_mounts=',{"type":"bind","source":"/opt/cni","destination":"/opt/cni","options":["bind","rw","slave","mode=777"]},{"type":"bind","source":"/var/lib/docker","destination":"/var/lib/docker","options":["bind","rw","slave","mode=755"]}'
    
    install_script="/srv/magnum/kubernetes/install-kubernetes.sh"
    mkdir -p /srv/magnum/kubernetes/
    
    install_content=$(cat << EOF
#!/bin/bash -x
atomic install --storage ostree --system --set=ADDTL_MOUNTS='${_addtl_mounts}' --system-package=no --name=kubelet ${_prefix}kubernetes-kubelet:${KUBE_TAG}
atomic install --storage ostree --system --system-package=no --name=kube-apiserver ${_prefix}kubernetes-apiserver:${KUBE_TAG}
atomic install --storage ostree --system --system-package=no --name=kube-controller-manager ${_prefix}kubernetes-controller-manager:${KUBE_TAG}
atomic install --storage ostree --system --system-package=no --name=kube-scheduler ${_prefix}kubernetes-scheduler:${KUBE_TAG}
atomic install --storage ostree --system --system-package=no --name=kube-proxy ${_prefix}kubernetes-proxy:${KUBE_TAG}
EOF
)

    # Write install script if it doesn't exist or content differs
    if [ ! -f "${install_script}" ] || [ "$(cat ${install_script})" != "${install_content}" ]; then
        echo "${install_content}" > "${install_script}.tmp"
        chmod +x "${install_script}.tmp"
        mv "${install_script}.tmp" "${install_script}"
    fi
    
    $ssh_cmd "${install_script}"
fi

CERT_DIR=/etc/kubernetes/certs

# Check if required certificates exist
if [ ! -f "${CERT_DIR}/ca.crt" ] || [ ! -f "${CERT_DIR}/proxy.crt" ] || [ ! -f "${CERT_DIR}/proxy.key" ]; then
    echo "Required certificates not found in ${CERT_DIR}"
    exit 1
fi

# Configure kube-proxy
PROXY_KUBECONFIG=/etc/kubernetes/proxy-kubeconfig.yaml
KUBE_PROXY_ARGS="--kubeconfig=${PROXY_KUBECONFIG} --cluster-cidr=${PODS_NETWORK_CIDR} --hostname-override=${INSTANCE_NAME}"

# Write proxy config if it doesn't exist or content differs
proxy_config="KUBE_PROXY_ARGS=\"${KUBE_PROXY_ARGS} ${KUBEPROXY_OPTIONS}\""
if [ ! -f /etc/kubernetes/proxy ] || [ "$(cat /etc/kubernetes/proxy)" != "${proxy_config}" ]; then
    echo "${proxy_config}" > /etc/kubernetes/proxy.tmp
    mv /etc/kubernetes/proxy.tmp /etc/kubernetes/proxy
fi

# Create proxy kubeconfig
proxy_kubeconfig=$(cat << EOF
apiVersion: v1
clusters:
- cluster:
    certificate-authority: ${CERT_DIR}/ca.crt
    server: https://127.0.0.1:${KUBE_API_PORT}
  name: kubernetes
contexts:
- context:
    cluster: kubernetes
    user: kube-proxy
  name: default
current-context: default
kind: Config
preferences: {}
users:
- name: kube-proxy
  user:
    as-user-extra: {}
    client-certificate: ${CERT_DIR}/proxy.crt
    client-key: ${CERT_DIR}/proxy.key
EOF
)

# Write proxy kubeconfig if it doesn't exist or content differs
if [ ! -f "${PROXY_KUBECONFIG}" ] || [ "$(cat ${PROXY_KUBECONFIG})" != "${proxy_kubeconfig}" ]; then
    echo "${proxy_kubeconfig}" > "${PROXY_KUBECONFIG}.tmp"
    mv "${PROXY_KUBECONFIG}.tmp" "${PROXY_KUBECONFIG}"
    chmod 0640 "${PROXY_KUBECONFIG}"
fi

# Update kubernetes config
if ! grep -q "^KUBE_ALLOW_PRIV=.*${KUBE_ALLOW_PRIV}" /etc/kubernetes/config; then
    sed -i "s/^KUBE_ALLOW_PRIV=.*/KUBE_ALLOW_PRIV=\"--allow-privileged=${KUBE_ALLOW_PRIV}\"/" /etc/kubernetes/config
fi

# Build API server arguments
KUBE_API_ARGS="--runtime-config=api/all=true"
KUBE_API_ARGS="$KUBE_API_ARGS --allow-privileged=$KUBE_ALLOW_PRIV"
KUBE_API_ARGS="$KUBE_API_ARGS --kubelet-preferred-address-types=InternalIP,Hostname,ExternalIP"
KUBE_API_ARGS="$KUBE_API_ARGS $KUBEAPI_OPTIONS"
KUBE_API_ADDRESS="--bind-address=0.0.0.0 --secure-port=$KUBE_API_PORT"

# Add security-related arguments if certificates exist
if [ -f "${CERT_DIR}/server.crt" ] && [ -f "${CERT_DIR}/server.key" ]; then
    KUBE_API_ARGS="$KUBE_API_ARGS --authorization-mode=Node,RBAC --tls-cert-file=$CERT_DIR/server.crt"
    KUBE_API_ARGS="$KUBE_API_ARGS --tls-private-key-file=$CERT_DIR/server.key"
    
    if [ -f "${CERT_DIR}/service_account_private.key" ]; then
        KUBE_API_ARGS="$KUBE_API_ARGS --service-account-signing-key-file=$CERT_DIR/service_account_private.key"
    fi
    
    if [ -f "${CERT_DIR}/service_account.key" ]; then
        KUBE_API_ARGS="$KUBE_API_ARGS --service-account-key-file=${CERT_DIR}/service_account.key"
    fi
    
    KUBE_API_ARGS="$KUBE_API_ARGS --service-account-issuer=https://kubernetes.default.svc.cluster.local"
    KUBE_API_ARGS="$KUBE_API_ARGS --client-ca-file=$CERT_DIR/ca.crt"
    KUBE_API_ARGS="$KUBE_API_ARGS --kubelet-certificate-authority=${CERT_DIR}/ca.crt --kubelet-client-certificate=${CERT_DIR}/server.crt --kubelet-client-key=${CERT_DIR}/server.key"
    
    # Add metrics-server/aggregator communication args
    KUBE_API_ARGS="${KUBE_API_ARGS} \
        --proxy-client-cert-file=${CERT_DIR}/server.crt \
        --proxy-client-key-file=${CERT_DIR}/server.key \
        --requestheader-allowed-names=front-proxy-client,kube,kubernetes \
        --requestheader-client-ca-file=${CERT_DIR}/ca.crt \
        --requestheader-extra-headers-prefix=X-Remote-Extra- \
        --requestheader-group-headers=X-Remote-Group \
        --requestheader-username-headers=X-Remote-User"
fi

# Configure Keystone authentication if enabled
if [ "$KEYSTONE_AUTH_ENABLED" == "True" ]; then
    KEYSTONE_WEBHOOK_CONFIG=/etc/kubernetes/keystone_webhook_config.yaml
    
    if [ ! -f "${KEYSTONE_WEBHOOK_CONFIG}" ]; then
        echo "Writing File: $KEYSTONE_WEBHOOK_CONFIG"
        mkdir -p $(dirname ${KEYSTONE_WEBHOOK_CONFIG})
        
        keystone_config=$(cat << EOF
---
apiVersion: v1
clusters:
- cluster:
    certificate-authority: ${CERT_DIR}/ca.crt
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
    client-certificate: ${CERT_DIR}/admin.crt
    client-key: ${CERT_DIR}/admin.key
EOF
)
        echo "${keystone_config}" > "${KEYSTONE_WEBHOOK_CONFIG}.tmp"
        mv "${KEYSTONE_WEBHOOK_CONFIG}.tmp" "${KEYSTONE_WEBHOOK_CONFIG}"
    fi
    
    KUBE_API_ARGS="$KUBE_API_ARGS --authentication-token-webhook-config-file=/etc/kubernetes/keystone_webhook_config.yaml --authorization-webhook-config-file=/etc/kubernetes/keystone_webhook_config.yaml"
    webhook_auth="--authorization-mode=Node,Webhook,RBAC"
    KUBE_API_ARGS=${KUBE_API_ARGS/--authorization-mode=Node,RBAC/$webhook_auth}
fi

# Update API server config
apiserver_config="
KUBE_API_ADDRESS=\"${KUBE_API_ADDRESS}\"
KUBE_SERVICE_ADDRESSES=\"--service-cluster-ip-range=${PORTAL_NETWORK_CIDR}\"
KUBE_API_ARGS=\"${KUBE_API_ARGS}\"
KUBE_ETCD_SERVERS=\"--etcd-servers=http://127.0.0.1:2379\"
"

mkdir -p /etc/kubernetes/
if [ ! -f /etc/kubernetes/apiserver ] || [ "$(cat /etc/kubernetes/apiserver)" != "${apiserver_config}" ]; then
    echo "${apiserver_config}" > /etc/kubernetes/apiserver.tmp
    mv /etc/kubernetes/apiserver.tmp /etc/kubernetes/apiserver
fi

# Configure controller-manager
CONTROLLER_KUBECONFIG=/etc/kubernetes/controller-kubeconfig.yaml

# Check if required certificates exist for controller
if [ ! -f "${CERT_DIR}/controller.crt" ] || [ ! -f "${CERT_DIR}/controller.key" ]; then
    echo "Required controller certificates not found in ${CERT_DIR}"
    exit 1
fi

controller_kubeconfig=$(cat << EOF
apiVersion: v1
clusters:
- cluster:
    certificate-authority: ${CERT_DIR}/ca.crt
    server: https://127.0.0.1:${KUBE_API_PORT}
  name: kubernetes
contexts:
- context:
    cluster: kubernetes
    user: controller
  name: default
current-context: default
kind: Config
preferences: {}
users:
- name: controller
  user:
    as-user-extra: {}
    client-certificate: ${CERT_DIR}/controller.crt
    client-key: ${CERT_DIR}/controller.key
EOF
)

# Write controller kubeconfig if it doesn't exist or content differs
if [ ! -f "${CONTROLLER_KUBECONFIG}" ] || [ "$(cat ${CONTROLLER_KUBECONFIG})" != "${controller_kubeconfig}" ]; then
    mkdir -p $(dirname "${CONTROLLER_KUBECONFIG}")
    echo "${controller_kubeconfig}" > "${CONTROLLER_KUBECONFIG}.tmp"
    mv "${CONTROLLER_KUBECONFIG}.tmp" "${CONTROLLER_KUBECONFIG}"
    chmod 0640 "${CONTROLLER_KUBECONFIG}"
fi

# Configure controller manager arguments
KUBE_CONTROLLER_MANAGER_ARGS="--leader-elect=true"
KUBE_CONTROLLER_MANAGER_ARGS="$KUBE_CONTROLLER_MANAGER_ARGS --cluster-name=${CLUSTER_UUID}"
KUBE_CONTROLLER_MANAGER_ARGS="${KUBE_CONTROLLER_MANAGER_ARGS} --allocate-node-cidrs=true"
KUBE_CONTROLLER_MANAGER_ARGS="${KUBE_CONTROLLER_MANAGER_ARGS} --kubeconfig=${CONTROLLER_KUBECONFIG}"
KUBE_CONTROLLER_MANAGER_ARGS="${KUBE_CONTROLLER_MANAGER_ARGS} --cluster-cidr=${PODS_NETWORK_CIDR}"
KUBE_CONTROLLER_MANAGER_ARGS="$KUBE_CONTROLLER_MANAGER_ARGS $KUBECONTROLLER_OPTIONS"

if [ -n "${ADMISSION_CONTROL_LIST}" ] && [ "${TLS_DISABLED}" == "False" ]; then
    if [ -f "$CERT_DIR/service_account_private.key" ] && [ -f "$CERT_DIR/ca.crt" ]; then
        KUBE_CONTROLLER_MANAGER_ARGS="$KUBE_CONTROLLER_MANAGER_ARGS --service-account-private-key-file=$CERT_DIR/service_account_private.key --root-ca-file=$CERT_DIR/ca.crt"
    fi
fi

if [ "$(echo "${CLOUD_PROVIDER_ENABLED}" | tr '[:upper:]' '[:lower:]')" = "true" ]; then
    KUBE_CONTROLLER_MANAGER_ARGS="$KUBE_CONTROLLER_MANAGER_ARGS --cloud-provider=external"
fi

if [ "$(echo $CERT_MANAGER_API | tr '[:upper:]' '[:lower:]')" = "true" ]; then
    if [ -f "$CERT_DIR/ca.crt" ] && [ -f "$CERT_DIR/ca.key" ]; then
        KUBE_CONTROLLER_MANAGER_ARGS="$KUBE_CONTROLLER_MANAGER_ARGS --cluster-signing-cert-file=$CERT_DIR/ca.crt --cluster-signing-key-file=$CERT_DIR/ca.key"
    fi
fi

KUBE_CONTROLLER_MANAGER_ARGS="${KUBE_CONTROLLER_MANAGER_ARGS} --use-service-account-credentials=true"

# Update controller manager config
controller_config="KUBE_CONTROLLER_MANAGER_ARGS=\"${KUBE_CONTROLLER_MANAGER_ARGS}\""

if [ ! -f /etc/kubernetes/controller-manager ] || [ "$(cat /etc/kubernetes/controller-manager)" != "${controller_config}" ]; then
    echo "${controller_config}" > /etc/kubernetes/controller-manager.tmp
    mv /etc/kubernetes/controller-manager.tmp /etc/kubernetes/controller-manager
fi

# kube-config scheduler 
SCHEDULER_KUBECONFIG=/etc/kubernetes/scheduler-kubeconfig.yaml
cat > ${SCHEDULER_KUBECONFIG} << EOF
apiVersion: v1
clusters:
- cluster:
    certificate-authority: ${CERT_DIR}/ca.crt
    server: https://127.0.0.1:${KUBE_API_PORT}
  name: kubernetes
contexts:
- context:
    cluster: kubernetes
    user: scheduler
  name: default
current-context: default
kind: Config
preferences: {}
users:
- name: scheduler
  user:
    as-user-extra: {}
    client-certificate: ${CERT_DIR}/scheduler.crt
    client-key: ${CERT_DIR}/scheduler.key
EOF
chmod 0640 ${SCHEDULER_KUBECONFIG}


# Add scheduler args
KUBE_SCHEDULER_ARGS="--leader-elect=true"
KUBE_SCHEDULER_ARGS="${KUBE_SCHEDULER_ARGS} --kubeconfig=${SCHEDULER_KUBECONFIG}"

sed -i '
    /^KUBE_SCHEDULER_ARGS=/ s#\(KUBE_SCHEDULER_ARGS\).*#\1="'"${KUBE_SCHEDULER_ARGS}"'"#
' /etc/kubernetes/scheduler


# Add kubelet args
$ssh_cmd mkdir -p /etc/kubernetes/manifests
KUBELET_ARGS=""
KUBELET_ARGS="${KUBELET_ARGS} ${KUBELET_OPTIONS}"


if [ -f /etc/sysconfig/docker ] ; then
    # For using default log-driver, other options should be ignored
    sed -i 's/\-\-log\-driver\=journald//g' /etc/sysconfig/docker
    # json-file is required for conformance.
    # https://docs.docker.com/config/containers/logging/json-file/
    sed -i -E 's/^OPTIONS=("|'"'"')/OPTIONS=\1--log-driver=json-file --log-opt max-size=10m --log-opt max-file=5 /' /etc/sysconfig/docker

    if [ -n "${INSECURE_REGISTRY_URL}" ]; then
        echo "INSECURE_REGISTRY='--insecure-registry ${INSECURE_REGISTRY_URL}'" >> /etc/sysconfig/docker
    fi
fi

KUBELET_ARGS="${KUBELET_ARGS} --node-labels=magnum.openstack.org/role=${NODEGROUP_ROLE}"
KUBELET_ARGS="${KUBELET_ARGS} --node-labels=magnum.openstack.org/nodegroup=${NODEGROUP_NAME}"

KUBELET_KUBECONFIG=/etc/kubernetes/kubelet.conf
cat > ${KUBELET_KUBECONFIG} << EOF
apiVersion: v1
clusters:
- cluster:
    certificate-authority: ${CERT_DIR}/ca.crt
    server: https://127.0.0.1:${KUBE_API_PORT}
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
chmod 0640 ${KUBELET_KUBECONFIG}

KUBELET_ARGS="${KUBELET_ARGS} --kubeconfig ${KUBELET_KUBECONFIG}"

cat > /etc/kubernetes/get_require_kubeconfig.sh << EOF
#!/bin/bash

KUBE_VERSION=\$(kubelet --version | awk '{print \$2}')
min_version=v1.8.0
if [[ "\${min_version}" != \$(echo -e "\${min_version}\n\${KUBE_VERSION}" | sort -s -t. -k 1,1 -k 2,2n -k 3,3n | head -n1) && "\${KUBE_VERSION}" != "devel" ]]; then
    echo "--require-kubeconfig"
fi
EOF
chmod +x /etc/kubernetes/get_require_kubeconfig.sh

# specified cgroup driver
if [ ${CONTAINER_RUNTIME} = "containerd"  ] ; then
    KUBELET_ARGS="${KUBELET_ARGS} --runtime-cgroups=/system.slice/containerd.service"

  # if less than 1.27, use remote runtime flags
  if version_lt $(echo ${KUBE_TAG} | cut -c 2-) 1.27; then
      KUBELET_ARGS="${KUBELET_ARGS} --container-runtime=remote"
      KUBELET_ARGS="${KUBELET_ARGS} --container-runtime-endpoint=unix:///run/containerd/containerd.sock"
  fi

fi

if [ -z "${KUBE_NODE_IP}" ]; then
    KUBE_NODE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
fi
EXTRA_REGISTER_WITH_TAINTS=""
EXTRA_KUBELETCONFIG_PARAMETERS=""
if version_gt $(echo ${KUBE_TAG} | cut -c 2-) 1.21; then
  EXTRA_KUBELETCONFIG_PARAMETERS='containerRuntimeEndpoint: unix:///run/containerd/containerd.sock
featureGates:
  GracefulNodeShutdown: false'
fi

if version_lt $(echo ${KUBE_TAG} | cut -c 2-) 1.23; then
  KUBELET_ARGS="${KUBELET_ARGS} --register-with-taints=node-role.kubernetes.io/master=:NoSchedule"
fi

if [[ ${LEAD_NODE_ROLE_NAME} == "control-plane" ]]; then
EXTRA_REGISTER_WITH_TAINTS='  - effect: "NoSchedule"
    key: "node-role.kubernetes.io/control-plane"'
fi

INSTANCE_ID=$($ssh_cmd curl -s http://169.254.169.254/openstack/latest/meta_data.json | $ssh_cmd jq -r .uuid)

KUBELET_CONFIG=/etc/kubernetes/kubelet-config.yaml
cat > ${KUBELET_CONFIG} << EOF
---
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
authentication:
  anonymous:
    enabled: false
  webhook:
    cacheTTL: 0s
    enabled: true
  x509:
    clientCAFile: "${CERT_DIR}/ca.crt"
authorization:
  mode: Webhook
  webhook:
    cacheAuthorizedTTL: 0s
    cacheUnauthorizedTTL: 0s
cgroupDriver: ${CGROUP_DRIVER}
clusterDNS:
- ${DNS_SERVICE_IP}
clusterDomain: ${DNS_CLUSTER_DOMAIN}
address: ${KUBE_NODE_IP}
failSwapOn: True
port: 10250
readOnlyPort: 0
containerLogMaxFiles: 5
containerLogMaxSize: 10Mi
registerWithTaints:
${EXTRA_REGISTER_WITH_TAINTS}
maxPods: 110
podPidsLimit: -1
providerID: openstack:///${INSTANCE_ID}
resolvConf: /run/systemd/resolve/resolv.conf
volumePluginDir: /var/lib/kubelet/volumeplugins
rotateCertificates: true
tlsCertFile: ${CERT_DIR}/kubelet.crt
tlsPrivateKeyFile: ${CERT_DIR}/kubelet.key
staticPodPath: /etc/kubernetes/manifests
runtimeRequestTimeout: 15m
eventRecordQPS: 5
${EXTRA_KUBELETCONFIG_PARAMETERS}
EOF

KUBELET_ARGS="${KUBELET_ARGS} --config=${KUBELET_CONFIG}"


cat > /etc/kubernetes/kubelet.env <<EOF
KUBELET_ADDRESS="--node-ip=${KUBE_NODE_IP}"
KUBELET_HOSTNAME="--hostname-override=${INSTANCE_NAME}"
KUBELET_ARGS="${KUBELET_ARGS}"
EOF
