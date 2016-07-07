#!/bin/sh

. /etc/sysconfig/heat-params

KUBE_OS_CLOUD_CONFIG=/etc/sysconfig/kube_openstack_config

# kubernetes backend only support keystone v2 at this point
AUTH_URL=$(echo "$AUTH_URL" | tr -s "v3" "v2")

# Generate a the configuration for Kubernetes services
# to talk to OpenStack Neutron
cat > $KUBE_OS_CLOUD_CONFIG <<EOF
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
