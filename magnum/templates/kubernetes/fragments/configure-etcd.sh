#!/bin/sh

. /etc/sysconfig/heat-params

myip=$(ip addr show eth0 |
awk '$1 == "inet" {print $2}' | cut -f1 -d/)

cat > /etc/etcd/etcd.conf <<EOF
ETCD_NAME="$myip"
ETCD_DATA_DIR="/var/lib/etcd/default.etcd"
ETCD_LISTEN_CLIENT_URLS="http://0.0.0.0:2379"
ETCD_LISTEN_PEER_URLS="http://$myip:2380"

ETCD_ADVERTISE_CLIENT_URLS="http://$myip:2379"
ETCD_INITIAL_ADVERTISE_PEER_URLS="http://$myip:2380"
ETCD_DISCOVERY="$ETCD_DISCOVERY_URL"
EOF

if [ -n "$HTTP_PROXY" ]; then
    echo "ETCD_DISCOVERY_PROXY=$HTTP_PROXY" >> /etc/etcd/etcd.conf
fi
