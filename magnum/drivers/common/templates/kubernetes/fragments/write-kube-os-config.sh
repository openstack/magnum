#!/bin/sh

set +x
. /etc/sysconfig/heat-params
set -x
ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"
$ssh_cmd mkdir -p /etc/kubernetes/

# Copy ca-bundle only if it doesn't exist or has changed
if [ ! -f /etc/kubernetes/ca-bundle.crt ] || ! $ssh_cmd cmp -s /etc/pki/tls/certs/ca-bundle.crt /etc/kubernetes/ca-bundle.crt; then
    $ssh_cmd cp /etc/pki/tls/certs/ca-bundle.crt /etc/kubernetes/ca-bundle.crt
fi

if [ -n "${TRUST_ID}" ]; then
    KUBE_OS_CLOUD_CONFIG=/etc/kubernetes/cloud-config

    # Generate the configuration for Kubernetes services
    # to talk to OpenStack Neutron and Cinder
    config_content=$(cat << EOF
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

    # Add region if specified
    if [ -n "${REGION_NAME}" ]; then
        config_content=$(echo "$config_content" | sed '/ca-file/a region='${REGION_NAME}'')
    fi

    # Write to temporary file first
    echo "$config_content" > ${KUBE_OS_CLOUD_CONFIG}.tmp

    # Move to final location if different or doesn't exist
    if [ ! -f ${KUBE_OS_CLOUD_CONFIG} ] || ! $ssh_cmd cmp -s ${KUBE_OS_CLOUD_CONFIG}.tmp ${KUBE_OS_CLOUD_CONFIG}; then
        mv ${KUBE_OS_CLOUD_CONFIG}.tmp ${KUBE_OS_CLOUD_CONFIG}

        # backwards compatibility, some apps may expect this file from previous magnum versions
        $ssh_cmd cp ${KUBE_OS_CLOUD_CONFIG} /etc/kubernetes/kube_openstack_config
    else
        rm ${KUBE_OS_CLOUD_CONFIG}.tmp
    fi

    # Create OCCM config with additional networking config
    occm_config="${config_content}
[Networking]
internal-network-name=$CLUSTER_NETWORK_NAME"

    # Write OCCM config to temporary file
    echo "$occm_config" > ${KUBE_OS_CLOUD_CONFIG}-occm.tmp

    # Move to final location if different or doesn't exist
    if [ ! -f ${KUBE_OS_CLOUD_CONFIG}-occm ] || ! $ssh_cmd cmp -s ${KUBE_OS_CLOUD_CONFIG}-occm.tmp ${KUBE_OS_CLOUD_CONFIG}-occm; then
        mv ${KUBE_OS_CLOUD_CONFIG}-occm.tmp ${KUBE_OS_CLOUD_CONFIG}-occm
    else
        rm ${KUBE_OS_CLOUD_CONFIG}-occm.tmp
    fi
fi
