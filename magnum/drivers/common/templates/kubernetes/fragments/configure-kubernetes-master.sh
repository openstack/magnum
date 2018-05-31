#!/bin/sh -x

. /etc/sysconfig/heat-params

echo "configuring kubernetes (master)"

_prefix=${CONTAINER_INFRA_PREFIX:-docker.io/openstackmagnum/}

# TODO(flwang): We should revisit this part to figure out if it's possible to
# only run the calico-node container as a systemd service before starting the
# minion nodes.
if [ "$NETWORK_DRIVER" = "calico" ]; then
    mkdir -p /opt/cni
    _addtl_mounts=',{"type":"bind","source":"/opt/cni","destination":"/opt/cni","options":["bind","rw","slave","mode=777"]}'
    atomic install --storage ostree --system --set=ADDTL_MOUNTS=${_addtl_mounts} --system-package=no --name=kubelet ${_prefix}kubernetes-kubelet:${KUBE_TAG}
fi
atomic install --storage ostree --system --system-package=no --name=kube-apiserver ${_prefix}kubernetes-apiserver:${KUBE_TAG}
atomic install --storage ostree --system --system-package=no --name=kube-controller-manager ${_prefix}kubernetes-controller-manager:${KUBE_TAG}
atomic install --storage ostree --system --system-package=no --name=kube-scheduler ${_prefix}kubernetes-scheduler:${KUBE_TAG}
if [ "$NETWORK_DRIVER" = "flannel" ]; then
    atomic install --storage ostree --system --system-package=no \
    --name=flanneld ${_prefix}flannel:${FLANNEL_TAG}
fi

sed -i '
    /^KUBE_ALLOW_PRIV=/ s/=.*/="--allow-privileged='"$KUBE_ALLOW_PRIV"'"/
    /^KUBE_MASTER=/ s|=.*|="--master=http://127.0.0.1:8080"|
' /etc/kubernetes/config

CERT_DIR=/etc/kubernetes/certs

KUBE_API_ARGS="--runtime-config=api/all=true"
KUBE_API_ARGS="$KUBE_API_ARGS --kubelet-preferred-address-types=InternalIP,Hostname,ExternalIP"
KUBE_API_ARGS="$KUBE_API_ARGS $KUBEAPI_OPTIONS"
if [ "$TLS_DISABLED" == "True" ]; then
    KUBE_API_ADDRESS="--insecure-bind-address=0.0.0.0 --insecure-port=$KUBE_API_PORT"
else
    KUBE_API_ADDRESS="--bind-address=0.0.0.0 --secure-port=$KUBE_API_PORT"
    # insecure port is used internaly
    KUBE_API_ADDRESS="$KUBE_API_ADDRESS --insecure-bind-address=127.0.0.1 --insecure-port=8080"
    KUBE_API_ARGS="$KUBE_API_ARGS --authorization-mode=Node,RBAC --tls-cert-file=$CERT_DIR/server.crt"
    KUBE_API_ARGS="$KUBE_API_ARGS --tls-private-key-file=$CERT_DIR/server.key"
    KUBE_API_ARGS="$KUBE_API_ARGS --client-ca-file=$CERT_DIR/ca.crt"
    KUBE_API_ARGS="$KUBE_API_ARGS --tls-ca-file=${CERT_DIR}/ca.crt"
    KUBE_API_ARGS="$KUBE_API_ARGS --service-account-key-file=${CERT_DIR}/server.key"
    KUBE_API_ARGS="$KUBE_API_ARGS --kubelet-certificate-authority=${CERT_DIR}/ca.crt --kubelet-client-certificate=${CERT_DIR}/server.crt --kubelet-client-key=${CERT_DIR}/server.key --kubelet-https=true"
fi

KUBE_ADMISSION_CONTROL=""
if [ -n "${ADMISSION_CONTROL_LIST}" ] && [ "${TLS_DISABLED}" == "False" ]; then
    KUBE_ADMISSION_CONTROL="--admission-control=NodeRestriction,${ADMISSION_CONTROL_LIST}"
fi

if [ -n "$TRUST_ID" ]; then
    KUBE_API_ARGS="$KUBE_API_ARGS --cloud-config=/etc/kubernetes/kube_openstack_config --cloud-provider=openstack"
fi

sed -i '
    /^KUBE_API_ADDRESS=/ s/=.*/="'"${KUBE_API_ADDRESS}"'"/
    /^KUBE_SERVICE_ADDRESSES=/ s|=.*|="--service-cluster-ip-range='"$PORTAL_NETWORK_CIDR"'"|
    /^KUBE_API_ARGS=/ s|=.*|="'"${KUBE_API_ARGS}"'"|
    /^KUBE_ETCD_SERVERS=/ s/=.*/="--etcd-servers=http:\/\/127.0.0.1:2379"/
    /^KUBE_ADMISSION_CONTROL=/ s/=.*/="'"${KUBE_ADMISSION_CONTROL}"'"/
' /etc/kubernetes/apiserver


