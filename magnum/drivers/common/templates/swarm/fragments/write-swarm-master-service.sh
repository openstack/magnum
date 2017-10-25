#!/bin/sh

CERT_DIR=/etc/docker

if [ "$VERIFY_CA" == "True" ]; then
    VERIFY_CA=""
else
    VERIFY_CA="-k"
fi

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
ExecStart=/usr/bin/docker run   --name swarm-manager \\
                                -v $CERT_DIR:$CERT_DIR:Z \\
                                -p 2376:2375 \\
                                -e http_proxy=$HTTP_PROXY \\
                                -e https_proxy=$HTTPS_PROXY \\
                                -e no_proxy=$NO_PROXY \\
                                swarm:$SWARM_VERSION \\
                                manage -H tcp://0.0.0.0:2375 \\
                                --strategy $SWARM_STRATEGY \\
                                --replication \\
                                --advertise $NODE_IP:2376 \\
END_SERVICE_TOP

if [ $TLS_DISABLED = 'False'  ]; then

cat >> /etc/systemd/system/swarm-manager.service << END_TLS
                                --tlsverify \\
                                --tlscacert=$CERT_DIR/ca.crt \\
                                --tlskey=$CERT_DIR/server.key \\
                                --tlscert=$CERT_DIR/server.crt \\
                                --discovery-opt kv.cacertfile=$CERT_DIR/ca.crt \\
                                --discovery-opt kv.certfile=$CERT_DIR/server.crt \\
                                --discovery-opt kv.keyfile=$CERT_DIR/server.key \\
END_TLS

fi

UUID=`uuidgen`
cat >> /etc/systemd/system/swarm-manager.service << END_SERVICE_BOTTOM
                                  etcd://$ETCD_SERVER_IP:2379/v2/keys/swarm/
ExecStop=/usr/bin/docker stop swarm-manager
Restart=always
ExecStartPost=/usr/bin/$WAIT_CURL $VERIFY_CA \\
    --data-binary '{"status": "SUCCESS", "reason": "Setup complete", "data": "OK", "id": "$UUID"}'

[Install]
WantedBy=multi-user.target
END_SERVICE_BOTTOM

chown root:root /etc/systemd/system/swarm-manager.service
chmod 644 /etc/systemd/system/swarm-manager.service
