#!/bin/bash

. /etc/sysconfig/heat-params

GENCONF_SCRIPT_DIR=/opt/dcos

sudo mkdir -p $GENCONF_SCRIPT_DIR/genconf
sudo chown -R centos $GENCONF_SCRIPT_DIR/genconf

# Configure ip-detect
cat > $GENCONF_SCRIPT_DIR/genconf/ip-detect <<EOF
#!/usr/bin/env bash
set -o nounset -o errexit
export PATH=/usr/sbin:/usr/bin:\$PATH
echo \$(ip addr show eth0 | grep -Eo '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' | head -1)
EOF

# Configure config.yaml
CONFIG_YAML_FILE=$GENCONF_SCRIPT_DIR/genconf/config.yaml

####################################################
# Cluster Setup

# bootstrap_url is not configurable
echo "bootstrap_url: file://$GENCONF_SCRIPT_DIR/genconf/serve" > $CONFIG_YAML_FILE

# cluster_name
echo "cluster_name: $CLUSTER_NAME" >> $CONFIG_YAML_FILE

# exhibitor_storage_backend
if [ "static" == "$EXHIBITOR_STORAGE_BACKEND" ]; then
    echo "exhibitor_storage_backend: static" >> $CONFIG_YAML_FILE
elif [ "zookeeper" == "$EXHIBITOR_STORAGE_BACKEND" ]; then
    echo "exhibitor_storage_backend: zookeeper" >> $CONFIG_YAML_FILE
    echo "exhibitor_zk_hosts: $EXHIBITOR_ZK_HOSTS" >> $CONFIG_YAML_FILE
    echo "exhibitor_zk_path: $EXHIBITOR_ZK_PATH" >> $CONFIG_YAML_FILE
elif [ "aws_s3" == "$EXHIBITOR_STORAGE_BACKEND" ]; then
    echo "exhibitor_storage_backend: aws_s3" >> $CONFIG_YAML_FILE
    echo "aws_access_key_id: $AWS_ACCESS_KEY_ID" >> $CONFIG_YAML_FILE
    echo "aws_region: $AWS_REGIION" >> $CONFIG_YAML_FILE
    echo "aws_secret_access_key: $AWS_SECRET_ACCESS_KEY" >> $CONFIG_YAML_FILE
    echo "exhibitor_explicit_keys: $EXHIBITOR_EXPLICIT_KEYS" >> $CONFIG_YAML_FILE
    echo "s3_bucket: $S3_BUCKET" >> $CONFIG_YAML_FILE
    echo "s3_prefix: $S3_PREFIX" >> $CONFIG_YAML_FILE
elif [ "azure" == "$EXHIBITOR_STORAGE_BACKEND" ]; then
    echo "exhibitor_storage_backend: azure" >> $CONFIG_YAML_FILE
    echo "exhibitor_azure_account_name: $EXHIBITOR_AZURE_ACCOUNT_NAME" >> $CONFIG_YAML_FILE
    echo "exhibitor_azure_account_key: $EXHIBITOR_AZURE_ACCOUNT_KEY" >> $CONFIG_YAML_FILE
    echo "exhibitor_azure_prefix: $EXHIBITOR_AZURE_PREFIX" >> $CONFIG_YAML_FILE
fi

# master_discovery
if [ "static" == "$MASTER_DISCOVERY" ]; then
    echo "master_discovery: static" >> $CONFIG_YAML_FILE
    echo "master_list:" >> $CONFIG_YAML_FILE
    for ip in $MASTER_LIST; do
        echo "- ${ip}" >> $CONFIG_YAML_FILE
    done
elif [ "master_http_loadbalancer" == "$MASTER_DISCOVERY" ]; then
    echo "master_discovery: master_http_loadbalancer" >> $CONFIG_YAML_FILE
    echo "exhibitor_address: $EXHIBITOR_ADDRESS" >> $CONFIG_YAML_FILE
    echo "num_masters: $NUM_MASTERS" >> $CONFIG_YAML_FILE
    echo "master_list:" >> $CONFIG_YAML_FILE
    for ip in $MASTER_LIST; do
        echo "- ${ip}" >> $CONFIG_YAML_FILE
    done
fi

####################################################
# Networking

# dcos_overlay_enable
if [ "false" == "$DCOS_OVERLAY_ENABLE" ]; then
    echo "dcos_overlay_enable: false" >> $CONFIG_YAML_FILE
elif [ "true" == "$DCOS_OVERLAY_ENABLE" ]; then
    echo "dcos_overlay_enable: true" >> $CONFIG_YAML_FILE
    echo "dcos_overlay_config_attempts: $DCOS_OVERLAY_CONFIG_ATTEMPTS" >> $CONFIG_YAML_FILE
    echo "dcos_overlay_mtu: $DCOS_OVERLAY_MTU" >> $CONFIG_YAML_FILE
    echo "dcos_overlay_network:" >> $CONFIG_YAML_FILE
    echo "$DCOS_OVERLAY_NETWORK" >> $CONFIG_YAML_FILE
