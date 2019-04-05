#!/bin/sh

. /etc/sysconfig/heat-params

mkdir -p /etc/kubernetes/

if [ -z "${TRUST_ID}" ]; then
    exit 0
fi

KUBE_OS_CLOUD_CONFIG=/etc/kubernetes/cloud-config
cp /etc/pki/tls/certs/ca-bundle.crt /etc/kubernetes/ca-bundle.crt

# Generate a the configuration for Kubernetes services
# to talk to OpenStack Neutron and Cinder
cat > $KUBE_OS_CLOUD_CONFIG <<EOF
[Global]
auth-url=$AUTH_URL
user-id=$TRUSTEE_USER_ID
password=$TRUSTEE_PASSWORD
trust-id=$TRUST_ID
ca-file=/etc/kubernetes/ca-bundle.crt
[LoadBalancer]
use-octavia=$OCTAVIA_ENABLED
subnet-id=$CLUSTER_SUBNET
floating-network-id=$EXTERNAL_NETWORK_ID
create-monitor=yes
monitor-delay=1m
monitor-timeout=30s
monitor-max-retries=3
[BlockStorage]
bs-version=v2
EOF

# Provide optional region parameter if it's set.
if [ -n ${REGION_NAME} ]; then
    sed -i '/ca-file/a region='${REGION_NAME}'' $KUBE_OS_CLOUD_CONFIG
fi

# backwards compatibility, some apps may expect this file from previous magnum versions.
cp ${KUBE_OS_CLOUD_CONFIG} /etc/kubernetes/kube_openstack_config
