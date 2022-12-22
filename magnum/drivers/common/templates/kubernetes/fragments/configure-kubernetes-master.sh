set +x
. /etc/sysconfig/heat-params
set -x
set -e

echo "configuring kubernetes (master)"

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

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
$ssh_cmd mkdir -p /opt/cni/bin
$ssh_cmd mkdir -p /etc/cni/net.d/

if [ "$NETWORK_DRIVER" = "calico" ]; then
    echo "net.ipv4.conf.all.rp_filter = 1" >> /etc/sysctl.conf
    $ssh_cmd sysctl -p
    if [ "`systemctl status NetworkManager.service | grep -o "Active: active"`" = "Active: active" ]; then
        CALICO_NM=/etc/NetworkManager/conf.d/calico.conf
        [ -f ${CALICO_NM} ] || {
        echo "Writing File: $CALICO_NM"
        mkdir -p $(dirname ${CALICO_NM})
        cat << EOF > ${CALICO_NM}
[keyfile]
unmanaged-devices=interface-name:cali*;interface-name:tunl*
EOF
}
        systemctl restart NetworkManager
    fi
elif [ "$NETWORK_DRIVER" = "flannel" ]; then
    $ssh_cmd modprobe vxlan
    echo "vxlan" > /etc/modules-load.d/vxlan.conf
fi


KUBE_MASTER_URI="https://127.0.0.1:$KUBE_API_PORT"
mkdir -p /srv/magnum/kubernetes/
cat > /etc/kubernetes/config <<EOF
KUBE_LOGTOSTDERR="--logtostderr=true"
KUBE_LOG_LEVEL="--v=3"
EOF
cat > /etc/kubernetes/kubelet <<EOF
KUBELET_ARGS="--fail-swap-on=false"
EOF

cat > /etc/kubernetes/apiserver <<EOF
KUBE_ETCD_SERVERS="--etcd-servers=http://127.0.0.1:2379,http://127.0.0.1:4001"
KUBE_SERVICE_ADDRESSES="--service-cluster-ip-range=10.254.0.0/16"
KUBE_ADMISSION_CONTROL="--admission-control=NodeRestriction,${ADMISSION_CONTROL_LIST}"
KUBE_API_ARGS=""
EOF

cat > /etc/kubernetes/controller-manager <<EOF
KUBE_CONTROLLER_MANAGER_ARGS=""
EOF
cat > /etc/kubernetes/scheduler<<EOF
KUBE_SCHEDULER_ARGS=""
EOF
cat > /etc/kubernetes/proxy <<EOF
KUBE_PROXY_ARGS=""
EOF


if [ "$(echo $USE_PODMAN | tr '[:upper:]' '[:lower:]')" == "true" ]; then
    cat > /etc/systemd/system/kube-apiserver.service <<EOF
[Unit]
Description=kube-apiserver via Hyperkube
[Service]
EnvironmentFile=/etc/sysconfig/heat-params
EnvironmentFile=/etc/kubernetes/config
EnvironmentFile=/etc/kubernetes/apiserver
ExecStartPre=/bin/mkdir -p /etc/kubernetes/
ExecStartPre=-/usr/bin/podman rm kube-apiserver
ExecStart=/bin/bash -c '/usr/bin/podman run --name kube-apiserver \\
    --net host \\
    --entrypoint /hyperkube \\
    --volume /etc/kubernetes:/etc/kubernetes:ro,z \\
    --volume /usr/lib/os-release:/etc/os-release:ro \\
    --volume /etc/ssl/certs:/etc/ssl/certs:ro \\
    --volume /run:/run \\
    --volume /etc/pki/tls/certs:/usr/share/ca-certificates:ro \\
    \${CONTAINER_INFRA_PREFIX:-\${HYPERKUBE_PREFIX}}hyperkube:\${KUBE_TAG} \\
    kube-apiserver \\
    \$KUBE_LOGTOSTDERR \$KUBE_LOG_LEVEL \$KUBE_ETCD_SERVERS \$KUBE_API_ADDRESS \$KUBELET_PORT \$KUBE_SERVICE_ADDRESSES \$KUBE_ADMISSION_CONTROL \$KUBE_API_ARGS'
