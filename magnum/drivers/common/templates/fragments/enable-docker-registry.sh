#!/bin/sh

. /etc/sysconfig/heat-params

if [ "$REGISTRY_ENABLED" = "False" ]; then
    exit 0
fi

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

echo "starting docker registry ..."
$ssh_cmd systemctl daemon-reload
$ssh_cmd systemctl enable registry
$ssh_cmd systemctl --no-block start registry
