#!/bin/sh

. /etc/sysconfig/heat-params

echo "configuring kubernetes (minion)"

CERT_DIR=/srv/kubernetes
PROTOCOL=https
FLANNEL_OPTIONS="-etcd-cafile $CERT_DIR/ca.crt \
-etcd-certfile $CERT_DIR/client.crt \
-etcd-keyfile $CERT_DIR/client.key"
ETCD_CURL_OPTIONS="--cacert $CERT_DIR/ca.crt \
--cert $CERT_DIR/client.crt --key $CERT_DIR/client.key"
ETCD_SERVER_IP=${ETCD_SERVER_IP:-$KUBE_MASTER_IP}
KUBE_PROTOCOL="https"
KUBE_CONFIG=""
FLANNELD_CONFIG=/etc/sysconfig/flanneld

if [ "$TLS_DISABLED" = "True" ]; then
    PROTOCOL=http
    FLANNEL_OPTIONS=""
    ETCD_CURL_OPTIONS=""
fi

sed -i '/FLANNEL_OPTIONS/'d $FLANNELD_CONFIG

cat >> $FLANNELD_CONFIG <<EOF
FLANNEL_OPTIONS="$FLANNEL_OPTIONS"
EOF

if [ "$TLS_DISABLED" = "True" ]; then
    KUBE_PROTOCOL="http"
else
    KUBE_CONFIG="--kubeconfig=/srv/kubernetes/kubeconfig.yaml"
fi
KUBE_MASTER_URI="$KUBE_PROTOCOL://$KUBE_MASTER_IP:$KUBE_API_PORT"

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
KUBELET_ARGS="--config=/etc/kubernetes/manifests --cadvisor-port=4194 ${KUBE_CONFIG} --hostname-override=${HOSTNAME_OVERRIDE}"
KUBELET_ARGS="${KUBELET_ARGS} --cluster_dns=${DNS_SERVICE_IP} --cluster_domain=${DNS_CLUSTER_DOMAIN}"

if [ -n "$TRUST_ID" ]; then
    KUBELET_ARGS="$KUBELET_ARGS --cloud-provider=openstack --cloud-config=/etc/sysconfig/kube_openstack_config"
fi

# Workaround for Cinder support (fixed in k8s >= 1.6)
if [ ! -f /usr/bin/udevadm ]; then
    ln -s /sbin/udevadm /usr/bin/udevadm
fi

# For using default log-driver, other options should be ignored
sed -i 's/\-\-log\-driver\=journald//g' /etc/sysconfig/docker

if [ -n "${INSECURE_REGISTRY_URL}" ]; then
    KUBELET_ARGS="${KUBELET_ARGS} --pod-infra-container-image=${INSECURE_REGISTRY_URL}/google_containers/pause\:0.8.0"
    echo "INSECURE_REGISTRY='--insecure-registry ${INSECURE_REGISTRY_URL}'" >> /etc/sysconfig/docker
fi

sed -i '
    /^KUBELET_ADDRESS=/ s/=.*/="--address=0.0.0.0"/
    /^KUBELET_HOSTNAME=/ s/=.*/=""/
    /^KUBELET_API_SERVER=/ s|=.*|="--api-servers='"$KUBE_MASTER_URI"'"|
    /^KUBELET_ARGS=/ s|=.*|="'"${KUBELET_ARGS}"'"|
' /etc/kubernetes/kubelet

sed -i '
    /^KUBE_PROXY_ARGS=/ s|=.*|='"$KUBE_CONFIG"'|
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
