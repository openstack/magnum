#!/bin/sh

. /etc/sysconfig/heat-params

if [ "$REGISTRY_ENABLED" = "False" ]; then
    exit 0
fi

echo "starting docker registry ..."
systemctl daemon-reload
systemctl enable registry
systemctl --no-block start registry
