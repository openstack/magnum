#!/bin/sh

# make sure we pick up any modified unit files
systemctl daemon-reload

echo starting services
for service in etcd kube-apiserver kube-scheduler kube-controller-manager flanneld kube-proxy; do
	echo "activating service $service"
	systemctl enable $service
	systemctl --no-block start $service
done


