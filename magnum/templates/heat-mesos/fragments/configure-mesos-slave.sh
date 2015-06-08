#!/bin/sh

. /etc/sysconfig/heat-params

echo "configuring mesos (slave)"

myip=$(ip addr show eth0 |
       awk '$1 == "inet" {print $2}' | cut -f1 -d/)

# This specifies how to connect to a master or a quorum of masters
echo "zk://$MESOS_MASTER_IP:2181/mesos" > /etc/mesos/zk

# The hostname the slave should report
echo "$myip" > /etc/mesos-slave/hostname

# The IP address to listen on
echo "$myip" > /etc/mesos-slave/ip

# List of containerizer implementations
echo "docker,mesos" > /etc/mesos-slave/containerizers

# Amount of time to wait for an executor to register
echo "$EXECUTOR_REGISTRATION_TIMEOUT" > /etc/mesos-slave/executor_registration_timeout
