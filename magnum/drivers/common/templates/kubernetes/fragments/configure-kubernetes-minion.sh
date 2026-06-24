#!/bin/bash

set +x
. /etc/sysconfig/heat-params
set -x
set -e

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

is_true() {
    [ "$(echo "${1:-false}" | tr '[:upper:]' '[:lower:]')" = "true" ]
}

# During a pure CA rotation the certificates have already been replaced
# and services restarted by rotate-kubernetes-ca-certs-worker.sh.
# Skip the full kubernetes minion reconfiguration to avoid unnecessary
# CNI plugin downloads, service file rewrites, and potential failures
# under the strict shell settings inherited from the rotation script.
if [ -n "${CA_ROTATION_ID:-}" ] && \
   ! is_true "${IS_UPGRADE:-false}" && \
   ! is_true "${IS_RESIZE:-false}"; then
    echo "Pure CA rotation detected – skipping kubernetes minion reconfiguration"
else

echo "configuring kubernetes (minion)"

version_gt() { test "$(printf '%s\n' "$@" | sort -V | head -n 1)" != "$1"; }
version_lt() { test "$(printf '%s\n' "$@" | sort -V | head -n 1)" = "$1"; }

if [ ! -z "$HTTP_PROXY" ]; then
    export HTTP_PROXY
fi

if [ ! -z "$HTTPS_PROXY" ]; then
    export HTTPS_PROXY
fi

if [ ! -z "$NO_PROXY" ]; then
    export NO_PROXY
fi

