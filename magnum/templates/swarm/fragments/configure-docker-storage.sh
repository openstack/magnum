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
pvcreate ${device_path}
vgcreate docker ${device_path}

cat > /etc/sysconfig/docker-storage-setup << EOF
VG=docker
EOF

sed -i '/^DOCKER_STORAGE_OPTIONS=/ s/=.*/=--storage-driver devicemapper --storage-opt dm.fs=xfs --storage-opt dm.thinpooldev=\/dev\/mapper\/docker-docker--pool --storage-opt dm.use_deferred_removal=true/' /etc/sysconfig/docker-storage
