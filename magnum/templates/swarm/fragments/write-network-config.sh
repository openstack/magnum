#!/bin/sh

. /etc/sysconfig/heat-params

if [ "$NETWORK_DRIVER" != "flannel" ]; then
    exit 0
fi

FLANNEL_JSON=/etc/sysconfig/flannel-network.json
FLANNEL_NETWORK_CIDR="$FLANNEL_NETWORK_CIDR"
FLANNEL_NETWORK_SUBNETLEN="$FLANNEL_NETWORK_SUBNETLEN"
FLANNEL_USE_VXLAN="$FLANNEL_USE_VXLAN"

if [ "$FLANNEL_USE_VXLAN" == "true" ]; then
    use_vxlan=1
fi

# Generate a flannel configuration that we will
# store into etcd using curl.
cat > $FLANNEL_JSON <<EOF
{
  "Network": "$FLANNEL_NETWORK_CIDR",
  "Subnetlen": $FLANNEL_NETWORK_SUBNETLEN
EOF

if [ "$use_vxlan" = 1 ]; then
cat >> $FLANNEL_JSON <<EOF
  ,
  "Backend": {
    "Type": "vxlan"
  }
EOF
fi

cat >> $FLANNEL_JSON <<EOF
}
EOF
