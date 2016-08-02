#!/bin/sh

. /etc/sysconfig/heat-params

echo "configuring kubernetes (master)"

KUBE_API_ARGS="--runtime_config=api/all=true"
KUBE_API_ADDRESS="--insecure-bind-address=0.0.0.0 --insecure-port=$KUBE_API_PORT"

sed -i '
  /^KUBE_ALLOW_PRIV=/ s/=.*/="--allow_privileged='"$KUBE_ALLOW_PRIV"'"/
' /etc/kubernetes/config

sed -i '
  /^KUBE_API_ADDRESS=/ s/=.*/='"${KUBE_API_ADDRESS}"'/
  /^KUBE_SERVICE_ADDRESSES=/ s|=.*|="--service-cluster-ip-range='"$PORTAL_NETWORK_CIDR"'"|
  /^KUBE_API_ARGS=/ s/KUBE_API_ARGS.//
  /^KUBE_ETCD_SERVERS=/ s/=.*/="--etcd_servers=http:\/\/127.0.0.1:2379"/
  /^KUBE_ADMISSION_CONTROL=/ s/=.*/=""/
' /etc/kubernetes/apiserver

cat >> /etc/kubernetes/apiserver <<EOF
#Uncomment the following line to disable Load Balancer feature
KUBE_API_ARGS="$KUBE_API_ARGS"
#Uncomment the following line to enable Load Balancer feature
#KUBE_API_ARGS="$KUBE_API_ARGS --cloud_config=/etc/sysconfig/kubernetes_openstack_config --cloud_provider=openstack"
EOF

sed -i '
  /^KUBELET_ADDRESSES=/ s/=.*/="--machines='""'"/
  /^KUBE_CONTROLLER_MANAGER_ARGS=/ s/KUBE_CONTROLLER_MANAGER_ARGS.*/#Uncomment the following line to enable Kubernetes Load Balancer feature \n#KUBE_CONTROLLER_MANAGER_ARGS="--cloud_config=\/etc\/sysconfig\/kubernetes_openstack_config --cloud_provider=openstack"/
' /etc/kubernetes/controller-manager

# Generate a the configuration for Kubernetes services to talk to OpenStack Neutron
cat > /etc/sysconfig/kubernetes_openstack_config <<EOF
[Global]
auth-url=$AUTH_URL
Username=$USERNAME
Password=$PASSWORD
tenant-name=$TENANT_NAME
[LoadBalancer]
subnet-id=$CLUSTER_SUBNET
create-monitor=yes
monitor-delay=1m
monitor-timeout=30s
monitor-max-retries=3
EOF

for service in kube-apiserver kube-scheduler kube-controller-manager; do
  echo "activating $service service"
  systemctl enable $service

  echo "starting $service services"
  systemctl --no-block start $service
done
