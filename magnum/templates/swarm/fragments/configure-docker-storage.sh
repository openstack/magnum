#!/bin/sh

. /etc/sysconfig/heat-params

attempts=60
while [ ${attempts} -gt 0 ]; do
    id=$(echo $DOCKER_VOLUME | awk  '{ string=substr($0, 1, 20); print string; }')
    device_name=$(ls /dev/disk/by-id | grep $id)
    if [ -n "${device_name}" ]; then
        break
    fi
    echo "waiting for disk device"
    sleep 0.5
    udevadm trigger
    attempts=$((attempts-1))
done

if [ -z "${device_name}" ]; then
    echo "ERROR: disk device does not exist" >&2
    exit 1
fi

device_path=/dev/disk/by-id/${device_name}

$configure_docker_storage_driver

if [ "$DOCKER_STORAGE_DRIVER" = "overlay" ]; then
    if [ $(echo -e "$(uname -r)\n3.18" | sort -V | head -1) \
         = $(uname -r) ]; then
        ERROR_MESSAGE="OverlayFS requires at least Linux kernel 3.18. Bay node kernel version: $(uname -r)"
        echo "ERROR: ${ERROR_MESSAGE}" >&2
        sh -c "${WAIT_CURL} --data-binary '{\"status\": \"FAILURE\", \"reason\": \"${ERROR_MESSAGE}\"}'"
    else
        configure_overlay
    fi
else
    configure_devicemapper
fi
