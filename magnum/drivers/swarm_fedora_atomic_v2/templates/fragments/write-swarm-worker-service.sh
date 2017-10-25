#!/bin/bash

. /etc/sysconfig/heat-params

set -x

if [ "$VERIFY_CA" == "True" ]; then
    VERIFY_CA=""
else
    VERIFY_CA="-k"
fi

if [ "${TLS_DISABLED}" = 'False'  ]; then
    tls="--tlsverify"
    tls=$tls" --tlscacert=/etc/docker/ca.crt"
    tls=$tls" --tlskey=/etc/docker/server.key"
    tls=$tls" --tlscert=/etc/docker/server.crt"
fi
cat > /usr/local/bin/magnum-start-swarm-worker << START_SWARM_BIN
#!/bin/bash -ex

i=0
until token=\$(/usr/bin/docker $tls -H $SWARM_API_IP swarm join-token --quiet worker)
do
    ((i++))
    [ \$i -lt 5 ] || break;
    sleep 5
done

if [[ -z \$token ]] ; then
    sh -c "${WAIT_CURL} ${VERIFY_CA} --data-binary '{\"status\": \"FAILURE\", \"reason\": \"Failed to retrieve swarm join token.\"}'"
fi

i=0
until docker swarm join --token \$token $SWARM_API_IP:2377
do
    ((i++))
    [ \$i -lt 5 ] || break;
    sleep 5
done
if [[ \$i -ge 5 ]] ; then
    sh -c "${WAIT_CURL} ${VERIFY_CA} --data-binary '{\"status\": \"FAILURE\", \"reason\": \"Node failed to join swarm.\"}'"
else
    sh -c "${WAIT_CURL} ${VERIFY_CA} --data-binary '{\"status\": \"SUCCESS\", \"reason\": \"Node joined swarm.\"}'"
fi
START_SWARM_BIN

chmod +x /usr/local/bin/magnum-start-swarm-worker

cat > /etc/systemd/system/swarm-worker.service << END_SERVICE
[Unit]
Description=Swarm Worker
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/magnum-start-swarm-worker

[Install]
WantedBy=multi-user.target
END_SERVICE

chown root:root /etc/systemd/system/swarm-worker.service
chmod 644 /etc/systemd/system/swarm-worker.service

systemctl daemon-reload
systemctl start --no-block swarm-worker
