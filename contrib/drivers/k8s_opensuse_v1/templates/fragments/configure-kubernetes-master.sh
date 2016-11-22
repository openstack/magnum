#!/bin/sh

. /etc/sysconfig/heat-params

echo "configuring kubernetes (master)"

KUBE_API_ARGS="--runtime_config=api/all=true"
KUBE_API_ADDRESS="--insecure-bind-address=0.0.0.0 --insecure-port=$KUBE_API_PORT"

# Setting correct permissions for Kubernetes files
chown -R kube:kube /var/lib/kubernetes

sed -i '
    /^KUBE_ALLOW_PRIV=/ s|=.*|="--allow-privileged='"$KUBE_ALLOW_PRIV"'"|
' /etc/kubernetes/config

sed -i '
    /^KUBE_API_ADDRESS=/ s|=.*|="--advertise-address='"$KUBE_NODE_IP"' --insecure-bind-address=0.0.0.0"|
    /^KUBE_API_PORT=/ s|=.*|="--insecure-port='"$KUBE_API_PORT"'"|
    /^KUBE_SERVICE_ADDRESSES=/ s|=.*|="--service-cluster-ip-range='"$PORTAL_NETWORK_CIDR"'"|
    /^KUBE_API_ARGS=/ s/=.*/="--runtime-config=api\/all=true"/
    /^KUBE_ETCD_SERVERS=/ s/=.*/="--etcd-servers=http:\/\/127.0.0.1:2379"/
    /^KUBE_ADMISSION_CONTROL=/ s/=.*/="--admission-control=NamespaceLifecycle,LimitRanger,ServiceAccount,ResourceQuota"/
' /etc/kubernetes/apiserver

cat >> /etc/kubernetes/apiserver <<EOF
#Uncomment the following line to enable Load Balancer feature
#KUBE_API_ARGS="--runtime-config=api/all=true --cloud-config=/etc/sysconfig/kubernetes_openstack_config --cloud-provider=openstack"
EOF

sed -i '
    /^KUBE_CONTROLLER_MANAGER_ARGS=/ s|=.*|="--leader-elect=true --cluster-name=kubernetes --cluster-cidr='"$FLANNEL_NETWORK_CIDR"'"|
' /etc/kubernetes/controller-manager

cat >> /etc/kubernetes/controller-manager <<EOF

#Uncomment the following line to enable Kubernetes Load Balancer feature
#KUBE_CONTROLLER_MANAGER_ARGS="--cloud-config=/etc/sysconfig/kubernetes_openstack_config --cloud-provider=openstack"
EOF

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
