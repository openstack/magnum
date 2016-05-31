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

KUBELET_ARGS="--config=/etc/kubernetes/manifests --cadvisor-port=4194 --hostname-override=$KUBE_NODE_IP ${KUBE_CONFIG}"

if [ -n "${INSECURE_REGISTRY_URL}" ]; then
    KUBELET_ARGS="${KUBELET_ARGS} --pod-infra-container-image=${INSECURE_REGISTRY_URL}/google_containers/pause\:0.8.0"
    echo "INSECURE_REGISTRY='--insecure-registry ${INSECURE_REGISTRY_URL}'" >> /etc/sysconfig/docker
fi

sed -i '
  /^KUBELET_ADDRESS=/ s/=.*/="--address=0.0.0.0"/
  /^KUBELET_HOSTNAME=/ s/=.*/=""/
  /^KUBELET_API_SERVER=/ s|=.*|="--api_servers='"$KUBE_MASTER_URI"'"|
  /^KUBELET_ARGS=/ s|=.*|='"${KUBELET_ARGS}"'|
' /etc/kubernetes/kubelet

sed -i '
  /^KUBE_PROXY_ARGS=/ s|=.*|='"$KUBE_CONFIG"'|
' /etc/kubernetes/proxy

if [ "$NETWORK_DRIVER" = "flannel" ]; then
    sed -i '
      /^FLANNEL_ETCD=/ s|=.*|="http://'"$ETCD_SERVER_IP"':2379"|
    ' /etc/sysconfig/flanneld

    # Make sure etcd has a flannel configuration
    . /etc/sysconfig/flanneld
    until curl -sf "$FLANNEL_ETCD/v2/keys${FLANNEL_ETCD_KEY}/config?quorum=false&recursive=false&sorted=false"
    do
        echo "Waiting for flannel configuration in etcd..."
        sleep 5
    done
fi

if [ "$VOLUME_DRIVER" = "cinder" ]; then
    CLOUD_CONFIG=/etc/kubernetes/kube_openstack_config
    KUBERNETES=/etc/kubernetes
    if [ ! -d ${KUBERNETES} -o ! -f ${CLOUD_CONFIG} ]; then
        sudo mkdir -p $KUBERNETES
    fi
    AUTH_URL=$(echo "$AUTH_URL" | tr -s "v3" "v2")
cat > $CLOUD_CONFIG <<EOF
[Global]
auth-url=$AUTH_URL
username=$USERNAME
password=$PASSWORD
region=$REGION_NAME
tenant-name=$TENANT_NAME
EOF

cat << _EOC_ >> /etc/kubernetes/kubelet
#KUBELET_ARGS="$KUBELET_ARGS --cloud-provider=openstack --cloud-config=/etc/kubernetes/kube_openstack_config"
_EOC_

    if [ ! -f /usr/bin/udevadm ]; then
        sudo ln -s /sbin/udevadm /usr/bin/udevadm
    fi

fi

cat >> /etc/environment <<EOF
KUBERNETES_MASTER=$KUBE_MASTER_URI
EOF

hostname `hostname | sed 's/.novalocal//'`