ExecStop=-/usr/bin/podman stop kube-apiserver
Delegate=yes
Restart=always
RestartSec=10
TimeoutStartSec=10min
[Install]
WantedBy=multi-user.target
EOF

    cat > /etc/systemd/system/kube-controller-manager.service <<EOF
[Unit]
Description=kube-controller-manager via Hyperkube
[Service]
EnvironmentFile=/etc/sysconfig/heat-params
EnvironmentFile=/etc/kubernetes/config
EnvironmentFile=/etc/kubernetes/controller-manager
ExecStartPre=/bin/mkdir -p /etc/kubernetes/
ExecStartPre=-/usr/bin/podman rm kube-controller-manager
ExecStart=/bin/bash -c '/usr/bin/podman run --name kube-controller-manager \\
    --net host \\
    --entrypoint /hyperkube \\
    --volume /etc/kubernetes:/etc/kubernetes:ro,z \\
    --volume /usr/lib/os-release:/etc/os-release:ro \\
    --volume /etc/ssl/certs:/etc/ssl/certs:ro \\
    --volume /run:/run \\
    --volume /etc/pki/tls/certs:/usr/share/ca-certificates:ro \\
    \${CONTAINER_INFRA_PREFIX:-\${HYPERKUBE_PREFIX}}hyperkube:\${KUBE_TAG} \\
    kube-controller-manager \\
    --secure-port=0 \\
    \$KUBE_LOGTOSTDERR \$KUBE_LOG_LEVEL \$KUBE_MASTER \$KUBE_CONTROLLER_MANAGER_ARGS'
ExecStop=-/usr/bin/podman stop kube-controller-manager
Delegate=yes
Restart=always
RestartSec=10
TimeoutStartSec=10min
[Install]
WantedBy=multi-user.target
EOF

    cat > /etc/systemd/system/kube-scheduler.service <<EOF
[Unit]
Description=kube-scheduler via Hyperkube
[Service]
EnvironmentFile=/etc/sysconfig/heat-params
EnvironmentFile=/etc/kubernetes/config
EnvironmentFile=/etc/kubernetes/scheduler
ExecStartPre=/bin/mkdir -p /etc/kubernetes/
ExecStartPre=-/usr/bin/podman rm kube-scheduler
ExecStart=/bin/bash -c '/usr/bin/podman run --name kube-scheduler \\
    --net host \\
    --entrypoint /hyperkube \\
    --volume /etc/kubernetes:/etc/kubernetes:ro,z \\
    --volume /usr/lib/os-release:/etc/os-release:ro \\
    --volume /etc/ssl/certs:/etc/ssl/certs:ro \\
    --volume /run:/run \\
    --volume /etc/pki/tls/certs:/usr/share/ca-certificates:ro \\
    \${CONTAINER_INFRA_PREFIX:-\${HYPERKUBE_PREFIX}}hyperkube:\${KUBE_TAG} \\
    kube-scheduler \\
    \$KUBE_LOGTOSTDERR \$KUBE_LOG_LEVEL \$KUBE_MASTER \$KUBE_SCHEDULER_ARGS'
ExecStop=-/usr/bin/podman stop kube-scheduler
Delegate=yes
Restart=always
RestartSec=10
TimeoutStartSec=10min
[Install]
WantedBy=multi-user.target
EOF



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
RestartSec=10
TimeoutStartSec=10min
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
atomic install --storage ostree --system --system-package=no --name=kube-apiserver ${_prefix}kubernetes-apiserver:${KUBE_TAG}
atomic install --storage ostree --system --system-package=no --name=kube-controller-manager ${_prefix}kubernetes-controller-manager:${KUBE_TAG}
atomic install --storage ostree --system --system-package=no --name=kube-scheduler ${_prefix}kubernetes-scheduler:${KUBE_TAG}
atomic install --storage ostree --system --system-package=no --name=kube-proxy ${_prefix}kubernetes-proxy:${KUBE_TAG}
EOF
    chmod +x /srv/magnum/kubernetes/install-kubernetes.sh
    $ssh_cmd "/srv/magnum/kubernetes/install-kubernetes.sh"
fi

CERT_DIR=/etc/kubernetes/certs

