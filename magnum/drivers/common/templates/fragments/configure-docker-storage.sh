#!/bin/sh

. /etc/sysconfig/heat-params

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

if [ -n "$DOCKER_VOLUME_SIZE" ] && [ "$DOCKER_VOLUME_SIZE" -gt 0 ]; then
    if [ "$ENABLE_CINDER" == "False" ]; then
        # FIXME(yuanying): Use ephemeral disk for docker storage
        # Currently Ironic doesn't support cinder volumes,
        # so we must use preserved ephemeral disk instead of a cinder volume.
        device_path=$($ssh_cmd readlink -f /dev/disk/by-label/ephemeral0)
    else
        attempts=60
        while [ ${attempts} -gt 0 ]; do
            device_name=$($ssh_cmd ls /dev/disk/by-id | grep ${DOCKER_VOLUME:0:20}$)
            if [ -n "${device_name}" ]; then
                break
            fi
            echo "waiting for disk device"
            sleep 0.5
            $ssh_cmd udevadm trigger
            let attempts--
        done

        if [ -z "${device_name}" ]; then
            echo "ERROR: disk device does not exist" >&2
            exit 1
        fi

        device_path=/dev/disk/by-id/${device_name}
    fi
fi

runtime=${CONTAINER_RUNTIME}

# Initialize configuration flag
need_configure=1

# Check if containerd is already running
if [ "$($ssh_cmd systemctl is-active containerd)" = "active" ]; then
    echo "Containerd is already running, skipping storage driver configuration"
    need_configure=0
fi

if [ "$need_configure" -eq 1 ]; then
    if [ ${CONTAINER_RUNTIME} = "containerd"  ] ; then
        storage_dir="/var/lib/containerd"
    else
        storage_dir="/var/lib/docker"
        runtime="docker"
    fi

    # stop docker
    $ssh_cmd systemctl stop ${runtime}
    # clear storage graph
    $ssh_cmd rm -rf ${storage_dir}
    $ssh_cmd mkdir -p ${storage_dir}
 
    if [ -n "$DOCKER_VOLUME_SIZE" ] && [ "$DOCKER_VOLUME_SIZE" -gt 0 ]; then
        $ssh_cmd mkfs.xfs -f ${device_path}
        echo "${device_path} ${storage_dir} xfs defaults 0 0" >> /etc/fstab
        $ssh_cmd mount -a
        $ssh_cmd restorecon -R ${storage_dir}
    fi
    if [ ${CONTAINER_RUNTIME} = "host-docker"  ] ; then
        sed -i -E 's/^OPTIONS=("|'"'"')/OPTIONS=\1--storage-driver='$DOCKER_STORAGE_DRIVER' /' /etc/sysconfig/docker
        # NOTE(flwang): The default nofile limit it too low, update it to
        # match the default value in containerd
        sed -i -E 's/--default-ulimit nofile=1024:1024/--default-ulimit nofile=1048576:1048576/' /etc/sysconfig/docker
    fi
fi
