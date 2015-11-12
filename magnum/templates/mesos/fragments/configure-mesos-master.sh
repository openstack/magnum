#!/bin/sh

. /etc/sysconfig/heat-params

echo "configuring mesos (master)"
mkdir -p /etc/marathon/conf

# Set a ID for each master node
echo "1" > /etc/zookeeper/conf/myid

# Append server IP address(es)
echo "
server.1=$MESOS_MASTER_IP:2888:3888
" >> /etc/zookeeper/conf/zoo.cfg

# List of Zookeeper URLs
echo "zk://$MESOS_MASTER_IP:2181/mesos" > /etc/mesos/zk
echo "zk://$MESOS_MASTER_IP:2181/mesos" > /etc/marathon/conf/master
echo "zk://$MESOS_MASTER_IP:2181/marathon" > /etc/marathon/conf/zk

# The size of the quorum of replicas
echo "1" > /etc/mesos-master/quorum

# The hostname the master should advertise in ZooKeeper
echo "$MESOS_MASTER_IP" > /etc/mesos-master/hostname
echo "$MESOS_MASTER_IP" > /etc/marathon/conf/hostname

# The IP address to listen on
echo "$MESOS_MASTER_IP" > /etc/mesos-master/ip

# The IP address to listen on
echo "$CLUSTER_NAME" > /etc/mesos-master/cluster
