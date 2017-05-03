#!/bin/sh

. /etc/sysconfig/heat-params

echo "configuring kubernetes (minion)"

ETCD_SERVER_IP=${ETCD_SERVER_IP:-$KUBE_MASTER_IP}
KUBE_PROTOCOL="https"
KUBE_CONFIG=""
if [ "$TLS_DISABLED" = "True" ]; then
    KUBE_PROTOCOL="http"
else
    KUBE_CONFIG="--kubeconfig=/srv/kubernetes/kubeconfig.yaml"
fi
KUBE_MASTER_URI="$KUBE_PROTOCOL://$KUBE_MASTER_IP:$KUBE_API_PORT"

sed -i '
  /^KUBE_ALLOW_PRIV=/ s/=.*/="--allow_privileged='"$KUBE_ALLOW_PRIV"'"/
  /^KUBE_ETCD_SERVERS=/ s|=.*|="--etcd_servers=http://'"$ETCD_SERVER_IP"':2379"|
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

if [ -n "${INSECURE_REGISTRY_URL}" ]; then
    KUBELET_ARGS="${KUBELET_ARGS} --pod-infra-container-image=${INSECURE_REGISTRY_URL}/google_containers/pause\:0.8.0"
    echo "INSECURE_REGISTRY='--insecure-registry ${INSECURE_REGISTRY_URL}'" >> /etc/sysconfig/docker
fi

sed -i '
  /^KUBELET_ADDRESS=/ s/=.*/="--address=0.0.0.0"/
  /^KUBELET_HOSTNAME=/ s/=.*/=""/
  /^KUBELET_API_SERVER=/ s|=.*|="--api_servers='"$KUBE_MASTER_URI"'"|
  /^KUBELET_ARGS=/ s|=.*|="'"${KUBELET_ARGS}"'"|
' /etc/kubernetes/kubelet

sed -i '
  /^KUBE_PROXY_ARGS=/ s|=.*|='"$KUBE_CONFIG"'|
' /etc/kubernetes/proxy

if [ "$NETWORK_DRIVER" = "flannel" ]; then
    sed -i '
        /^FLANNEL_ETCD_ENDPOINTS=/ s|=.*|="http://'"$ETCD_SERVER_IP"':2379"|
    ' /etc/sysconfig/flanneld

    # Make sure etcd has a flannel configuration
    . /etc/sysconfig/flanneld
    until curl -sf "$FLANNEL_ETCD_ENDPOINTS/v2/keys${FLANNEL_ETCD_PREFIX}/config?quorum=false&recursive=false&sorted=false"
    do
        echo "Waiting for flannel configuration in etcd..."
        sleep 5
    done
fi

cat >> /etc/environment <<EOF
KUBERNETES_MASTER=$KUBE_MASTER_URI
EOF

hostname `hostname | sed 's/.novalocal//'`
