#!/bin/sh

. /etc/sysconfig/heat-params

if [ "$NETWORK_DRIVER" != "flannel" ]; then
    exit 0
fi

FLANNEL_DOCKER_BRIDGE_BIN=/usr/local/bin/flannel-docker-bridge
FLANNEL_DOCKER_BRIDGE_SERVICE=/etc/systemd/system/flannel-docker-bridge.service
DOCKER_FLANNEL_CONF=/etc/systemd/system/docker.service.d/flannel.conf
FLANNEL_DOCKER_BRIDGE_CONF=/etc/systemd/system/flanneld.service.d/flannel-docker-bridge.conf

mkdir -p /etc/systemd/system/docker.service.d
mkdir -p /etc/systemd/system/flanneld.service.d

cat >> $FLANNEL_DOCKER_BRIDGE_BIN <<EOF
#!/bin/sh

if ! [ "\$FLANNEL_SUBNET" ] && [ "\$FLANNEL_MTU" ] ; then
  echo "ERROR: missing required environment variables." >&2
  exit 1
fi

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

echo "activating service flanneld"
systemctl enable flanneld
systemctl --no-block start flanneld
