#!/bin/sh

. /etc/sysconfig/heat-params

echo "configuring kubernetes (master)"

# Generate ServiceAccount key if needed
SERVICE_ACCOUNT_KEY="/var/lib/kubernetes/serviceaccount.key"
if [[ ! -f "${SERVICE_ACCOUNT_KEY}" ]]; then
    mkdir -p "$(dirname ${SERVICE_ACCOUNT_KEY})"
    openssl genrsa -out "${SERVICE_ACCOUNT_KEY}" 2048 2>/dev/null
fi

# Setting correct permissions for Kubernetes files
chown -R kube:kube /var/lib/kubernetes

KUBE_API_ARGS="--service-account-key-file=$SERVICE_ACCOUNT_KEY --runtime_config=api/all=true"

if [ "$TLS_DISABLED" == "True" ]; then
    sed -i '
        /^# KUBE_API_PORT=/ s|.*|KUBE_API_PORT="--port=8080 --insecure-port='"$KUBE_API_PORT"'"|
    ' /etc/kubernetes/apiserver
else
    # insecure port is used internaly
    sed -i '
        /^# KUBE_API_PORT=/ s|.*|KUBE_API_PORT="--port=8080 --insecure-port=8080 --secure-port='"$KUBE_API_PORT"'"|
    ' /etc/kubernetes/apiserver
    KUBE_API_ARGS="$KUBE_API_ARGS --tls_cert_file=/etc/kubernetes/ssl/server.crt"
    KUBE_API_ARGS="$KUBE_API_ARGS --tls_private_key_file=/etc/kubernetes/ssl/server.key"
    KUBE_API_ARGS="$KUBE_API_ARGS --client_ca_file=/etc/kubernetes/ssl/ca.crt"
fi

sed -i '
    /^KUBE_ALLOW_PRIV=/ s|=.*|="--allow-privileged='"$KUBE_ALLOW_PRIV"'"|
' /etc/kubernetes/config

sed -i '
    /^KUBE_API_ADDRESS=/ s|=.*|="--advertise-address='"$KUBE_NODE_IP"' --insecure-bind-address=0.0.0.0 --bind_address=0.0.0.0"|
    /^KUBE_SERVICE_ADDRESSES=/ s|=.*|="--service-cluster-ip-range='"$PORTAL_NETWORK_CIDR"'"|
    /^KUBE_API_ARGS=/ s|=.*|="--service-account-key-file='"$SERVICE_ACCOUNT_KEY"' --runtime-config=api\/all=true"|
    /^KUBE_ETCD_SERVERS=/ s/=.*/="--etcd-servers=http:\/\/127.0.0.1:2379"/
    /^KUBE_ADMISSION_CONTROL=/ s/=.*/="--admission-control=NamespaceLifecycle,LimitRanger,ServiceAccount,ResourceQuota"/
' /etc/kubernetes/apiserver

cat >> /etc/kubernetes/apiserver <<EOF
#Uncomment the following line to enable Load Balancer feature
#KUBE_API_ARGS="--service-account-key-file='"$SERVICE_ACCOUNT_KEY"' --runtime-config=api\/all=true" --runtime-config=api\/all=true --cloud-config=/etc/sysconfig/kubernetes_openstack_config --cloud-provider=openstack"
EOF

sed -i '
    /^KUBE_CONTROLLER_MANAGER_ARGS=/ s|=.*|="--service_account_private_key_file='"$SERVICE_ACCOUNT_KEY"' --leader-elect=true --cluster-name=kubernetes --cluster-cidr='"$FLANNEL_NETWORK_CIDR"'"|
' /etc/kubernetes/controller-manager

cat >> /etc/kubernetes/controller-manager <<EOF
#Uncomment the following line to enable Load Balancer feature
#KUBE_CONTROLLER_MANAGER_ARGS="--service_account_private_key_file='"$SERVICE_ACCOUNT_KEY"' --leader-elect=true --cluster-name=kubernetes --cluster-cidr='"$FLANNEL_NETWORK_CIDR"' --cloud-config=/etc/sysconfig/kubernetes_openstack_config --cloud-provider=openstack"
EOF

# Generate a the configuration for Kubernetes services to talk to OpenStack Neutron
cat > /etc/sysconfig/kubernetes_openstack_config <<EOF
[Global]
auth-url=$AUTH_URL
username=$USERNAME
password=$PASSWORD
tenant-name=$TENANT_NAME
domain-name=$DOMAIN_NAME
[LoadBalancer]
lb-version=v2
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
