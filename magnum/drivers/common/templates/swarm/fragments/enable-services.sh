#!/bin/sh

set -x

systemctl stop docker

echo "starting services"
systemctl daemon-reload
for service in $NODE_SERVICES; do
    echo "activating service $service"
    systemctl enable $service
    systemctl --no-block start $service
done

setenforce 1
