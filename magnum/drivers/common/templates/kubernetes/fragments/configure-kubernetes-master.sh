#!/bin/sh

. /etc/sysconfig/heat-params

echo "configuring kubernetes (master)"

if [ -z "$KUBE_NODE_IP" ]; then
    # FIXME(yuanying): Set KUBE_NODE_IP correctly
    KUBE_NODE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
fi

sed -i '
    /^KUBE_ALLOW_PRIV=/ s/=.*/="--allow-privileged='"$KUBE_ALLOW_PRIV"'"/
' /etc/kubernetes/config

KUBE_API_ARGS="--runtime-config=api/all=true"
if [ "$TLS_DISABLED" == "True" ]; then
    KUBE_API_ADDRESS="--insecure-bind-address=0.0.0.0 --insecure-port=$KUBE_API_PORT"
else
    KUBE_API_ADDRESS="--bind-address=0.0.0.0 --secure-port=$KUBE_API_PORT"
    # insecure port is used internaly
    KUBE_API_ADDRESS="$KUBE_API_ADDRESS --insecure-port=8080"
    KUBE_API_ARGS="$KUBE_API_ARGS --tls-cert-file=/srv/kubernetes/server.crt"
    KUBE_API_ARGS="$KUBE_API_ARGS --tls-private-key-file=/srv/kubernetes/server.key"
    KUBE_API_ARGS="$KUBE_API_ARGS --client-ca-file=/srv/kubernetes/ca.crt"
fi

sed -i '
    /^KUBE_API_ADDRESS=/ s/=.*/="'"${KUBE_API_ADDRESS}"'"/
    /^KUBE_SERVICE_ADDRESSES=/ s|=.*|="--service-cluster-ip-range='"$PORTAL_NETWORK_CIDR"'"|
    /^KUBE_API_ARGS=/ s/KUBE_API_ARGS.//
    /^KUBE_ETCD_SERVERS=/ s/=.*/="--etcd-servers=http:\/\/127.0.0.1:2379"/
    /^KUBE_ADMISSION_CONTROL=/ s/=.*/=""/
' /etc/kubernetes/apiserver
cat << _EOC_ >> /etc/kubernetes/apiserver
#Uncomment the following line to disable Load Balancer feature
KUBE_API_ARGS="$KUBE_API_ARGS"
#Uncomment the following line to enable Load Balancer feature
#KUBE_API_ARGS="$KUBE_API_ARGS --cloud-config=/etc/sysconfig/kube_openstack_config --cloud-provider=openstack"
_EOC_

sed -i '
    /^KUBELET_ADDRESSES=/ s/=.*/="--machines='""'"/
    /^KUBE_CONTROLLER_MANAGER_ARGS=/ s/KUBE_CONTROLLER_MANAGER_ARGS.*/#Uncomment the following line to enable Kubernetes Load Balancer feature \n#KUBE_CONTROLLER_MANAGER_ARGS="--cloud-config=\/etc\/sysconfig\/kube_openstack_config --cloud-provider=openstack"/
' /etc/kubernetes/controller-manager

KUBELET_ARGS="--register-node=true --register-schedulable=false --config=/etc/kubernetes/manifests --hostname-override=$KUBE_NODE_IP"

if [ -n "${INSECURE_REGISTRY_URL}" ]; then
    KUBELET_ARGS="${KUBELET_ARGS} --pod-infra-container-image=${INSECURE_REGISTRY_URL}/google_containers/pause\:0.8.0"
    echo "INSECURE_REGISTRY='--insecure-registry ${INSECURE_REGISTRY_URL}'" >> /etc/sysconfig/docker
fi

sed -i '
    /^KUBELET_ADDRESS=/ s/=.*/="--address=0.0.0.0"/
    /^KUBELET_HOSTNAME=/ s/=.*/=""/
    /^KUBELET_ARGS=/ s|=.*|='"$KUBELET_ARGS"'|
' /etc/kubernetes/kubelet
