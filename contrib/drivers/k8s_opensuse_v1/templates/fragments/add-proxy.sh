#!/bin/sh

. /etc/sysconfig/heat-params

DOCKER_PROXY_CONF=/etc/systemd/system/docker.service.d/proxy.conf
BASH_RC=/etc/bashrc

mkdir -p /etc/systemd/system/docker.service.d

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
    if [ -f "$BASH_RC" ]; then
        echo "declare -x https_proxy=$HTTPS_PROXY" >> $BASH_RC
    else
        echo "File $BASH_RC does not exist, not setting https_proxy"
    fi
fi

if [ -n "$NO_PROXY" ]; then
    if [ -f "$BASH_RC" ]; then
        echo "declare -x no_proxy=$NO_PROXY" >> $BASH_RC
    else
        echo "File $BASH_RC does not exist, not setting no_proxy"
    fi
fi
