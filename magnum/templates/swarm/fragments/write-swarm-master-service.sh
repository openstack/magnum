#!/bin/sh

cat > /etc/systemd/system/swarm-manager.service << END_SERVICE_TOP
[Unit]
Description=Swarm Manager
After=docker.service etcd.service
Requires=docker.service etcd.service
OnFailure=swarm-manager-failure.service

[Service]
TimeoutStartSec=0
ExecStartPre=-/usr/bin/docker kill swarm-manager
ExecStartPre=-/usr/bin/docker rm swarm-manager
ExecStartPre=-/usr/bin/docker pull swarm:$SWARM_VERSION
ExecStart=/usr/bin/docker run --name swarm-manager \\
                              -v /etc/docker:/etc/docker \\
                              -p 2376:2375 \\
                              -e http_proxy=$HTTP_PROXY \\
                              -e https_proxy=$HTTPS_PROXY \\
                              -e no_proxy=$NO_PROXY \\
                              swarm:$SWARM_VERSION \\
                              manage -H tcp://0.0.0.0:2375 \\
                              --replication \\
                              --advertise $NODE_IP:2376 \\
END_SERVICE_TOP

if [ $TLS_DISABLED = 'False'  ]; then

cat >> /etc/systemd/system/swarm-manager.service << END_TLS
                              --tlsverify \\
                              --tlscacert=/etc/docker/ca.crt \\
                              --tlskey=/etc/docker/server.key \\
                              --tlscert=/etc/docker/server.crt \\
END_TLS

fi

cat >> /etc/systemd/system/swarm-manager.service << END_SERVICE_BOTTOM
                                  etcd://$ETCD_SERVER_IP:2379/v2/keys/swarm/
ExecStop=/usr/bin/docker stop swarm-manager
ExecStartPost=/usr/bin/curl -i -X POST -H 'Content-Type: application/json' -H 'X-Auth-Token: $WAIT_HANDLE_TOKEN' \\
  --data-binary "'"'{"Status": "SUCCESS", "Reason": "Setup complete", "Data": "OK", "UniqueId": "00000"}'"'" \\
  "$WAIT_HANDLE_ENDPOINT"

[Install]
WantedBy=multi-user.target
END_SERVICE_BOTTOM

chown root:root /etc/systemd/system/swarm-manager.service
chmod 644 /etc/systemd/system/swarm-manager.service
