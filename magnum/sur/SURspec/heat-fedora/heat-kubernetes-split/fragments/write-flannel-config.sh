#!/bin/sh

. /etc/sysconfig/heat-params
. /etc/sysconfig/flanneld

FLANNEL_JSON=/etc/sysconfig/flannel-network.json

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

