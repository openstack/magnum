#!/bin/sh

# docker is already enabled and possibly running on centos atomic host
# so we need to stop it first and delete the docker0 bridge (which will
# be re-created using the flannel-provided subnet).
echo "stopping docker"
systemctl stop docker
ip link del docker0

# make sure we pick up any modified unit files
systemctl daemon-reload

for service in docker kubelet kube-proxy; do
    echo "activating service $service"
    systemctl enable $service
    systemctl --no-block start $service
done
