#!/bin/sh

. /etc/sysconfig/heat-params

# make sure we pick up any modified unit files
systemctl daemon-reload

# if the certificate manager api is enabled, wait for the ca key to be handled
# by the heat container agent (required for the controller-manager)
while [ ! -f /etc/kubernetes/certs/ca.key ] && \
    [ "$(echo $CERT_MANAGER_API | tr '[:upper:]' '[:lower:]')" == "true" ]; do
    echo "waiting for CA to be made available for certificate manager api"
    sleep 2
done

# docker is already enabled and possibly running on centos atomic host
# so we need to stop it first and delete the docker0 bridge (which will
# be re-created using the flannel-provided subnet).
echo "stopping docker"
systemctl stop docker
ip link del docker0

echo "starting services"
for service in etcd docker kube-apiserver kube-controller-manager kube-scheduler kubelet kube-proxy; do
    echo "activating service $service"
    systemctl enable $service
    systemctl --no-block start $service
done