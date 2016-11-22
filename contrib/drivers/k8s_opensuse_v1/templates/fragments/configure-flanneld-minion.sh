#!/bin/sh

. /etc/sysconfig/heat-params

if [ "$NETWORK_DRIVER" != "flannel" ]; then
    exit 0
fi

sed -i '
    /^FLANNEL_ETCD_ENDPOINTS=/ s|=.*|="http://'"$ETCD_SERVER_IP"':2379"|
    /^#FLANNEL_OPTIONS=/ s//FLANNEL_OPTIONS="-iface eth0 --ip-masq"/
' /etc/sysconfig/flanneld

cat >> /etc/sysconfig/flanneld <<EOF

# etcd config key.  This is the configuration key that flannel queries
# For address range assignment
FLANNEL_ETCD_KEY="/flannel/network"
EOF

echo "activating flanneld service"
systemctl enable flanneld

echo "starting flanneld service"
systemctl --no-block start flanneld
