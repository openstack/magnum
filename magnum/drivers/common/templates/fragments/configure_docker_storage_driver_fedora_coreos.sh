ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

runtime=${CONTAINER_RUNTIME}
if [ ${CONTAINER_RUNTIME} = "containerd"  ] ; then
    storage_dir="/var/lib/containerd"
else
    storage_dir="/var/lib/docker"
    runtime="docker"
fi

clear_docker_storage () {
    # stop docker
    $ssh_cmd systemctl stop ${runtime}
    # clear storage graph
    $ssh_cmd rm -rf ${storage_dir}
    $ssh_cmd mkdir -p ${storage_dir}
}

# Configure generic docker storage driver.
configure_storage_driver_generic() {
    clear_docker_storage

    if [ -n "$DOCKER_VOLUME_SIZE" ] && [ "$DOCKER_VOLUME_SIZE" -gt 0 ]; then
        $ssh_cmd mkfs.xfs -f ${device_path}
        echo "${device_path} ${storage_dir} xfs defaults 0 0" >> /etc/fstab
        $ssh_cmd mount -a
        $ssh_cmd restorecon -R ${storage_dir}
    fi
    if [ ${CONTAINER_RUNTIME} = "host-docker"  ] ; then
        sed -i -E 's/^OPTIONS=("|'"'"')/OPTIONS=\1--storage-driver='$1' /' /etc/sysconfig/docker
        # NOTE(flwang): The default nofile limit it too low, update it to
        # match the default value in containerd
        sed -i -E 's/--default-ulimit nofile=1024:1024/--default-ulimit nofile=1048576:1048576/' /etc/sysconfig/docker
    fi
}

configure_devicemapper() {
    configure_storage_driver_generic
}

