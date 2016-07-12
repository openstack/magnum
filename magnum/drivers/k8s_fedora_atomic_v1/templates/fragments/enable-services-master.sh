#!/bin/sh

# make sure we pick up any modified unit files
systemctl daemon-reload

echo "starting services"
for service in etcd docker kube-apiserver kubelet; do
    echo "activating service $service"
    systemctl enable $service
    systemctl --no-block start $service
done
