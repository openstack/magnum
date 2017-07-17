#!/bin/sh

. /etc/sysconfig/heat-params

KUBE_OS_CLOUD_CONFIG=/etc/kubernetes/kube_openstack_config

# Generate a the configuration for Kubernetes services
# to talk to OpenStack Neutron
cat > $KUBE_OS_CLOUD_CONFIG <<EOF
[Global]
auth-url=$AUTH_URL
user-id=$TRUSTEE_USER_ID
password=$TRUSTEE_PASSWORD
trust-id=$TRUST_ID
[LoadBalancer]
subnet-id=$CLUSTER_SUBNET
create-monitor=yes
monitor-delay=1m
monitor-timeout=30s
monitor-max-retries=3
EOF
