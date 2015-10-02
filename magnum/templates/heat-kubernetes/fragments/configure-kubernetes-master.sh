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
  /^KUBE_API_ARGS=/ s/KUBE_API_ARGS./#Uncomment the following line to disable Load Balancer feature\nKUBE_API_ARGS="--runtime_config=api\/all=true"\n#Uncomment the following line to enable Load Balancer feature\n#KUBE_API_ARGS="--runtime_config=api\/all=true --cloud_config=\/etc\/sysconfig\/kube_openstack_config --cloud_provider=openstack"/
  /^KUBE_ETCD_SERVERS=/ s/=.*/="--etcd_servers=http:\/\/127.0.0.1:2379"/
  /^KUBE_ADMISSION_CONTROL=/ s/=.*/=""/
' /etc/kubernetes/apiserver

sed -i '
  /^KUBELET_ADDRESSES=/ s/=.*/="--machines='""'"/
  /^KUBE_CONTROLLER_MANAGER_ARGS=/ s/KUBE_CONTROLLER_MANAGER_ARGS.*/#Uncomment the following line to enable Kubernetes Load Balancer feature \n#KUBE_CONTROLLER_MANAGER_ARGS="--cloud_config=\/etc\/sysconfig\/kube_openstack_config --cloud_provider=openstack"/
' /etc/kubernetes/controller-manager
