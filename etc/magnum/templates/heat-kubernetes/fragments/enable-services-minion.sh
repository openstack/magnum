#!/bin/sh

# docker is already enabled and possibly running on centos atomic host
# so we need to stop it first and delete the docker0 bridge (which will
# be re-created using the flannel-provided subnet).
echo "stopping docker"
systemctl stop docker
ip link del docker0

for service in wait-for-flanneld flanneld docker.socket docker kubelet kube-proxy; do
	echo "activating service $service"
	systemctl enable $service
	systemctl --no-block start $service
done

