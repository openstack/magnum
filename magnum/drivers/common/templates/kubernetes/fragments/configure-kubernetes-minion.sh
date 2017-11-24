#!/bin/sh

. /etc/sysconfig/heat-params

echo "configuring kubernetes (minion)"

_prefix=${CONTAINER_INFRA_PREFIX:-docker.io/openstackmagnum/}
atomic install --storage ostree --system --system-package=no --name=kubelet ${_prefix}kubernetes-kubelet:${KUBE_TAG}
atomic install --storage ostree --system --system-package=no --name=kube-proxy ${_prefix}kubernetes-proxy:${KUBE_TAG}

CERT_DIR=/etc/kubernetes/certs
PROTOCOL=https
FLANNEL_OPTIONS="-etcd-cafile $CERT_DIR/ca.crt \
-etcd-certfile $CERT_DIR/client.crt \
-etcd-keyfile $CERT_DIR/client.key"
ETCD_CURL_OPTIONS="--cacert $CERT_DIR/ca.crt \
--cert $CERT_DIR/client.crt --key $CERT_DIR/client.key"
ETCD_SERVER_IP=${ETCD_SERVER_IP:-$KUBE_MASTER_IP}
KUBE_PROTOCOL="https"
KUBECONFIG=/etc/kubernetes/kubeconfig.yaml
FLANNELD_CONFIG=/etc/sysconfig/flanneld

if [ "$TLS_DISABLED" = "True" ]; then
    PROTOCOL=http
    FLANNEL_OPTIONS=""
    ETCD_CURL_OPTIONS=""
    KUBE_PROTOCOL="http"
fi

sed -i '/FLANNEL_OPTIONS/'d $FLANNELD_CONFIG

cat >> $FLANNELD_CONFIG <<EOF
FLANNEL_OPTIONS="$FLANNEL_OPTIONS"
EOF

KUBE_MASTER_URI="$KUBE_PROTOCOL://$KUBE_MASTER_IP:$KUBE_API_PORT"

cat << EOF >> ${KUBECONFIG}
apiVersion: v1
kind: Config
users:
- name: kubeclient
  user:
    client-certificate: ${CERT_DIR}/client.crt
    client-key: ${CERT_DIR}/client.key
clusters:
- name: kubernetes
  cluster:
    server: ${KUBE_MASTER_URI}
    certificate-authority: ${CERT_DIR}/ca.crt
contexts:
- context:
    cluster: kubernetes
    user: kubeclient
  name: service-account-context
current-context: service-account-context
EOF

if [ "$TLS_DISABLED" = "True" ]; then
    sed -i 's/^.*user:$//' ${KUBECONFIG}
    sed -i 's/^.*client-certificate.*$//' ${KUBECONFIG}
    sed -i 's/^.*client-key.*$//' ${KUBECONFIG}
    sed -i 's/^.*certificate-authority.*$//' ${KUBECONFIG}
fi

chmod 0644 ${KUBECONFIG}

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
HOSTNAME_OVERRIDE=$(hostname --short | sed 's/\.novalocal//')
KUBELET_ARGS="--pod-manifest-path=/etc/kubernetes/manifests --cadvisor-port=4194 --kubeconfig ${KUBECONFIG} --hostname-override=${HOSTNAME_OVERRIDE}"
KUBELET_ARGS="${KUBELET_ARGS} --cluster_dns=${DNS_SERVICE_IP} --cluster_domain=${DNS_CLUSTER_DOMAIN}"

if [ -n "$TRUST_ID" ]; then
    KUBELET_ARGS="$KUBELET_ARGS --cloud-provider=openstack --cloud-config=/etc/kubernetes/kube_openstack_config"
fi

# Workaround for Cinder support (fixed in k8s >= 1.6)
if [ ! -f /usr/bin/udevadm ]; then
    ln -s /sbin/udevadm /usr/bin/udevadm
fi

# For using default log-driver, other options should be ignored
sed -i 's/\-\-log\-driver\=journald//g' /etc/sysconfig/docker

KUBELET_ARGS="${KUBELET_ARGS} --pod-infra-container-image=${CONTAINER_INFRA_PREFIX:-gcr.io/google_containers/}pause:3.0"
if [ -n "${INSECURE_REGISTRY_URL}" ]; then
    echo "INSECURE_REGISTRY='--insecure-registry ${INSECURE_REGISTRY_URL}'" >> /etc/sysconfig/docker
fi

# specified cgroup driver
KUBELET_ARGS="${KUBELET_ARGS} --cgroup-driver=systemd"

sed -i '
    /^KUBELET_ADDRESS=/ s/=.*/="--address=0.0.0.0"/
    /^KUBELET_HOSTNAME=/ s/=.*/=""/
    s/^KUBELET_API_SERVER=.*$//
    /^KUBELET_ARGS=/ s|=.*|="'"${KUBELET_ARGS}"'"|
' /etc/kubernetes/kubelet

sed -i '
    /^KUBE_PROXY_ARGS=/ s|=.*|=--kubeconfig='"$KUBECONFIG"'|
' /etc/kubernetes/proxy

if [ "$NETWORK_DRIVER" = "flannel" ]; then
    sed -i '
        /^FLANNEL_ETCD_ENDPOINTS=/ s|=.*|="'"$PROTOCOL"'://'"$ETCD_SERVER_IP"':2379"|
    ' $FLANNELD_CONFIG

    # Make sure etcd has a flannel configuration
    . $FLANNELD_CONFIG
    until curl -sf $ETCD_CURL_OPTIONS \
        "$FLANNEL_ETCD_ENDPOINTS/v2/keys${FLANNEL_ETCD_PREFIX}/config?quorum=false&recursive=false&sorted=false"
    do
        echo "Waiting for flannel configuration in etcd..."
        sleep 5
    done
fi

cat >> /etc/environment <<EOF
KUBERNETES_MASTER=$KUBE_MASTER_URI
EOF

hostname `hostname | sed 's/.novalocal//'`
