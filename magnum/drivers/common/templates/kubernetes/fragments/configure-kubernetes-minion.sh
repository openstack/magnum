set +x
. /etc/sysconfig/heat-params
set -x
set -e

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

echo "configuring kubernetes (minion)"

if [ ! -z "$HTTP_PROXY" ]; then
    export HTTP_PROXY
fi

if [ ! -z "$HTTPS_PROXY" ]; then
    export HTTPS_PROXY
fi

if [ ! -z "$NO_PROXY" ]; then
    export NO_PROXY
fi

$ssh_cmd rm -rf /etc/cni/net.d/*
$ssh_cmd rm -rf /var/lib/cni/*
$ssh_cmd rm -rf /opt/cni/*
$ssh_cmd mkdir -p /opt/cni
$ssh_cmd mkdir -p /opt/cni/bin
$ssh_cmd mkdir -p /etc/cni/net.d/
_addtl_mounts=',{"type":"bind","source":"/opt/cni","destination":"/opt/cni","options":["bind","rw","slave","mode=777"]},{"type":"bind","source":"/var/lib/docker","destination":"/var/lib/docker","options":["bind","rw","slave","mode=755"]}'

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
    $ssh_cmd modprobe vxlan
    echo "vxlan" > /etc/modules-load.d/vxlan.conf
fi

mkdir -p /srv/magnum/kubernetes/
cat > /etc/kubernetes/config <<EOF
KUBE_LOGTOSTDERR="--logtostderr=true"
KUBE_LOG_LEVEL="--v=3"
EOF
cat > /etc/kubernetes/kubelet <<EOF
KUBELET_ARGS="--fail-swap-on=false"
EOF
cat > /etc/kubernetes/proxy <<EOF
KUBE_PROXY_ARGS=""
EOF
if [ "$(echo $USE_PODMAN | tr '[:upper:]' '[:lower:]')" == "true" ]; then
    cat > /etc/systemd/system/kubelet.service <<EOF
[Unit]
Description=Kubelet via Hyperkube (System Container)
Wants=rpc-statd.service

[Service]
EnvironmentFile=/etc/sysconfig/heat-params
EnvironmentFile=/etc/kubernetes/config
EnvironmentFile=/etc/kubernetes/kubelet
ExecStartPre=/bin/mkdir -p /etc/kubernetes/cni/net.d
ExecStartPre=/bin/mkdir -p /etc/kubernetes/manifests
ExecStartPre=/bin/mkdir -p /var/lib/calico
ExecStartPre=/bin/mkdir -p /var/lib/containerd
ExecStartPre=/bin/mkdir -p /var/lib/docker
ExecStartPre=/bin/mkdir -p /var/lib/kubelet/volumeplugins
ExecStartPre=/bin/mkdir -p /opt/cni/bin
ExecStartPre=-/usr/bin/podman rm kubelet
ExecStart=/bin/bash -c '/usr/bin/podman run --name kubelet \\
    --privileged \\
    --pid host \\
    --network host \\
    --entrypoint /hyperkube \\
    --volume /:/rootfs:rslave,ro \\
    --volume /etc/cni/net.d:/etc/cni/net.d:ro,z \\
    --volume /etc/kubernetes:/etc/kubernetes:ro,z \\
    --volume /usr/lib/os-release:/usr/lib/os-release:ro \\
    --volume /etc/ssl/certs:/etc/ssl/certs:ro \\
    --volume /lib/modules:/lib/modules:ro \\
    --volume /run:/run \\
    --volume /dev:/dev \\
    --volume /sys/fs/cgroup:/sys/fs/cgroup \\
    --volume /etc/pki/tls/certs:/usr/share/ca-certificates:ro \\
    --volume /var/lib/calico:/var/lib/calico \\
    --volume /var/lib/docker:/var/lib/docker \\
    --volume /var/lib/containerd:/var/lib/containerd \\
    --volume /var/lib/kubelet:/var/lib/kubelet:rshared,z \\
    --volume /var/log:/var/log \\
    --volume /var/run:/var/run \\
    --volume /var/run/lock:/var/run/lock:z \\
    --volume /opt/cni/bin:/opt/cni/bin:z \\
    --volume /etc/machine-id:/etc/machine-id \\
    \${CONTAINER_INFRA_PREFIX:-\${HYPERKUBE_PREFIX}}hyperkube:\${KUBE_TAG} \\
    kubelet \\
    \$KUBE_LOGTOSTDERR \$KUBE_LOG_LEVEL \$KUBELET_API_SERVER \$KUBELET_ADDRESS \$KUBELET_PORT \$KUBELET_HOSTNAME \$KUBELET_ARGS'
ExecStop=-/usr/bin/podman stop kubelet
Delegate=yes
Restart=always
TimeoutStartSec=10min
RestartSec=10
[Install]
WantedBy=multi-user.target
EOF

    cat > /etc/systemd/system/kube-proxy.service <<EOF
[Unit]
Description=kube-proxy via Hyperkube
[Service]
EnvironmentFile=/etc/sysconfig/heat-params
EnvironmentFile=/etc/kubernetes/config
EnvironmentFile=/etc/kubernetes/proxy
ExecStartPre=/bin/mkdir -p /etc/kubernetes/
ExecStartPre=-/usr/bin/podman rm kube-proxy
ExecStart=/bin/bash -c '/usr/bin/podman run --name kube-proxy \\
    --privileged \\
    --net host \\
    --entrypoint /hyperkube \\
    --volume /etc/kubernetes:/etc/kubernetes:ro,z \\
    --volume /usr/lib/os-release:/etc/os-release:ro \\
    --volume /etc/ssl/certs:/etc/ssl/certs:ro \\
    --volume /run:/run \\
    --volume /sys/fs/cgroup:/sys/fs/cgroup \\
    --volume /lib/modules:/lib/modules:ro \\
    --volume /etc/pki/tls/certs:/usr/share/ca-certificates:ro \\
    \${CONTAINER_INFRA_PREFIX:-\${HYPERKUBE_PREFIX}}hyperkube:\${KUBE_TAG} \\
    kube-proxy \\
    \$KUBE_LOGTOSTDERR \$KUBE_LOG_LEVEL \$KUBE_MASTER \$KUBE_PROXY_ARGS'
ExecStop=-/usr/bin/podman stop kube-proxy
Delegate=yes
Restart=always
TimeoutStartSec=10min
RestartSec=10
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
KUBELET_KUBECONFIG=/etc/kubernetes/kubelet-config.yaml
PROXY_KUBECONFIG=/etc/kubernetes/proxy-config.yaml

if [ "$TLS_DISABLED" = "True" ]; then
    KUBE_PROTOCOL="http"
fi

KUBE_MASTER_URI="$KUBE_PROTOCOL://$KUBE_MASTER_IP:$KUBE_API_PORT"

if [ -z "${KUBE_NODE_IP}" ]; then
    KUBE_NODE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
fi
cat << EOF >> ${KUBELET_KUBECONFIG}
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
cat << EOF >> ${PROXY_KUBECONFIG}
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
KUBELET_ARGS="--pod-manifest-path=/etc/kubernetes/manifests --kubeconfig ${KUBELET_KUBECONFIG} --hostname-override=${INSTANCE_NAME}"
KUBELET_ARGS="${KUBELET_ARGS} --address=${KUBE_NODE_IP} --port=10250 --read-only-port=0 --anonymous-auth=false --authorization-mode=Webhook --authentication-token-webhook=true"
KUBELET_ARGS="${KUBELET_ARGS} --cluster_dns=${DNS_SERVICE_IP} --cluster_domain=${DNS_CLUSTER_DOMAIN}"
KUBELET_ARGS="${KUBELET_ARGS} --resolv-conf=/run/systemd/resolve/resolv.conf"
KUBELET_ARGS="${KUBELET_ARGS} --volume-plugin-dir=/var/lib/kubelet/volumeplugins"
KUBELET_ARGS="${KUBELET_ARGS} --node-labels=magnum.openstack.org/role=${NODEGROUP_ROLE}"
KUBELET_ARGS="${KUBELET_ARGS} --node-labels=magnum.openstack.org/nodegroup=${NODEGROUP_NAME}"
KUBELET_ARGS="${KUBELET_ARGS} ${KUBELET_OPTIONS}"

if [ "$(echo "${CLOUD_PROVIDER_ENABLED}" | tr '[:upper:]' '[:lower:]')" = "true" ]; then
    KUBELET_ARGS="${KUBELET_ARGS} --cloud-provider=external"
fi

if [ -f /etc/sysconfig/docker ] ; then
    # For using default log-driver, other options should be ignored
    sed -i 's/\-\-log\-driver\=journald//g' /etc/sysconfig/docker
    # json-file is required for conformance.
    # https://docs.docker.com/config/containers/logging/json-file/
    DOCKER_OPTIONS="--log-driver=json-file --log-opt max-size=10m --log-opt max-file=5"
    if [ -n "${INSECURE_REGISTRY_URL}" ]; then
        DOCKER_OPTIONS="${DOCKER_OPTIONS} --insecure-registry ${INSECURE_REGISTRY_URL}"
    fi
    sed -i -E 's/^OPTIONS=("|'"'"')/OPTIONS=\1'"${DOCKER_OPTIONS}"' /' /etc/sysconfig/docker
fi

KUBELET_ARGS="${KUBELET_ARGS} --pod-infra-container-image=${CONTAINER_INFRA_PREFIX:-gcr.io/google_containers/}pause:3.1"

KUBELET_ARGS="${KUBELET_ARGS} --client-ca-file=${CERT_DIR}/ca.crt --tls-cert-file=${CERT_DIR}/kubelet.crt --tls-private-key-file=${CERT_DIR}/kubelet.key"

# specified cgroup driver
KUBELET_ARGS="${KUBELET_ARGS} --cgroup-driver=${CGROUP_DRIVER}"
if [ ${CONTAINER_RUNTIME} = "containerd"  ] ; then
    KUBELET_ARGS="${KUBELET_ARGS} --runtime-cgroups=/system.slice/containerd.service"
    KUBELET_ARGS="${KUBELET_ARGS} --container-runtime=remote"
    KUBELET_ARGS="${KUBELET_ARGS} --runtime-request-timeout=15m"
    KUBELET_ARGS="${KUBELET_ARGS} --container-runtime-endpoint=unix:///run/containerd/containerd.sock"
else
    KUBELET_ARGS="${KUBELET_ARGS} --network-plugin=cni --cni-conf-dir=/etc/cni/net.d --cni-bin-dir=/opt/cni/bin"
fi

auto_healing_enabled=$(echo ${AUTO_HEALING_ENABLED} | tr '[:upper:]' '[:lower:]')
autohealing_controller=$(echo ${AUTO_HEALING_CONTROLLER} | tr '[:upper:]' '[:lower:]')
if [[ "${auto_healing_enabled}" = "true" && "${autohealing_controller}" = "draino" ]]; then
    KUBELET_ARGS="${KUBELET_ARGS} --node-labels=draino-enabled=true"
fi


sed -i '
    /^KUBELET_ADDRESS=/ s/=.*/="--address=0.0.0.0"/
    /^KUBELET_HOSTNAME=/ s/=.*/=""/
    s/^KUBELET_API_SERVER=.*$//
    /^KUBELET_ARGS=/ s|=.*|="'"${KUBELET_ARGS}"'"|
' /etc/kubernetes/kubelet

KUBE_PROXY_ARGS="--kubeconfig=${PROXY_KUBECONFIG} --cluster-cidr=${PODS_NETWORK_CIDR} --hostname-override=${INSTANCE_NAME}"
cat > /etc/kubernetes/proxy << EOF
KUBE_PROXY_ARGS="${KUBE_PROXY_ARGS} ${KUBEPROXY_OPTIONS}"
EOF

cat >> /etc/environment <<EOF
KUBERNETES_MASTER=$KUBE_MASTER_URI
EOF
