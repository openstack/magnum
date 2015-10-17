#!/bin/sh

. /etc/sysconfig/heat-params

echo "configuring kubernetes (master)"
sed -i '
  /^ETCD_LISTEN_CLIENT_URLS=/ s/=.*/="http:\/\/0.0.0.0:2379"/
' /etc/etcd/etcd.conf

sed -i '
  /^KUBE_ALLOW_PRIV=/ s/=.*/="--allow_privileged='"$KUBE_ALLOW_PRIV"'"/
' /etc/kubernetes/config

KUBE_API_ARGS="--runtime_config=api/all=true"
if [ "$TLS_DISABLED" == "True" ]; then
    KUBE_API_ADDRESS="--insecure-bind-address=0.0.0.0 --insecure-port=$KUBE_API_PORT"
else
    KUBE_API_ADDRESS="--bind_address=0.0.0.0 --secure-port=$KUBE_API_PORT"
    # insecure port is used internaly
    KUBE_API_ADDRESS="$KUBE_API_ADDRESS --insecure-port=8080"
    KUBE_API_ARGS="$KUBE_API_ARGS --tls_cert_file=/srv/kubernetes/server.crt"
    KUBE_API_ARGS="$KUBE_API_ARGS --tls_private_key_file=/srv/kubernetes/server.key"
    KUBE_API_ARGS="$KUBE_API_ARGS --client_ca_file=/srv/kubernetes/ca.crt"
fi

sed -i '
  /^KUBE_API_ADDRESS=/ s/=.*/='"${KUBE_API_ADDRESS}"'/
  /^KUBE_SERVICE_ADDRESSES=/ s|=.*|="--service-cluster-ip-range='"$PORTAL_NETWORK_CIDR"'"|
  /^KUBE_API_ARGS=/ s/KUBE_API_ARGS.//
  /^KUBE_ETCD_SERVERS=/ s/=.*/="--etcd_servers=http:\/\/127.0.0.1:2379"/
  /^KUBE_ADMISSION_CONTROL=/ s/=.*/=""/
' /etc/kubernetes/apiserver
cat << _EOC_ >> /etc/kubernetes/apiserver
#Uncomment the following line to disable Load Balancer feature
KUBE_API_ARGS="$KUBE_API_ARGS"
#Uncomment the following line to enable Load Balancer feature
#KUBE_API_ARGS="$KUBE_API_ARGS --cloud_config=/etc/sysconfig/kube_openstack_config --cloud_provider=openstack"
_EOC_

sed -i '
  /^KUBELET_ADDRESSES=/ s/=.*/="--machines='""'"/
  /^KUBE_CONTROLLER_MANAGER_ARGS=/ s/KUBE_CONTROLLER_MANAGER_ARGS.*/#Uncomment the following line to enable Kubernetes Load Balancer feature \n#KUBE_CONTROLLER_MANAGER_ARGS="--cloud_config=\/etc\/sysconfig\/kube_openstack_config --cloud_provider=openstack"/
' /etc/kubernetes/controller-manager
