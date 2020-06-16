set -x

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

# docker is already enabled and possibly running on centos atomic host
# so we need to stop it first and delete the docker0 bridge (which will
# be re-created using the flannel-provided subnet).
echo "stopping docker"
if [ ${CONTAINER_RUNTIME} != "containerd"  ] ; then
    $ssh_cmd systemctl stop docker
fi

# make sure we pick up any modified unit files
$ssh_cmd systemctl daemon-reload

if [ ${CONTAINER_RUNTIME} = "containerd"  ] ; then
    container_runtime_service="containerd"
else
    container_runtime_service="docker"
fi
for action in enable restart; do
    for service in ${container_runtime_service} kubelet kube-proxy; do
        echo "$action service $service"
        $ssh_cmd systemctl $action $service
    done
done
