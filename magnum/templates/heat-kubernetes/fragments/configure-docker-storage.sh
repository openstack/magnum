#!/bin/sh

. /etc/sysconfig/heat-params

DOCKER_DEV=/dev/disk/by-id/virtio-${DOCKER_VOLUME:0:20}

if ! [ -b $DOCKER_DEV ]; then
	echo "ERROR: device $DOCKER_DEV does not exist" >&2
	exit 1
fi

pvcreate $DOCKER_DEV
vgcreate docker $DOCKER_DEV
lvcreate --wipesignatures y -n data docker -l 95%VG
lvcreate --wipesignatures y -n metadata docker -l 5%VG

cat > /etc/sysconfig/docker-storage <<EOF
DOCKER_STORAGE_OPTIONS="--storage-opt dm.blkdiscard=false --storage-opt dm.metadatadev=/dev/docker/metadata --storage-opt dm.datadev=/dev/docker/data --storage-opt dm.fs=xfs"
EOF

