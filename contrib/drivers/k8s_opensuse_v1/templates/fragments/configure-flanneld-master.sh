#!/bin/sh

. /etc/sysconfig/heat-params

if [ "$NETWORK_DRIVER" != "flannel" ]; then
    exit 0
fi

FLANNEL_ETCD="http://127.0.0.1:2379"
FLANNEL_JSON=/etc/sysconfig/flannel-network.json
FLANNELD_CONFIG=/etc/sysconfig/flanneld

sed -i '
    /^FLANNEL_ETCD=/ s/=.*/="http:\/\/127.0.0.1:2379"/
    /^#FLANNEL_OPTIONS=/ s//FLANNEL_OPTIONS="-iface eth0 --ip-masq"/
' /etc/sysconfig/flanneld

cat >> /etc/sysconfig/flanneld <<EOF

# etcd config key.  This is the configuration key that flannel queries
# For address range assignment
FLANNEL_ETCD_KEY="/flannel/network"
EOF

. /etc/sysconfig/flanneld

# Generate a flannel configuration that we will
# store into etcd using curl.
cat > $FLANNEL_JSON <<EOF
{
  "Network": "$FLANNEL_NETWORK_CIDR",
  "Subnetlen": $FLANNEL_NETWORK_SUBNETLEN,
  "SubnetMin": "$FLANNEL_NETWORK_SUBNET_MIN",
  "SubnetMax": "$FLANNEL_NETWORK_SUBNET_MAX",
  "Backend": {
    "Type": "$FLANNEL_BACKEND"
  }
}
EOF

# wait for etcd to become active (we will need it to push the flanneld config)
while ! curl -sf -o /dev/null $FLANNEL_ETCD/v2/keys/; do
    echo "waiting for etcd"
    sleep 1
done

# put the flannel config in etcd
echo "creating flanneld config in etcd"
curl -sf -L $FLANNEL_ETCD/v2/keys$FLANNEL_ETCD_KEY/config \
  -X PUT \
  --data-urlencode value@$FLANNEL_JSON

echo "activating flanneld service"
systemctl enable flanneld

echo "starting flanneld service"
systemctl --no-block start flanneld