# Add controller manager args
KUBE_CONTROLLER_MANAGER_ARGS="--leader-elect=true"
KUBE_CONTROLLER_MANAGER_ARGS="$KUBE_CONTROLLER_MANAGER_ARGS $KUBECONTROLLER_OPTIONS"
if [ -n "${ADMISSION_CONTROL_LIST}" ] && [ "${TLS_DISABLED}" == "False" ]; then
    KUBE_CONTROLLER_MANAGER_ARGS="$KUBE_CONTROLLER_MANAGER_ARGS --service-account-private-key-file=$CERT_DIR/server.key --root-ca-file=$CERT_DIR/ca.crt"
fi

if [ -n "$TRUST_ID" ]; then
    KUBE_CONTROLLER_MANAGER_ARGS="$KUBE_CONTROLLER_MANAGER_ARGS --cloud-config=/etc/kubernetes/kube_openstack_config --cloud-provider=openstack"
fi

if [ "$(echo $CERT_MANAGER_API | tr '[:upper:]' '[:lower:]')" = "true" ]; then
    KUBE_CONTROLLER_MANAGER_ARGS="$KUBE_CONTROLLER_MANAGER_ARGS --cluster-signing-cert-file=$CERT_DIR/ca.crt --cluster-signing-key-file=$CERT_DIR/ca.key"
fi

sed -i '
    /^KUBELET_ADDRESSES=/ s/=.*/="--machines='""'"/
    /^KUBE_CONTROLLER_MANAGER_ARGS=/ s#\(KUBE_CONTROLLER_MANAGER_ARGS\).*#\1="'"${KUBE_CONTROLLER_MANAGER_ARGS}"'"#
' /etc/kubernetes/controller-manager

sed -i '/^KUBE_SCHEDULER_ARGS=/ s/=.*/="--leader-elect=true"/' /etc/kubernetes/scheduler

HOSTNAME_OVERRIDE=$(hostname --short | sed 's/\.novalocal//')
KUBELET_ARGS="--register-node=true --register-schedulable=false --pod-manifest-path=/etc/kubernetes/manifests --cadvisor-port=0 --hostname-override=${HOSTNAME_OVERRIDE}"
KUBELET_ARGS="${KUBELET_ARGS} --cluster_dns=${DNS_SERVICE_IP} --cluster_domain=${DNS_CLUSTER_DOMAIN}"
KUBELET_ARGS="${KUBELET_ARGS} ${KUBELET_OPTIONS}"

# For using default log-driver, other options should be ignored
sed -i 's/\-\-log\-driver\=journald//g' /etc/sysconfig/docker

if [ -n "${INSECURE_REGISTRY_URL}" ]; then
    echo "INSECURE_REGISTRY='--insecure-registry ${INSECURE_REGISTRY_URL}'" >> /etc/sysconfig/docker
fi

if [ "$NETWORK_DRIVER" = "calico" ]; then
    KUBELET_ARGS="${KUBELET_ARGS} --network-plugin=cni --cni-conf-dir=/etc/cni/net.d --cni-bin-dir=/opt/cni/bin --register-with-taints=CriticalAddonsOnly=True:NoSchedule,dedicated=master:NoSchedule"

    KUBELET_KUBECONFIG=/etc/kubernetes/kubelet-config.yaml
    HOSTNAME_OVERRIDE=$(hostname --short | sed 's/\.novalocal//')
    cat << EOF >> ${KUBELET_KUBECONFIG}
apiVersion: v1
clusters:
- cluster:
    certificate-authority: ${CERT_DIR}/ca.crt
    server: http://127.0.0.1:8080
  name: kubernetes
contexts:
- context:
    cluster: kubernetes
    user: system:node:${HOSTNAME_OVERRIDE}
  name: default
current-context: default
kind: Config
preferences: {}
users:
- name: system:node:${HOSTNAME_OVERRIDE}
  user:
    as-user-extra: {}
    client-certificate: ${CERT_DIR}/server.crt
    client-key: ${CERT_DIR}/server.key
EOF

    cat > /etc/kubernetes/get_require_kubeconfig.sh <<EOF
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

    systemctl disable docker
    if cat /usr/lib/systemd/system/docker.service | grep 'native.cgroupdriver'; then
            cp /usr/lib/systemd/system/docker.service /etc/systemd/system/
            sed -i "s/\(native.cgroupdriver=\)\w\+/\1$CGROUP_DRIVER/" \
                    /etc/systemd/system/docker.service
    else
            cat > /etc/systemd/system/docker.service.d/cgroupdriver.conf << EOF
ExecStart=---exec-opt native.cgroupdriver=$CGROUP_DRIVER
EOF

    fi

    systemctl daemon-reload
    systemctl enable docker

    if [ -z "${KUBE_NODE_IP}" ]; then
        KUBE_NODE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
    fi

    KUBELET_ARGS="${KUBELET_ARGS} --address=${KUBE_NODE_IP} --port=10250 --read-only-port=0 --anonymous-auth=false --authorization-mode=Webhook --authentication-token-webhook=true"

    sed -i '
    /^KUBELET_ADDRESS=/ s/=.*/="--address=${KUBE_NODE_IP}"/
    /^KUBELET_HOSTNAME=/ s/=.*/=""/
    /^KUBELET_ARGS=/ s|=.*|="'"\$(/etc/kubernetes/get_require_kubeconfig.sh) ${KUBELET_ARGS}"'"|
' /etc/kubernetes/kubelet
fi
