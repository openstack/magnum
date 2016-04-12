#!/bin/sh

. /etc/sysconfig/heat-params

mkdir -p /etc/systemd/system/docker.service.d

cat > /etc/systemd/system/docker.service << END_SERVICE_TOP
[Unit]
Description=Docker Application Container Engine
Documentation=http://docs.docker.com
After=network.target docker.socket
Requires=docker.socket
Wants=docker-storage-setup.service

[Service]
TimeoutStartSec=300
Type=notify
EnvironmentFile=-/etc/sysconfig/docker
EnvironmentFile=-/etc/sysconfig/docker-storage
EnvironmentFile=-/etc/sysconfig/docker-network
Environment=GOTRACEBACK=crash
ExecStart=/usr/bin/docker daemon -H fd:// \\
          -H tcp://0.0.0.0:2375 \\
END_SERVICE_TOP

if [ "$TLS_DISABLED" = 'False'  ]; then

cat >> /etc/systemd/system/docker.service << END_TLS
          --tlsverify \\
          --tlscacert="/etc/docker/ca.crt" \\
          --tlskey="/etc/docker/server.key" \\
          --tlscert="/etc/docker/server.crt" \\
END_TLS

fi

cat >> /etc/systemd/system/docker.service << END_SERVICE_BOTTOM
          \$OPTIONS \\
          \$DOCKER_STORAGE_OPTIONS \\
          \$DOCKER_NETWORK_OPTIONS \\
          \$INSECURE_REGISTRY
LimitNOFILE=1048576
LimitNPROC=1048576
LimitCORE=infinity
MountFlags=slave

[Install]
WantedBy=multi-user.target
END_SERVICE_BOTTOM

chown root:root /etc/systemd/system/docker.service
chmod 644 /etc/systemd/system/docker.service
