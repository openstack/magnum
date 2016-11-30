#!/bin/sh

. /etc/sysconfig/heat-params

if [ "$NETWORK_DRIVER" != "flannel" ]; then
    exit 0
fi

. /etc/sysconfig/flanneld

FLANNEL_CONFIG_BIN=/usr/local/bin/flannel-config
FLANNEL_CONFIG_SERVICE=/etc/systemd/system/flannel-config.service
FLANNEL_JSON=/etc/sysconfig/flannel-network.json

echo "creating $FLANNEL_CONFIG_BIN"
cat > $FLANNEL_CONFIG_BIN <<EOF
#!/bin/sh

if ! [ -f "$FLANNEL_JSON" ]; then
  echo "ERROR: missing network configuration file" >&2
  exit 1
fi

if [ -z "$FLANNEL_ETCD_ENDPOINTS" ] || [ -z "$FLANNEL_ETCD_PREFIX" ]; then
  echo "ERROR: missing required configuration" >&2
  exit 1
fi

echo "creating flanneld config in etcd"
while ! curl -sf -L $FLANNEL_ETCD_ENDPOINTS/v2/keys${FLANNEL_ETCD_PREFIX}/config \
        -X PUT --data-urlencode value@${FLANNEL_JSON}; do
    echo "waiting for etcd"
    sleep 1
done
EOF

cat > $FLANNEL_CONFIG_SERVICE <<EOF
[Unit]
After=etcd.service
Requires=etcd.service

[Service]
Type=oneshot
EnvironmentFile=/etc/sysconfig/flanneld
ExecStart=$FLANNEL_CONFIG_BIN

[Install]
WantedBy=multi-user.target
EOF

chown root:root $FLANNEL_CONFIG_BIN
chmod 0755 $FLANNEL_CONFIG_BIN

chown root:root $FLANNEL_CONFIG_SERVICE
chmod 0644 $FLANNEL_CONFIG_SERVICE

systemctl enable flannel-config
systemctl start --no-block flannel-config
