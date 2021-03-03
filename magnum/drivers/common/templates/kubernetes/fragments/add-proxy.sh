set +x
. /etc/sysconfig/heat-params
set -x

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

if [ ${CONTAINER_RUNTIME} = "containerd"  ] ; then
    SERVICE_DIR="/etc/systemd/system/containerd.service.d"
else
    SERVICE_DIR="/etc/systemd/system/docker.service.d"
fi

HTTP_PROXY_CONF=${SERVICE_DIR}/http_proxy.conf

HTTPS_PROXY_CONF=${SERVICE_DIR}/https_proxy.conf

NO_PROXY_CONF=${SERVICE_DIR}/no_proxy.conf

RUNTIME_RESTART=0

BASH_RC=/etc/bashrc

mkdir -p ${SERVICE_DIR}

if [ -n "$HTTP_PROXY" ]; then
    cat <<EOF | sed "s/^ *//" > $HTTP_PROXY_CONF
    [Service]
    Environment=HTTP_PROXY=$HTTP_PROXY
EOF

    RUNTIME_RESTART=1

    if [ -f "$BASH_RC" ]; then
        echo "declare -x http_proxy=$HTTP_PROXY" >> $BASH_RC
    else
        echo "File $BASH_RC does not exist, not setting http_proxy"
    fi
fi

if [ -n "$HTTPS_PROXY" ]; then
    cat <<EOF | sed "s/^ *//" > $HTTPS_PROXY_CONF
    [Service]
    Environment=HTTPS_PROXY=$HTTPS_PROXY
EOF

    RUNTIME_RESTART=1

    if [ -f "$BASH_RC" ]; then
        echo "declare -x https_proxy=$HTTPS_PROXY" >> $BASH_RC
    else
        echo "File $BASH_RC does not exist, not setting https_proxy"
    fi
fi

if [ -n "$NO_PROXY" ]; then
    cat <<EOF | sed "s/^ *//" > $NO_PROXY_CONF
    [Service]
    Environment=NO_PROXY=$NO_PROXY
EOF

    RUNTIME_RESTART=1

    if [ -f "$BASH_RC" ]; then
        echo "declare -x no_proxy=$NO_PROXY" >> $BASH_RC
    else
        echo "File $BASH_RC does not exist, not setting no_proxy"
    fi
fi

if [ "$RUNTIME_RESTART" -eq 1 ]; then
    $ssh_cmd systemctl daemon-reload
    if [ ${CONTAINER_RUNTIME} = "containerd"  ] ; then
        $ssh_cmd systemctl --no-block restart containerd.service
    else
        $ssh_cmd systemctl --no-block restart docker.service
    fi
fi
