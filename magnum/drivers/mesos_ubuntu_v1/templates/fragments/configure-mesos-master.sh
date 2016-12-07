#!/bin/bash

. /etc/sysconfig/heat-params

echo "Configuring mesos (master)"

myip=$(ip addr show eth0 |
    awk '$1 == "inet" {print $2}' | cut -f1 -d/)

# Fix /etc/hosts
sed -i "s/127.0.1.1/$myip/" /etc/hosts

######################################################################
#
# Configure ZooKeeper
#

# List all ZooKeeper nodes
id=1
for master_ip in $MESOS_MASTERS_IPS; do
    echo "server.$((id++))=${master_ip}:2888:3888" >> /etc/zookeeper/conf/zoo.cfg
done

# Set a ID for this node
id=1
for master_ip in $MESOS_MASTERS_IPS; do
    if [ "$master_ip" = "$myip" ]; then
        break
    fi
    id=$((id+1))
done
echo "$id" > /etc/zookeeper/conf/myid

######################################################################
#
# Configure Mesos
#

# Set the ZooKeeper URL
zk="zk://"
for master_ip in $MESOS_MASTERS_IPS; do
    zk="${zk}${master_ip}:2181,"
done
# Remove tailing ',' (format: zk://host1:port1,...,hostN:portN/path)
zk=${zk::-1}
echo "${zk}/mesos" > /etc/mesos/zk

# The IP address to listen on
echo "$myip" > /etc/mesos-master/ip

# The size of the quorum of replicas
echo "$QUORUM" > /etc/mesos-master/quorum

# The hostname advertised in ZooKeeper
echo "$myip" > /etc/mesos-master/hostname

# The cluster name
echo "$CLUSTER_NAME" > /etc/mesos-master/cluster

######################################################################
#
# Configure Marathon
#

mkdir -p /etc/marathon/conf

# Set the ZooKeeper URL
echo "${zk}/mesos" > /etc/marathon/conf/master
echo "${zk}/marathon" > /etc/marathon/conf/zk

# Set the hostname advertised in ZooKeeper
echo "$myip" > /etc/marathon/conf/hostname