if [ "$NETWORK_DRIVER" = "flannel" ]; then
    cni_bin_dir="/opt/cni/bin"
    $ssh_cmd mkdir -p "${cni_bin_dir}"

    cni_plugin_path="/srv/magnum/kubernetes/cni"
    $ssh_cmd mkdir -p ${cni_plugin_path}
    $ssh_cmd curl --retry 5 --retry-delay 10 -L https://github.com/containernetworking/plugins/releases/download/${FLANNEL_CNI_TAG}/cni-plugins-linux-amd64-${FLANNEL_CNI_TAG}.tgz -o ${cni_plugin_path}/cni-plugins-linux-amd64-${FLANNEL_CNI_TAG}.tgz
    $ssh_cmd tar -C "${cni_bin_dir}" -xzf ${cni_plugin_path}/cni-plugins-linux-amd64-${FLANNEL_CNI_TAG}.tgz
    $ssh_cmd chmod +x "${cni_bin_dir}"/*
fi

if [ "$NETWORK_DRIVER" = "calico" ]; then
    echo "net.ipv4.conf.all.rp_filter = 1" >> /etc/sysctl.conf
    # NOTE(flwang): The default value for vm.max_map_count is too low, update
    # it to 262144 to meet the minium requirement of Elasticsearch
    echo "vm.max_map_count = 262144" >> /etc/sysctl.conf

    $ssh_cmd sysctl -p
    if [ "$($ssh_cmd systemctl status NetworkManager.service | grep -o "Active: active")" = "Active: active" ]; then
        CALICO_NM=/etc/NetworkManager/conf.d/calico.conf
        [ -f ${CALICO_NM} ] || {
        echo "Writing File: $CALICO_NM"
        mkdir -p $(dirname ${CALICO_NM})
        cat << EOF > ${CALICO_NM}
[keyfile]
unmanaged-devices=interface-name:cali*;interface-name:tunl*
EOF
}
        $ssh_cmd systemctl restart NetworkManager
    fi
elif [ "$NETWORK_DRIVER" = "flannel" ]; then
    $ssh_cmd modprobe -a vxlan br_netfilter
    cat <<EOF > /etc/modules-load.d/flannel.conf
vxlan
br_netfilter
EOF
fi

cat <<EOF > /etc/sysctl.d/k8s_custom.conf
net.ipv4.conf.default.rp_filter=2
net.ipv4.conf.*.rp_filter=2
net.ipv4.conf.all.promote_secondaries = 1
net.ipv4.conf.*.accept_source_route = 1
net.ipv4.ip_unprivileged_port_start = 0
net.ipv4.ping_group_range = 0 2147483647
EOF

mkdir -p /srv/magnum/kubernetes/
mkdir -p /etc/kubernetes
cat > /etc/kubernetes/config <<EOF
KUBE_LOG_LEVEL="--v=3"
EOF

cat > /etc/kubernetes/proxy <<EOF
KUBE_PROXY_ARGS=""
EOF
if [ "$(echo $USE_PODMAN | tr '[:upper:]' '[:lower:]')" == "true" ]; then
    cat > /etc/systemd/system/kubelet.service <<EOF
[Unit]
Description=Kubelet
Wants=rpc-statd.service

[Service]
EnvironmentFile=/etc/sysconfig/heat-params
EnvironmentFile=/etc/kubernetes/config
EnvironmentFile=/etc/kubernetes/kubelet.env
ExecStartPre=/bin/mkdir -p /etc/kubernetes/cni/net.d
ExecStartPre=/bin/mkdir -p /etc/kubernetes/manifests
ExecStartPre=/bin/mkdir -p /var/lib/calico
ExecStartPre=/bin/mkdir -p /var/lib/containerd
ExecStartPre=/bin/mkdir -p /var/lib/docker
ExecStartPre=/bin/mkdir -p /var/lib/kubelet/volumeplugins
ExecStartPre=/bin/mkdir -p /opt/cni/bin
ExecStart=/usr/local/bin/kubelet \\
    \$KUBE_LOG_LEVEL \$KUBELET_API_SERVER \$KUBELET_ADDRESS \$KUBELET_PORT \$KUBELET_HOSTNAME \$KUBELET_ARGS
Delegate=yes
Restart=always
RestartSec=10
TimeoutStartSec=10min
[Install]
WantedBy=multi-user.target
EOF

    cat > /etc/systemd/system/kube-proxy.service <<EOF
[Unit]
Description=kube-proxy via registry.k8s.io/kube-proxy
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
Restart=always
RestartSec=10
TimeoutStartSec=10min
[Install]
WantedBy=multi-user.target
EOF
else
    _prefix=${CONTAINER_INFRA_PREFIX:-docker.io/openstackmagnum/}
    _addtl_mounts=',{"type":"bind","source":"/opt/cni","destination":"/opt/cni","options":["bind","rw","slave","mode=777"]},{"type":"bind","source":"/var/lib/docker","destination":"/var/lib/docker","options":["bind","rw","slave","mode=755"]}'
    mkdir -p /srv/magnum/kubernetes/
    cat > /srv/magnum/kubernetes/install-kubernetes.sh <<EOF
#!/bin/bash -x
atomic install --storage ostree --system --set=ADDTL_MOUNTS='${_addtl_mounts}' --system-package=no --name=kubelet ${_prefix}kubernetes-kubelet:${KUBE_TAG}
atomic install --storage ostree --system --system-package=no --name=kube-proxy ${_prefix}kubernetes-proxy:${KUBE_TAG}
EOF
    chmod +x /srv/magnum/kubernetes/install-kubernetes.sh
    $ssh_cmd "/srv/magnum/kubernetes/install-kubernetes.sh"
fi

CERT_DIR=/etc/kubernetes/certs
ETCD_SERVER_IP=${ETCD_SERVER_IP:-$KUBE_MASTER_IP}
KUBE_PROTOCOL="https"
KUBELET_KUBECONFIG=/etc/kubernetes/kubelet.conf
PROXY_KUBECONFIG=/etc/kubernetes/proxy-config.yaml

if [ "$TLS_DISABLED" = "True" ]; then
    KUBE_PROTOCOL="http"
fi

KUBE_MASTER_URI="$KUBE_PROTOCOL://$KUBE_MASTER_IP:$KUBE_API_PORT"

if [ -z "${KUBE_NODE_IP}" ]; then
    KUBE_NODE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
fi
cat > ${KUBELET_KUBECONFIG} << EOF
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
cat > ${PROXY_KUBECONFIG} << EOF
apiVersion: v1
clusters:
- cluster:
    certificate-authority: ${CERT_DIR}/ca.crt
    server: ${KUBE_MASTER_URI}
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

if [ "$TLS_DISABLED" = "True" ]; then
    sed -i 's/^.*user:$//' ${KUBELET_KUBECONFIG}
    sed -i 's/^.*client-certificate.*$//' ${KUBELET_KUBECONFIG}
    sed -i 's/^.*client-key.*$//' ${KUBELET_KUBECONFIG}
    sed -i 's/^.*certificate-authority.*$//' ${KUBELET_KUBECONFIG}
fi

chmod 0640 ${KUBELET_KUBECONFIG}
chmod 0640 ${PROXY_KUBECONFIG}

sed -i '
    /^KUBE_ALLOW_PRIV=/ s/=.*/="--allow-privileged='"$KUBE_ALLOW_PRIV"'"/
    /^KUBE_ETCD_SERVERS=/ s|=.*|="--etcd-servers=http://'"$ETCD_SERVER_IP"':2379"|
    /^KUBE_MASTER=/ s|=.*|="--master='"$KUBE_MASTER_URI"'"|
