#!/bin/sh

set +x
. /etc/sysconfig/heat-params
set -x

$ssh_cmd mkdir -p /etc/kubernetes/

if [ -z "${TRUST_ID}" ]; then
    exit 0
fi

KUBE_OS_CLOUD_CONFIG=/etc/kubernetes/cloud-config
$ssh_cmd cp /etc/pki/tls/certs/ca-bundle.crt /etc/kubernetes/ca-bundle.crt

# Generate a the configuration for Kubernetes services
# to talk to OpenStack Neutron and Cinder
CLOUD_CONFIG=$(cat <<EOF
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
)

cat > ${KUBE_OS_CLOUD_CONFIG} <<EOF
$CLOUD_CONFIG
EOF

# Provide optional region parameter if it's set.
if [ -n "${REGION_NAME}" ]; then
    sed -i '/ca-file/a region='${REGION_NAME}'' $KUBE_OS_CLOUD_CONFIG
fi

# backwards compatibility, some apps may expect this file from previous magnum versions.
$ssh_cmd cp ${KUBE_OS_CLOUD_CONFIG} /etc/kubernetes/kube_openstack_config

# Append additional networking config to config file provided to openstack
# cloud controller manager (not supported by in-tree Cinder).
cat > ${KUBE_OS_CLOUD_CONFIG}-occm <<EOF
$CLOUD_CONFIG
[Networking]
internal-network-name=$CLUSTER_NETWORK
EOF
