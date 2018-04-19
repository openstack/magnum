#!/bin/sh

. /etc/sysconfig/heat-params

if [ "$NETWORK_DRIVER" != "flannel" ]; then
    exit 0
fi

FLANNEL_JSON=/etc/sysconfig/flannel-network.json
FLANNELD_CONFIG=/etc/sysconfig/flanneld

cat > /etc/sysconfig/flanneld <<EOF
FLANNEL_ETCD_ENDPOINTS="http://127.0.0.1:2379"
FLANNEL_ETCD_PREFIX="/atomic.io/network"
FLANNEL_OPTIONS=
EOF

# Generate a flannel configuration that we will
# store into etcd using curl.
cat > $FLANNEL_JSON <<EOF
{
  "Network": "$FLANNEL_NETWORK_CIDR",
  "Subnetlen": $FLANNEL_NETWORK_SUBNETLEN,
  "Backend": {
    "Type": "$FLANNEL_BACKEND"
  }
}
EOF
