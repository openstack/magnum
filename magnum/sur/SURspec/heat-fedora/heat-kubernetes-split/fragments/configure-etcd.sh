#!/bin/sh

myip=$(ip addr show eth0 |
awk '$1 == "inet" {print $2}' | cut -f1 -d/)

cat > /etc/etcd/etcd.conf <<EOF
# [member]
ETCD_NAME=default
ETCD_DATA_DIR="/var/lib/etcd/default.etcd"
ETCD_LISTEN_CLIENT_URLS="http://0.0.0.0:4001"

[cluster]
ETCD_ADVERTISE_CLIENT_URLS="http://$myip:4001"
EOF
