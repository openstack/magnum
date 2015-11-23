#!/bin/sh

. /etc/sysconfig/heat-params

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
pvcreate ${device_path}
vgcreate docker ${device_path}

cat > /etc/sysconfig/docker-storage-setup << EOF
VG=docker
EOF
