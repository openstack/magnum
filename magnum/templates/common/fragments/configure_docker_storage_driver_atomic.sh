configure_overlay () {
    rm -rf /var/lib/docker/*

    mkfs.xfs ${device_path}
    echo "${device_path} /var/lib/docker xfs defaults 0 0" >> /etc/fstab
    mount -a

    echo "STORAGE_DRIVER=overlay" > /etc/sysconfig/docker-storage-setup

    # SELinux must be enabled and in enforcing mode on the physical
    # machine, but must be disabled in the container when performing
    # container separation
    sed -i "/^OPTIONS=/ s/--selinux-enabled/--selinux-enabled=false/" /etc/sysconfig/docker
}

configure_devicemapper () {
    pvcreate ${device_path}
    vgcreate docker ${device_path}

    echo "VG=docker" > /etc/sysconfig/docker-storage-setup

    STORAGE_CONF="--storage-driver devicemapper \
                  --storage-opt dm.fs=xfs \
                  --storage-opt dm.thinpooldev=/dev/mapper/docker-docker--pool \
                  --storage-opt dm.use_deferred_removal=true"

    sed -i "/^DOCKER_STORAGE_OPTIONS=/ s#=.*#=${STORAGE_CONF}#" /etc/sysconfig/docker-storage
}