# kube-proxy config
PROXY_KUBECONFIG=/etc/kubernetes/proxy-kubeconfig.yaml
KUBE_PROXY_ARGS="--kubeconfig=${PROXY_KUBECONFIG} --cluster-cidr=${PODS_NETWORK_CIDR} --hostname-override=${INSTANCE_NAME}"
cat > /etc/kubernetes/proxy << EOF
KUBE_PROXY_ARGS="${KUBE_PROXY_ARGS} ${KUBEPROXY_OPTIONS}"
EOF

cat << EOF >> ${PROXY_KUBECONFIG}
apiVersion: v1
clusters:
- cluster:
    certificate-authority: ${CERT_DIR}/ca.crt
    server: ${KUBE_MASTER_URI}
  name: ${CLUSTER_UUID}
contexts:
- context:
    cluster: ${CLUSTER_UUID}
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

sed -i '
    /^KUBE_ALLOW_PRIV=/ s/=.*/="--allow-privileged='"$KUBE_ALLOW_PRIV"'"/
' /etc/kubernetes/config

KUBE_API_ARGS="--runtime-config=api/all=true"
KUBE_API_ARGS="$KUBE_API_ARGS --allow-privileged=$KUBE_ALLOW_PRIV"
KUBE_API_ARGS="$KUBE_API_ARGS --kubelet-preferred-address-types=InternalIP,Hostname,ExternalIP"
KUBE_API_ARGS="$KUBE_API_ARGS $KUBEAPI_OPTIONS"
KUBE_API_ADDRESS="--bind-address=0.0.0.0 --secure-port=$KUBE_API_PORT"
KUBE_API_ARGS="$KUBE_API_ARGS --authorization-mode=Node,RBAC --tls-cert-file=$CERT_DIR/server.crt"
KUBE_API_ARGS="$KUBE_API_ARGS --tls-private-key-file=$CERT_DIR/server.key"
KUBE_API_ARGS="$KUBE_API_ARGS --client-ca-file=$CERT_DIR/ca.crt"
KUBE_API_ARGS="$KUBE_API_ARGS --service-account-key-file=${CERT_DIR}/service_account.key"
KUBE_API_ARGS="$KUBE_API_ARGS --service-account-signing-key-file=${CERT_DIR}/service_account_private.key"
KUBE_API_ARGS="$KUBE_API_ARGS --service-account-issuer=https://kubernetes.default.svc.cluster.local"
KUBE_API_ARGS="$KUBE_API_ARGS --kubelet-certificate-authority=${CERT_DIR}/ca.crt --kubelet-client-certificate=${CERT_DIR}/server.crt --kubelet-client-key=${CERT_DIR}/server.key"
# Allow for metrics-server/aggregator communication
KUBE_API_ARGS="${KUBE_API_ARGS} \
    --proxy-client-cert-file=${CERT_DIR}/front-proxy/server.crt \
    --proxy-client-key-file=${CERT_DIR}/front-proxy/server.key \
    --requestheader-allowed-names=front-proxy,kube,kubernetes \
    --requestheader-client-ca-file=${CERT_DIR}/front-proxy/ca.crt \
    --requestheader-extra-headers-prefix=X-Remote-Extra- \
    --requestheader-group-headers=X-Remote-Group \
    --requestheader-username-headers=X-Remote-User"

KUBE_ADMISSION_CONTROL=""
if [ -n "${ADMISSION_CONTROL_LIST}" ] && [ "${TLS_DISABLED}" == "False" ]; then
    KUBE_ADMISSION_CONTROL="--admission-control=NodeRestriction,${ADMISSION_CONTROL_LIST}"
fi

if [ "$(echo "${CLOUD_PROVIDER_ENABLED}" | tr '[:upper:]' '[:lower:]')" = "true" ]; then
    KUBE_API_ARGS="$KUBE_API_ARGS --cloud-provider=external"
fi

