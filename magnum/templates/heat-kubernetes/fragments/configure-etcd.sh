#!/bin/sh

. /etc/sysconfig/heat-params

myip=$(ip addr show eth0 |
awk '$1 == "inet" {print $2}' | cut -f1 -d/)

cat > /etc/etcd/etcd.conf <<EOF
# [member]
ETCD_NAME="$myip"
ETCD_DATA_DIR="/var/lib/etcd/default.etcd"
ETCD_LISTEN_CLIENT_URLS="http://0.0.0.0:4001"
ETCD_LISTEN_PEER_URLS="http://$myip:7001"

[cluster]
ETCD_ADVERTISE_CLIENT_URLS="http://$myip:4001"
ETCD_INITIAL_ADVERTISE_PEER_URLS="http://$myip:7001"
ETCD_DISCOVERY="$ETCD_DISCOVERY_URL"
EOF
