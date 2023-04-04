set +x
. /etc/sysconfig/heat-params
set -x

$ssh_cmd mkdir -p /etc/kubernetes/

if [ -n "${TRUST_ID}" ]; then
    KUBE_OS_CLOUD_CONFIG=/etc/kubernetes/cloud-config

    # Generate a the configuration for Kubernetes services
    # to talk to OpenStack Neutron and Cinder
    cat > ${KUBE_OS_CLOUD_CONFIG} <<EOF
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
lb-provider=$OCTAVIA_PROVIDER
lb-method=$OCTAVIA_LB_ALGORITHM
create-monitor=$OCTAVIA_LB_HEALTHCHECK
monitor-delay=1m
monitor-timeout=30s
monitor-max-retries=3
[BlockStorage]
bs-version=v2
EOF

    # Provide optional region parameter if it's set.
    if [ -n "${REGION_NAME}" ]; then
        sed -i '/ca-file/a region='${REGION_NAME}'' $KUBE_OS_CLOUD_CONFIG
    fi

    # backwards compatibility, some apps may expect this file from previous magnum versions.
    $ssh_cmd cp ${KUBE_OS_CLOUD_CONFIG} /etc/kubernetes/kube_openstack_config

    # Append additional networking config to config file provided to openstack
    # cloud controller manager (not supported by in-tree Cinder).
    $ssh_cmd cp ${KUBE_OS_CLOUD_CONFIG} ${KUBE_OS_CLOUD_CONFIG}-occm
    cat >> ${KUBE_OS_CLOUD_CONFIG}-occm <<EOF
[Networking]
internal-network-name=$CLUSTER_NETWORK_NAME
EOF
fi
