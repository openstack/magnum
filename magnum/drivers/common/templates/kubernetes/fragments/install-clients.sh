step="install-clients"
printf "Starting to run ${step}\n"

set -e
set +x
. /etc/sysconfig/heat-params
set -x

hyperkube_image="${CONTAINER_INFRA_PREFIX:-${HYPERKUBE_PREFIX}}hyperkube:${KUBE_TAG}"
ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"
mkdir -p /srv/magnum/bin/
i=0
until ${ssh_cmd} "/usr/bin/podman run \
    --entrypoint /bin/bash \
    --name install-kubectl \
    --net host \
    --privileged \
    --rm \
    --user root \
    --volume /srv/magnum/bin:/host/srv/magnum/bin \
    ${hyperkube_image} \
    -c 'cp /usr/local/bin/kubectl /host/srv/magnum/bin/kubectl'"
do
    i=$((i + 1))
    if [ ${i} -gt 60 ] ; then
        echo "ERROR Unable to install kubectl. Abort."
        exit 1
    fi
    echo "WARNING Attempt ${i}: Trying to install kubectl. Sleeping 5s"
    sleep 5s
done
echo "INFO Installed kubectl."

echo "export PATH=/srv/magnum/bin:\$PATH" >> /etc/bashrc
export PATH=/srv/magnum/bin:$PATH

printf "Finished running ${step}\n"
