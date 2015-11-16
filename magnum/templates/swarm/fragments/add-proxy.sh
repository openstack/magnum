#!/bin/sh

. /etc/sysconfig/heat-params

DOCKER_PROXY_CONF=/etc/systemd/system/docker.service.d/proxy.conf
BASH_RC=/etc/bashrc

if [ -n "$HTTP_PROXY" ]; then
    cat <<EOF | sed "s/^ *//" > $DOCKER_PROXY_CONF
    [Service]
    Environment=HTTP_PROXY=$HTTP_PROXY
EOF

    systemctl daemon-reload
    systemctl --no-block restart docker.service

    if [ -f "$BASH_RC" ]; then
        echo "declare -x http_proxy=$HTTP_PROXY" >> $BASH_RC
    else
        echo "File $BASH_RC does not exist, not setting http_proxy"
    fi
fi

if [ -n "$HTTPS_PROXY" ]; then
    if [ -f $BASH_RC ]; then
        echo "declare -x https_proxy=$HTTPS_PROXY" >> $BASH_RC
    else
        echo "File $BASH_RC does not exist, not setting https_proxy"
    fi
fi

if [ -f "$BASH_RC" ]; then
    if [ -n "$NO_PROXY" ]; then
        echo "declare -x no_proxy=$NO_PROXY" >> $BASH_RC
    else
        echo "declare -x no_proxy=$SWARM_API_IP,$ETCD_SERVER_IP,$SWARM_NODE_IP" >> $BASH_RC
    fi
else
    echo "File $BASH_RC does not exist, not setting no_proxy"
fi
