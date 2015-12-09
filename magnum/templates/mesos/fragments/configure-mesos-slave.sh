#!/bin/bash

. /etc/sysconfig/heat-params

echo "Configuring mesos (slave)"

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

# The hostname the slave should report
echo "$myip" > /etc/mesos-slave/hostname

# The IP address to listen on
echo "$myip" > /etc/mesos-slave/ip

# List of containerizer implementations
echo "docker,mesos" > /etc/mesos-slave/containerizers

# Amount of time to wait for an executor to register
cat > /etc/mesos-slave/executor_registration_timeout <<EOF
$EXECUTOR_REGISTRATION_TIMEOUT
EOF
