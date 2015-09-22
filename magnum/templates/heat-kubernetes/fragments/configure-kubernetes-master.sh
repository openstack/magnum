#!/bin/sh

. /etc/sysconfig/heat-params

echo "configuring kubernetes (master)"
sed -i '
  /^ETCD_LISTEN_CLIENT_URLS=/ s/=.*/="http:\/\/0.0.0.0:2379"/
' /etc/etcd/etcd.conf

sed -i '
  /^KUBE_ALLOW_PRIV=/ s/=.*/="--allow_privileged='"$KUBE_ALLOW_PRIV"'"/
' /etc/kubernetes/config

sed -i '
  /^KUBE_API_ADDRESS=/ s/=.*/="--address=0.0.0.0"/
  /^KUBE_SERVICE_ADDRESSES=/ s|=.*|="--service-cluster-ip-range='"$PORTAL_NETWORK_CIDR"'"|
  /^KUBE_API_ARGS=/ s/=.*/="--runtime_config=api\/all=true"/
  /^KUBE_ETCD_SERVERS=/ s/=.*/="--etcd_servers=http:\/\/127.0.0.1:2379"/
  /^KUBE_ADMISSION_CONTROL=/ s/=.*/=""/
' /etc/kubernetes/apiserver

sed -i '
  /^KUBELET_ADDRESSES=/ s/=.*/="--machines='""'"/
' /etc/kubernetes/controller-manager
