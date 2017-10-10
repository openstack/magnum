#!/bin/sh

. /etc/sysconfig/heat-params

if [ -n "$DOCKER_VOLUME_SIZE" ] && [ "$DOCKER_VOLUME_SIZE" -gt 0 ]; then
    if [ "$ENABLE_CINDER" == "False" ]; then
        # FIXME(yuanying): Use ephemeral disk for docker storage
        # Currently Ironic doesn't support cinder volumes,
        # so we must use preserved ephemeral disk instead of a cinder volume.
        device_path=$(readlink -f /dev/disk/by-label/ephemeral0)
    else
        attempts=60
        while [ ${attempts} -gt 0 ]; do
            device_name=$(ls /dev/disk/by-id | grep ${DOCKER_VOLUME:0:20}$)
            if [ -n "${device_name}" ]; then
                break
            fi
            echo "waiting for disk device"
            sleep 0.5
            udevadm trigger
            let attempts--
        done

        if [ -z "${device_name}" ]; then
            echo "ERROR: disk device does not exist" >&2
            exit 1
        fi

        device_path=/dev/disk/by-id/${device_name}
    fi
fi

$configure_docker_storage_driver

if [ "$DOCKER_STORAGE_DRIVER" = "devicemapper" ]; then
    configure_devicemapper
else
    configure_storage_driver_generic $DOCKER_STORAGE_DRIVER
fi
