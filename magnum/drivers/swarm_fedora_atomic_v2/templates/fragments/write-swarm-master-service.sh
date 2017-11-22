#!/bin/bash

. /etc/sysconfig/heat-params

set -x

if [ "$VERIFY_CA" == "True" ]; then
    VERIFY_CA=""
else
    VERIFY_CA="-k"
fi

if [ "${IS_PRIMARY_MASTER}" = "True" ]; then
    cat > /usr/local/bin/magnum-start-swarm-manager << START_SWARM_BIN
#!/bin/bash -xe

docker swarm init --advertise-addr "${SWARM_NODE_IP}"
if [[ \$? -eq 0 ]]; then
    status="SUCCESS"
    msg="Swarm init was successful."
else
    status="FAILURE"
    msg="Failed to init swarm."
fi
sh -c "${WAIT_CURL} ${VERIFY_CA} --data-binary '{\"status\": \"\$status\", \"reason\": \"\$msg\"}'"
START_SWARM_BIN
else
    if [ "${TLS_DISABLED}" = 'False'  ]; then
        tls="--tlsverify"
        tls=$tls" --tlscacert=/etc/docker/ca.crt"
        tls=$tls" --tlskey=/etc/docker/server.key"
        tls=$tls" --tlscert=/etc/docker/server.crt"
    fi

    cat > /usr/local/bin/magnum-start-swarm-manager << START_SWARM_BIN
#!/bin/bash -xe
i=0
until token=\$(docker $tls -H $PRIMARY_MASTER_IP swarm join-token --quiet manager)
do
    ((i++))
    [ \$i -lt 5 ] || break;
    sleep 5
done

if [[ -z \$token ]] ; then
    sh -c "${WAIT_CURL} ${VERIFY_CA} --data-binary '{\"status\": \"FAILURE\", \"reason\": \"Failed to retrieve swarm join token.\"}'"
fi

i=0
until docker swarm join --token \$token $PRIMARY_MASTER_IP:2377
do
    ((i++))
    [ \$i -lt 5 ] || break;
    sleep 5
done
if [[ \$i -ge 5 ]] ; then
    sh -c "${WAIT_CURL} ${VERIFY_CA} --data-binary '{\"status\": \"FAILURE\", \"reason\": \"Manager failed to join swarm.\"}'"
else
    sh -c "${WAIT_CURL} ${VERIFY_CA} --data-binary '{\"status\": \"SUCCESS\", \"reason\": \"Manager joined swarm.\"}'"
fi
START_SWARM_BIN
fi
chmod +x /usr/local/bin/magnum-start-swarm-manager

cat > /etc/systemd/system/swarm-manager.service << END_SERVICE
[Unit]
Description=Swarm Manager
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/magnum-start-swarm-manager

[Install]
WantedBy=multi-user.target
END_SERVICE

chown root:root /etc/systemd/system/swarm-manager.service
chmod 644 /etc/systemd/system/swarm-manager.service

systemctl daemon-reload
systemctl start --no-block swarm-manager