fi

# dns_search
if [ -n "$DNS_SEARCH" ]; then
    echo "dns_search: $DNS_SEARCH" >> $CONFIG_YAML_FILE
fi

# resolvers
echo "resolvers:" >> $CONFIG_YAML_FILE
for ip in $RESOLVERS; do
echo "- ${ip}" >> $CONFIG_YAML_FILE
done

# use_proxy
if [ -n "$HTTP_PROXY" ] && [ -n "$HTTPS_PROXY" ]; then
echo "use_proxy: true" >> $CONFIG_YAML_FILE
echo "http_proxy: $HTTP_PROXY" >> $CONFIG_YAML_FILE
echo "https_proxy: $HTTPS_PROXY" >> $CONFIG_YAML_FILE
if [ -n "$NO_PROXY" ]; then
    echo "no_proxy:" >> $CONFIG_YAML_FILE
    for ip in $NO_PROXY; do
        echo "- ${ip}" >> $CONFIG_YAML_FILE
    done
fi
fi

####################################################
# Performance and Tuning

# check_time
if [ "false" == "$CHECK_TIME" ]; then
    echo "check_time: false" >> $CONFIG_YAML_FILE
fi

# docker_remove_delay
if [ "1" != "$DOCKER_REMOVE_DELAY" ]; then
    echo "docker_remove_delay: $DOCKER_REMOVE_DELAY" >> $CONFIG_YAML_FILE
fi

# gc_delay
if [ "2" != "$GC_DELAY" ]; then
    echo "gc_delay: $GC_DELAY" >> $CONFIG_YAML_FILE
fi

# log_directory
if [ "/genconf/logs" != "$LOG_DIRECTORY" ]; then
    echo "log_directory: $LOG_DIRECTORY" >> $CONFIG_YAML_FILE
fi

# process_timeout
if [ "120" != "$PROCESS_TIMEOUT" ]; then
    echo "process_timeout: $PROCESS_TIMEOUT" >> $CONFIG_YAML_FILE
fi

####################################################
# Security And Authentication

# oauth_enabled
if [ "false" == "$OAUTH_ENABLED" ]; then
    echo "oauth_enabled: false" >> $CONFIG_YAML_FILE
fi

# telemetry_enabled
if [ "false" == "$TELEMETRY_ENABLED" ]; then
    echo "telemetry_enabled: false" >> $CONFIG_YAML_FILE
fi

####################################################
# Rexray Configuration

# NOTE: This feature is considered experimental: use it at your own risk.
# We might add, change, or delete any functionality as described in this document.
# See https://dcos.io/docs/1.8/usage/storage/external-storage/
if [ "$VOLUME_DRIVER" == "rexray" ]; then

if [ ${AUTH_URL##*/}=="v3" ]; then
    extra_configs="domainName:           $DOMAIN_NAME"
else
    extra_configs=""
fi

    echo "rexray_config:" >> $CONFIG_YAML_FILE
    echo "  rexray:" >> $CONFIG_YAML_FILE
    echo "    modules:" >> $CONFIG_YAML_FILE
    echo "      default-admin:" >> $CONFIG_YAML_FILE
    echo "        host: tcp://127.0.0.1:61003" >> $CONFIG_YAML_FILE
    echo "    storageDrivers:" >> $CONFIG_YAML_FILE
    echo "    - openstack" >> $CONFIG_YAML_FILE
    echo "    volume:" >> $CONFIG_YAML_FILE
    echo "      mount:" >> $CONFIG_YAML_FILE
    echo "        preempt: $REXRAY_PREEMPT" >> $CONFIG_YAML_FILE
    echo "  openstack:" >> $CONFIG_YAML_FILE
    echo "    authUrl:              $AUTH_URL" >> $CONFIG_YAML_FILE
    echo "    username:             $USERNAME" >> $CONFIG_YAML_FILE
    echo "    password:             $PASSWORD" >> $CONFIG_YAML_FILE
    echo "    tenantName:           $TENANT_NAME" >> $CONFIG_YAML_FILE
    echo "    regionName:           $REGION_NAME" >> $CONFIG_YAML_FILE
    echo "    availabilityZoneName: nova" >> $CONFIG_YAML_FILE
    echo "    $extra_configs" >> $CONFIG_YAML_FILE
fi


cd $GENCONF_SCRIPT_DIR
sudo bash $GENCONF_SCRIPT_DIR/dcos_generate_config.sh --genconf

cd $GENCONF_SCRIPT_DIR/genconf/serve
sudo bash $GENCONF_SCRIPT_DIR/genconf/serve/dcos_install.sh --no-block-dcos-setup $ROLES
