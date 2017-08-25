#!/bin/sh

. /etc/sysconfig/heat-params

DOCKER_HTTP_PROXY_CONF=/etc/systemd/system/docker.service.d/http_proxy.conf

DOCKER_HTTPS_PROXY_CONF=/etc/systemd/system/docker.service.d/https_proxy.conf

DOCKER_NO_PROXY_CONF=/etc/systemd/system/docker.service.d/no_proxy.conf

DOCKER_RESTART=0

BASH_RC=/etc/bashrc

mkdir -p /etc/systemd/system/docker.service.d

if [ -n "$HTTP_PROXY" ]; then
    cat <<EOF | sed "s/^ *//" > $DOCKER_HTTP_PROXY_CONF
    [Service]
    Environment=HTTP_PROXY=$HTTP_PROXY
EOF

    DOCKER_RESTART=1

    if [ -f "$BASH_RC" ]; then
        echo "declare -x http_proxy=$HTTP_PROXY" >> $BASH_RC
    else
        echo "File $BASH_RC does not exist, not setting http_proxy"
    fi
fi

if [ -n "$HTTPS_PROXY" ]; then
    cat <<EOF | sed "s/^ *//" > $DOCKER_HTTPS_PROXY_CONF
    [Service]
    Environment=HTTPS_PROXY=$HTTPS_PROXY
EOF

    DOCKER_RESTART=1

    if [ -f "$BASH_RC" ]; then
        echo "declare -x https_proxy=$HTTPS_PROXY" >> $BASH_RC
    else
        echo "File $BASH_RC does not exist, not setting https_proxy"
    fi
fi

if [ -n "$HTTP_PROXY" -o -n "$HTTPS_PROXY" ]; then
    if [ -n "$NO_PROXY" ]; then
        cat <<EOF | sed "s/^ *//" > $DOCKER_NO_PROXY_CONF
        [Service]
        Environment=NO_PROXY=$NO_PROXY
EOF

        DOCKER_RESTART=1

        if [ -f "$BASH_RC" ]; then
            echo "declare -x no_proxy=$NO_PROXY" >> $BASH_RC
        else
            echo "File $BASH_RC does not exist, not setting no_proxy"
        fi
    fi
fi

if [ "$DOCKER_RESTART" -eq 1 ]; then
    systemctl daemon-reload
    systemctl --no-block restart docker.service
fi