if [ "$KEYSTONE_AUTH_ENABLED" == "True" ]; then
    KEYSTONE_WEBHOOK_CONFIG=/etc/kubernetes/keystone_webhook_config.yaml

    [ -f ${KEYSTONE_WEBHOOK_CONFIG} ] || {
echo "Writing File: $KEYSTONE_WEBHOOK_CONFIG"
mkdir -p $(dirname ${KEYSTONE_WEBHOOK_CONFIG})
cat << EOF > ${KEYSTONE_WEBHOOK_CONFIG}
---
apiVersion: v1
kind: Config
preferences: {}
clusters:
  - cluster:
      insecure-skip-tls-verify: true
      server: https://127.0.0.1:8443/webhook
    name: webhook
users:
  - name: webhook
contexts:
  - context:
      cluster: webhook
      user: webhook
    name: webhook
current-context: webhook
EOF
}
    KUBE_API_ARGS="$KUBE_API_ARGS --authentication-token-webhook-config-file=/etc/kubernetes/keystone_webhook_config.yaml --authorization-webhook-config-file=/etc/kubernetes/keystone_webhook_config.yaml"
    webhook_auth="--authorization-mode=Node,Webhook,RBAC"
    KUBE_API_ARGS=${KUBE_API_ARGS/--authorization-mode=Node,RBAC/$webhook_auth}
fi

sed -i '
    /^KUBE_API_ADDRESS=/ s/=.*/="'"${KUBE_API_ADDRESS}"'"/
    /^KUBE_SERVICE_ADDRESSES=/ s|=.*|="--service-cluster-ip-range='"$PORTAL_NETWORK_CIDR"'"|
    /^KUBE_API_ARGS=/ s|=.*|="'"${KUBE_API_ARGS}"'"|
    /^KUBE_ETCD_SERVERS=/ s/=.*/="--etcd-servers=http:\/\/127.0.0.1:2379"/
    /^KUBE_ADMISSION_CONTROL=/ s/=.*/="'"${KUBE_ADMISSION_CONTROL}"'"/
' /etc/kubernetes/apiserver

ADMIN_KUBECONFIG=/etc/kubernetes/admin.conf
cat << EOF >> ${ADMIN_KUBECONFIG}
apiVersion: v1
clusters:
- cluster:
    certificate-authority: ${CERT_DIR}/ca.crt
    server: ${KUBE_MASTER_URI}
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
echo "export KUBECONFIG=${ADMIN_KUBECONFIG}" >> /etc/bashrc
chown root:root ${ADMIN_KUBECONFIG}
chmod 600 ${ADMIN_KUBECONFIG}
export KUBECONFIG=${ADMIN_KUBECONFIG}

# Add controller manager args
KUBE_CONTROLLER_MANAGER_ARGS="--leader-elect=true --kubeconfig=/etc/kubernetes/admin.conf"
KUBE_CONTROLLER_MANAGER_ARGS="$KUBE_CONTROLLER_MANAGER_ARGS --cluster-name=${CLUSTER_UUID}"
KUBE_CONTROLLER_MANAGER_ARGS="${KUBE_CONTROLLER_MANAGER_ARGS} --allocate-node-cidrs=true"
KUBE_CONTROLLER_MANAGER_ARGS="${KUBE_CONTROLLER_MANAGER_ARGS} --cluster-cidr=${PODS_NETWORK_CIDR}"
KUBE_CONTROLLER_MANAGER_ARGS="$KUBE_CONTROLLER_MANAGER_ARGS $KUBECONTROLLER_OPTIONS"
if [ -n "${ADMISSION_CONTROL_LIST}" ] && [ "${TLS_DISABLED}" == "False" ]; then
    KUBE_CONTROLLER_MANAGER_ARGS="$KUBE_CONTROLLER_MANAGER_ARGS --service-account-private-key-file=$CERT_DIR/service_account_private.key --root-ca-file=$CERT_DIR/ca.crt"
fi

if [ "$(echo "${CLOUD_PROVIDER_ENABLED}" | tr '[:upper:]' '[:lower:]')" = "true" ]; then
    KUBE_CONTROLLER_MANAGER_ARGS="$KUBE_CONTROLLER_MANAGER_ARGS --cloud-provider=external"
    if [ "$(echo "${VOLUME_DRIVER}" | tr '[:upper:]' '[:lower:]')" = "cinder" ] && [ "$(echo "${CINDER_CSI_ENABLED}" | tr '[:upper:]' '[:lower:]')" != "true" ]; then
        KUBE_CONTROLLER_MANAGER_ARGS="$KUBE_CONTROLLER_MANAGER_ARGS --external-cloud-volume-plugin=openstack --cloud-config=/etc/kubernetes/cloud-config"
    fi
fi


