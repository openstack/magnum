#!/bin/sh

. /etc/sysconfig/heat-params

myip="$SWARM_NODE_IP"

CONF_FILE=/etc/systemd/system/swarm-agent.service
CERT_DIR=/etc/docker
PROTOCOL=https
ETCDCTL_OPTIONS="--ca-file $CERT_DIR/ca.crt \
--cert-file $CERT_DIR/server.crt \
--key-file $CERT_DIR/server.key"

if [ $TLS_DISABLED = 'True'  ]; then
    PROTOCOL=http
    ETCDCTL_OPTIONS=""
fi

if [ -z "$NO_PROXY" ]; then
    NO_PROXY=$SWARM_API_IP,$ETCD_SERVER_IP,$SWARM_NODE_IP
fi

cat > $CONF_FILE << EOF
[Unit]
Description=Swarm Agent
After=docker.service
Requires=docker.service
OnFailure=swarm-agent-failure.service

[Service]
TimeoutStartSec=0
ExecStartPre=-/usr/bin/docker kill swarm-agent
ExecStartPre=-/usr/bin/docker rm swarm-agent
ExecStartPre=-/usr/bin/docker pull swarm:$SWARM_VERSION
ExecStart=/usr/bin/docker run   -e http_proxy=$HTTP_PROXY \\
                                -e https_proxy=$HTTPS_PROXY \\
                                -e no_proxy=$NO_PROXY \\
                                -v $CERT_DIR:$CERT_DIR:Z \\
                                --name swarm-agent \\
                                swarm:$SWARM_VERSION \\
                                join \\
                                --addr $myip:2375 \\
EOF

if [ $TLS_DISABLED = 'False'  ]; then

cat >> /etc/systemd/system/swarm-agent.service << END_TLS
                                --discovery-opt kv.cacertfile=$CERT_DIR/ca.crt \\
                                --discovery-opt kv.certfile=$CERT_DIR/server.crt \\
                                --discovery-opt kv.keyfile=$CERT_DIR/server.key \\
END_TLS

fi

cat >> /etc/systemd/system/swarm-agent.service << END_SERVICE_BOTTOM
                              etcd://$ETCD_SERVER_IP:2379/v2/keys/swarm/
Restart=always
ExecStop=/usr/bin/docker stop swarm-agent
ExecStartPost=/usr/local/bin/notify-heat

[Install]
WantedBy=multi-user.target
END_SERVICE_BOTTOM

chown root:root $CONF_FILE
chmod 644 $CONF_FILE

SCRIPT=/usr/local/bin/notify-heat

cat > $SCRIPT << EOF
#!/bin/sh
until etcdctl \
    --peers $PROTOCOL://$ETCD_SERVER_IP:2379 \
    $ETCDCTL_OPTIONS --timeout 1s \
    --total-timeout 5s \
    ls /v2/keys/swarm/docker/swarm/nodes/$myip:2375
do
    echo "Waiting for swarm agent registration..."
    sleep 5
done

UUID=`uuidgen`
curl -k -i -X POST -H 'Content-Type: application/json' -H 'X-Auth-Token: $WAIT_HANDLE_TOKEN' \
    --data-binary "'"'{"Status": "SUCCESS", "Reason": "Swarm agent ready", "Data": "OK", "Id": "'${UUID}'"}'"'" \
    "$WAIT_HANDLE_ENDPOINT"
EOF

chown root:root $SCRIPT
chmod 755 $SCRIPT
