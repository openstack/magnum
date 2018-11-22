#!/bin/sh

. /etc/sysconfig/heat-params

CERT_DIR=/etc/docker
PROTOCOL=https
FLANNEL_OPTIONS="-etcd-cafile $CERT_DIR/ca.crt \
-etcd-certfile $CERT_DIR/server.crt \
-etcd-keyfile $CERT_DIR/server.key"
DOCKER_NETWORK_OPTIONS="--cluster-store etcd://$ETCD_SERVER_IP:2379 \
--cluster-store-opt kv.cacertfile=$CERT_DIR/ca.crt \
--cluster-store-opt kv.certfile=$CERT_DIR/server.crt \
--cluster-store-opt kv.keyfile=$CERT_DIR/server.key \
--cluster-advertise $SWARM_NODE_IP:9379"

if [ "$TLS_DISABLED" = "True" ]; then
    PROTOCOL=http
    FLANNEL_OPTIONS=""
    DOCKER_NETWORK_OPTIONS="--cluster-store etcd://$ETCD_SERVER_IP:2379 \
    --cluster-advertise $SWARM_NODE_IP:9379"
fi

echo "Configuring ${NETWORK_DRIVER} network service ..."

if [ "$NETWORK_DRIVER" == "docker" ]; then
    sed -i "/^DOCKER_NETWORK_OPTIONS=/ s#=.*#='$DOCKER_NETWORK_OPTIONS'#" \
        /etc/sysconfig/docker-network
fi

if [ "$NETWORK_DRIVER" != "flannel" ]; then
    exit 0
fi

SYSTEMD_UNITS_DIR=/etc/systemd/system/
FLANNELD_CONFIG=/etc/sysconfig/flanneld
FLANNEL_DOCKER_BRIDGE_BIN=/usr/local/bin/flannel-docker-bridge
FLANNEL_DOCKER_BRIDGE_SERVICE=/etc/systemd/system/flannel-docker-bridge.service
FLANNEL_IPTABLES_FORWARD_ACCEPT_SERVICE=flannel-iptables-forward-accept.service
DOCKER_FLANNEL_CONF=/etc/systemd/system/docker.service.d/flannel.conf
FLANNEL_DOCKER_BRIDGE_CONF=/etc/systemd/system/flanneld.service.d/flannel-docker-bridge.conf

mkdir -p /etc/systemd/system/docker.service.d
mkdir -p /etc/systemd/system/flanneld.service.d

sed -i '
/^FLANNEL_ETCD=/ s|=.*|="'"$PROTOCOL"'://'"$ETCD_SERVER_IP"':2379"|
' $FLANNELD_CONFIG

sed -i '/FLANNEL_OPTIONS/'d $FLANNELD_CONFIG

cat >> $FLANNELD_CONFIG <<EOF
FLANNEL_OPTIONS="$FLANNEL_OPTIONS"
EOF

cat >> $FLANNEL_DOCKER_BRIDGE_BIN <<EOF
#!/bin/sh

if ! [ "\$FLANNEL_SUBNET" ] && [ "\$FLANNEL_MTU" ] ; then
    echo "ERROR: missing required environment variables." >&2
    exit 1
fi

# NOTE(mnaser): Since Docker 1.13, it does not set the default forwarding
#               policy to ACCEPT which will cause CNI networking to fail.
iptables -P FORWARD ACCEPT

mkdir -p /run/flannel/
cat > /run/flannel/docker <<EOF
DOCKER_NETWORK_OPTIONS="--bip=\$FLANNEL_SUBNET --mtu=\$FLANNEL_MTU"
EOF

chown root:root $FLANNEL_DOCKER_BRIDGE_BIN
chmod 0755 $FLANNEL_DOCKER_BRIDGE_BIN

cat >> $FLANNEL_DOCKER_BRIDGE_SERVICE <<EOF
[Unit]
After=flanneld.service
Before=docker.service
Requires=flanneld.service

[Service]
Type=oneshot
EnvironmentFile=/run/flannel/subnet.env
ExecStart=/usr/local/bin/flannel-docker-bridge

[Install]
WantedBy=docker.service
EOF

chown root:root $FLANNEL_DOCKER_BRIDGE_SERVICE
chmod 0644 $FLANNEL_DOCKER_BRIDGE_SERVICE

cat >> $DOCKER_FLANNEL_CONF <<EOF
[Unit]
Requires=flannel-docker-bridge.service
After=flannel-docker-bridge.service

[Service]
EnvironmentFile=/run/flannel/docker
EOF

chown root:root $DOCKER_FLANNEL_CONF
chmod 0644 $DOCKER_FLANNEL_CONF

cat >> $FLANNEL_DOCKER_BRIDGE_CONF <<EOF
[Unit]
Requires=flannel-docker-bridge.service
Before=flannel-docker-bridge.service

[Install]
Also=flannel-docker-bridge.service
EOF

chown root:root $FLANNEL_DOCKER_BRIDGE_CONF
chmod 0644 $FLANNEL_DOCKER_BRIDGE_CONF

# Workaround for https://github.com/coreos/flannel/issues/799
# Not solved upstream properly yet.
cat >> "${SYSTEMD_UNITS_DIR}${FLANNEL_IPTABLES_FORWARD_ACCEPT_SERVICE}" <<EOF
[Unit]
After=flanneld.service docker.service kubelet.service kube-proxy.service
Requires=flanneld.service

[Service]
Type=oneshot
ExecStart=/usr/sbin/iptables -P FORWARD ACCEPT
ExecStartPost=/usr/sbin/iptables -S

[Install]
WantedBy=flanneld.service
EOF

chown root:root "${SYSTEMD_UNITS_DIR}${FLANNEL_IPTABLES_FORWARD_ACCEPT_SERVICE}"
chmod 0644 "${SYSTEMD_UNITS_DIR}${FLANNEL_IPTABLES_FORWARD_ACCEPT_SERVICE}"
systemctl daemon-reload
systemctl enable "${FLANNEL_IPTABLES_FORWARD_ACCEPT_SERVICE}"

echo "activating service flanneld"
systemctl enable flanneld
systemctl --no-block start flanneld
