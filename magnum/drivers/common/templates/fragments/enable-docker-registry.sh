#!/bin/sh

. /etc/sysconfig/heat-params

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

if [ "$(echo $REGISTRY_ENABLED | tr '[:upper:]' '[:lower:]')" = "true" ]; then
    echo "starting docker registry ..."
    $ssh_cmd systemctl daemon-reload
    $ssh_cmd systemctl enable registry
    $ssh_cmd systemctl --no-block start registry
fi
