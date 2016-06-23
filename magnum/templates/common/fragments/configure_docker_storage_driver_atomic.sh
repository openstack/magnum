# This file contains docker storage drivers configuration for fedora
# atomic hosts. Currently, devicemapper and overlay are supported.

# Remove any existing docker-storage configuration. In case of an
# existing configuration, docker-storage-setup will fail.
clear_docker_storage_congiguration () {
    if [ -f /etc/sysconfig/docker-storage ]; then
        sed -i "/^DOCKER_STORAGE_OPTIONS=/ s/=.*/=/" /etc/sysconfig/docker-storage
    fi
}

# Configure docker storage with xfs as backing filesystem.
configure_overlay () {
    clear_docker_storage_congiguration

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

# Configure docker storage with devicemapper using direct LVM
configure_devicemapper () {
    clear_docker_storage_congiguration

    pvcreate ${device_path}
    vgcreate docker ${device_path}

    echo "VG=docker" > /etc/sysconfig/docker-storage-setup
}
