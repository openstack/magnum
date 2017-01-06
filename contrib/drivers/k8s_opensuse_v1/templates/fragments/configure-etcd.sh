#!/bin/sh

. /etc/sysconfig/heat-params

myip="$KUBE_NODE_IP"

sed -i '
    /ETCD_NAME=/c ETCD_NAME="'$myip'"
    /ETCD_DATA_DIR=/c ETCD_DATA_DIR="/var/lib/etcd/default.etcd"
    /ETCD_LISTEN_CLIENT_URLS=/c ETCD_LISTEN_CLIENT_URLS="http://0.0.0.0:2379"
    /ETCD_LISTEN_PEER_URLS=/c ETCD_LISTEN_PEER_URLS="http://'$myip':2380"
    /ETCD_ADVERTISE_CLIENT_URLS=/c ETCD_ADVERTISE_CLIENT_URLS="http://'$myip':2379"
    /ETCD_INITIAL_ADVERTISE_PEER_URLS=/c ETCD_INITIAL_ADVERTISE_PEER_URLS="http://'$myip':2380"
    /ETCD_DISCOVERY=/c ETCD_DISCOVERY="'$ETCD_DISCOVERY_URL'"
' /etc/sysconfig/etcd

echo "activating etcd service"
systemctl enable etcd

echo "starting etcd service"
systemctl --no-block start etcd