if [ "$(echo $CERT_MANAGER_API | tr '[:upper:]' '[:lower:]')" = "true" ]; then
    KUBE_CONTROLLER_MANAGER_ARGS="$KUBE_CONTROLLER_MANAGER_ARGS --cluster-signing-cert-file=$CERT_DIR/ca.crt --cluster-signing-key-file=$CERT_DIR/ca.key"
fi

sed -i '
    /^KUBELET_ADDRESSES=/ s/=.*/="--machines='""'"/
    /^KUBE_CONTROLLER_MANAGER_ARGS=/ s#\(KUBE_CONTROLLER_MANAGER_ARGS\).*#\1="'"${KUBE_CONTROLLER_MANAGER_ARGS}"'"#
' /etc/kubernetes/controller-manager

sed -i '/^KUBE_SCHEDULER_ARGS=/ s#=.*#="--leader-elect=true --kubeconfig=/etc/kubernetes/admin.conf"#' /etc/kubernetes/scheduler

$ssh_cmd mkdir -p /etc/kubernetes/manifests
KUBELET_ARGS="--register-node=true --pod-manifest-path=/etc/kubernetes/manifests --hostname-override=${INSTANCE_NAME}"
KUBELET_ARGS="${KUBELET_ARGS} --pod-infra-container-image=${CONTAINER_INFRA_PREFIX:-gcr.io/google_containers/}pause:3.1"
KUBELET_ARGS="${KUBELET_ARGS} --cluster_dns=${DNS_SERVICE_IP} --cluster_domain=${DNS_CLUSTER_DOMAIN}"
KUBELET_ARGS="${KUBELET_ARGS} --resolv-conf=/run/systemd/resolve/resolv.conf"
KUBELET_ARGS="${KUBELET_ARGS} --volume-plugin-dir=/var/lib/kubelet/volumeplugins"
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

KUBELET_ARGS="${KUBELET_ARGS} --register-with-taints=node-role.kubernetes.io/master=:NoSchedule"
KUBELET_ARGS="${KUBELET_ARGS} --node-labels=magnum.openstack.org/role=${NODEGROUP_ROLE}"
KUBELET_ARGS="${KUBELET_ARGS} --node-labels=magnum.openstack.org/nodegroup=${NODEGROUP_NAME}"

KUBELET_KUBECONFIG=/etc/kubernetes/kubelet-config.yaml
cat << EOF >> ${KUBELET_KUBECONFIG}
apiVersion: v1
clusters:
- cluster:
    certificate-authority: ${CERT_DIR}/ca.crt
    server: ${KUBE_MASTER_URI}
  name: ${CLUSTER_UUID}
contexts:
- context:
    cluster: ${CLUSTER_UUID}
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

cat > /etc/kubernetes/get_require_kubeconfig.sh << EOF
#!/bin/bash

KUBE_VERSION=\$(kubelet --version | awk '{print \$2}')
min_version=v1.8.0
if [[ "\${min_version}" != \$(echo -e "\${min_version}\n\${KUBE_VERSION}" | sort -s -t. -k 1,1 -k 2,2n -k 3,3n | head -n1) && "\${KUBE_VERSION}" != "devel" ]]; then
    echo "--require-kubeconfig"
fi
EOF
chmod +x /etc/kubernetes/get_require_kubeconfig.sh

KUBELET_ARGS="${KUBELET_ARGS} --client-ca-file=${CERT_DIR}/ca.crt --tls-cert-file=${CERT_DIR}/kubelet.crt --tls-private-key-file=${CERT_DIR}/kubelet.key --kubeconfig ${KUBELET_KUBECONFIG}"

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

if [ -z "${KUBE_NODE_IP}" ]; then
    KUBE_NODE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
fi

KUBELET_ARGS="${KUBELET_ARGS} --address=${KUBE_NODE_IP} --port=10250 --read-only-port=0 --anonymous-auth=false --authorization-mode=Webhook --authentication-token-webhook=true"

sed -i '
/^KUBELET_ADDRESS=/ s/=.*/=""/
/^KUBELET_HOSTNAME=/ s/=.*/=""/
/^KUBELET_ARGS=/ s|=.*|="'"${KUBELET_ARGS}"'"|
' /etc/kubernetes/kubelet