' /etc/kubernetes/config

# NOTE:  Kubernetes plugin for Openstack requires that the node name registered
# in the kube-apiserver be the same as the Nova name of the instance, so that
# the plugin can use the name to query for attributes such as IP, etc.
# The hostname of the node is set to be the Nova name of the instance, and
# the option --hostname-override for kubelet uses the hostname to register the node.
# Using any other name will break the load balancer and cinder volume features.
mkdir -p /etc/kubernetes/manifests
KUBELET_ARGS="--kubeconfig ${KUBELET_KUBECONFIG}"

KUBELET_ARGS="${KUBELET_ARGS} --node-labels=magnum.openstack.org/role=${NODEGROUP_ROLE}"
KUBELET_ARGS="${KUBELET_ARGS} --node-labels=magnum.openstack.org/nodegroup=${NODEGROUP_NAME}"
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

if [ ${CONTAINER_RUNTIME} = "containerd"  ] ; then
  KUBELET_ARGS="${KUBELET_ARGS} --runtime-cgroups=/system.slice/containerd.service"

  # if less than 1.27, use remote runtime flags
  if version_lt $(echo ${KUBE_TAG} | cut -c 2-) 1.27; then
      KUBELET_ARGS="${KUBELET_ARGS} --container-runtime=remote"
      KUBELET_ARGS="${KUBELET_ARGS} --container-runtime-endpoint=unix:///run/containerd/containerd.sock"
  fi
fi

auto_healing_enabled=$(echo ${AUTO_HEALING_ENABLED} | tr '[:upper:]' '[:lower:]')
autohealing_controller=$(echo ${AUTO_HEALING_CONTROLLER} | tr '[:upper:]' '[:lower:]')

EXTRA_KUBELETCONFIG_PARAMETERS=""
if version_gt $(echo ${KUBE_TAG} | cut -c 2-) 1.21; then
  EXTRA_KUBELETCONFIG_PARAMETERS='containerRuntimeEndpoint: unix:///run/containerd/containerd.sock
featureGates:
  GracefulNodeShutdown: false'
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


KUBE_PROXY_ARGS="--kubeconfig=${PROXY_KUBECONFIG} --cluster-cidr=${PODS_NETWORK_CIDR} --hostname-override=${INSTANCE_NAME}"
cat > /etc/kubernetes/proxy << EOF
KUBE_PROXY_ARGS="${KUBE_PROXY_ARGS} ${KUBEPROXY_OPTIONS}"
EOF

cat >> /etc/environment <<EOF
KUBERNETES_MASTER=$KUBE_MASTER_URI
EOF
fi
