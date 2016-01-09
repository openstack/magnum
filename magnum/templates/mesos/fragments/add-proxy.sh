#!/bin/sh

. /etc/sysconfig/heat-params

DOCKER_PROXY_CONF=/etc/default/docker
BASH_RC=/etc/bash.bashrc

if [ -n "$HTTP_PROXY" ]; then
    echo "export http_proxy=$HTTP_PROXY" >> $DOCKER_PROXY_CONF

    if [ -f "$BASH_RC" ]; then
        echo "export http_proxy=$HTTP_PROXY" >> $BASH_RC
    else
        echo "File $BASH_RC does not exist, not setting http_proxy"
    fi
fi

if [ -n "$HTTPS_PROXY" ]; then
    echo "export https_proxy=$HTTPS_PROXY" >> $DOCKER_PROXY_CONF

    if [ -f $BASH_RC ]; then
        echo "export https_proxy=$HTTPS_PROXY" >> $BASH_RC
    else
        echo "File $BASH_RC does not exist, not setting https_proxy"
    fi
fi

if [ -n "$HTTP_PROXY" -o -n $HTTPS_PROXY ]; then
    service docker restart
fi

if [ -f "$BASH_RC" ]; then
    if [ -n "$NO_PROXY" ]; then
        echo "export no_proxy=$NO_PROXY" >> $BASH_RC
    fi
else
    echo "File $BASH_RC does not exist, not setting no_proxy"
fi
