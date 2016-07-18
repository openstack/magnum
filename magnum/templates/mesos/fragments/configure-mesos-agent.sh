#!/bin/bash

. /etc/sysconfig/heat-params

echo "Configuring mesos (agent)"

myip=$(ip addr show eth0 |
       awk '$1 == "inet" {print $2}' | cut -f1 -d/)

zk=""
for master_ip in $MESOS_MASTERS_IPS; do
    zk="${zk}${master_ip}:2181,"
done
# Remove last ','
zk=${zk::-1}
# Zookeeper URL. This specifies how to connect to a quorum of masters
# Format: zk://host1:port1,...,hostN:portN/path
echo "zk://${zk}/mesos" > /etc/mesos/zk

# The hostname the agent should report
echo "$myip" > /etc/mesos-agent/hostname

# The IP address to listen on
echo "$myip" > /etc/mesos-agent/ip

# List of containerizer implementations
echo "docker,mesos" > /etc/mesos-agent/containerizers

# Amount of time to wait for an executor to register
cat > /etc/mesos-agent/executor_registration_timeout <<EOF
$EXECUTOR_REGISTRATION_TIMEOUT
EOF

if [ -n "$ISOLATION" ]; then
    echo "$ISOLATION" > /etc/mesos-agent/isolation
fi

if [ -n "$WORK_DIR" ]; then
    echo "$WORK_DIR" > /etc/mesos-agent/work_dir
fi

if [ -n "$IMAGE_PROVIDERS" ]; then
    if [ -n "$ISOLATION" ]; then
        echo "$IMAGE_PROVIDERS" > /etc/mesos-agent/image_providers
    else
        echo "isolation doesn't exist, not setting image_providers"
    fi
fi

if [ -n "$EXECUTOR_ENVIRONMENT_VARIABLES" ]; then
    echo "$EXECUTOR_ENVIRONMENT_VARIABLES" > /etc/executor_environment_variables
    echo "file:///etc/executor_environment_variables" > /etc/mesos-agent/executor_environment_variables
fi
