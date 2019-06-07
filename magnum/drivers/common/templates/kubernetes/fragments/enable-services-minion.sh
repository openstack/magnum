#!/bin/sh

set -x

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

# docker is already enabled and possibly running on centos atomic host
# so we need to stop it first and delete the docker0 bridge (which will
# be re-created using the flannel-provided subnet).
echo "stopping docker"
$ssh_cmd systemctl stop docker
$ssh_cmd ip link del docker0

# make sure we pick up any modified unit files
$ssh_cmd systemctl daemon-reload

for service in docker kubelet kube-proxy; do
    echo "activating service $service"
    $ssh_cmd systemctl enable $service
    $ssh_cmd systemctl --no-block start $service
done
