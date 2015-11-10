#!/bin/sh

. /etc/sysconfig/heat-params

DOCKER_DEV=/dev/disk/by-id/virtio-${DOCKER_VOLUME:0:20}

attempts=60
while [[ ! -b $DOCKER_DEV && $attempts != 0 ]]; do
    echo "waiting for disk $DOCKER_DEV"
    sleep 0.5
    udevadm trigger
    let attempts--
done

if ! [ -b $DOCKER_DEV ]; then
    echo "ERROR: device $DOCKER_DEV does not exist" >&2
    exit 1
fi

pvcreate $DOCKER_DEV
vgcreate docker $DOCKER_DEV

cat > /etc/sysconfig/docker-storage-setup <<EOF
VG=docker
EOF
