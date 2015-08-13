#!/bin/sh

. /etc/sysconfig/heat-params

if [ "$HTTP_PROXY" != "" ]; then
    cat > /etc/systemd/system/docker.service.d/proxy.conf <<EOF
[Service]
Environment=HTTP_PROXY=$HTTP_PROXY
EOF
systemctl daemon-reload
systemctl --no-block restart docker.service
    if [ -f "/etc/bashrc" ]; then
        cat >> /etc/bashrc <<EOF
declare -x http_proxy=$HTTP_PROXY
EOF
    else
        echo "File /etc/bashrc does not exists, not setting http_proxy"
    fi
fi

if [ "$HTTPS_PROXY" != "" ]; then
    if [ -f "/etc/bashrc" ]; then
        cat >> /etc/bashrc <<EOF
declare -x https_proxy=$HTTPS_PROXY
EOF
    else
         echo "File /etc/bashrc does not exists, not setting https_proxy"
    fi
fi

if [ -f "/etc/bashrc" ]; then
    if [ -n "$NO_PROXY" ]; then
        cat >> /etc/bashrc <<EOF
declare -x no_proxy=$NO_PROXY
EOF
    else
        cat>> /etc/bashrc <<EOF
declare -x no_proxy=$SWARM_MANAGER_IP,$SWARM_NODE_IP
EOF
   fi
else
    echo "File /etc/bashrc does not exists, not setting no_proxy"
fi
