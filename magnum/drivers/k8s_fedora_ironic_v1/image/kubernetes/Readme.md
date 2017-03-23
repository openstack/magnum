Kubernetes elements
===================

This directory contains `[diskimage-builder](https://github.com/openstack/diskimage-builder)`
elements to build an image which contains kubernetes required to use kubecluster-fedora-ironic.yaml.

An example fedora based image and uploaded to glance with the following:

    # Install diskimage-builder in virtual environment
    virtualenv .
    . bin/activate
    pip install diskimage-builder
    git clone https://git.openstack.org/openstack/magnum
    git clone https://git.openstack.org/openstack/dib-utils.git
    export PATH="${PWD}/dib-utils/bin:$PATH"
    export ELEMENTS_PATH=$(python -c 'import os, diskimage_builder, pkg_resources;print(os.path.abspath(pkg_resources.resource_filename(diskimage_builder.__name__, "elements")))')
    export ELEMENTS_PATH=${ELEMENTS_PATH}:magnum/magnum/drivers/k8s_fedora_ironic_v1/image
    export DIB_RELEASE=25
    disk-image-create baremetal \
      fedora selinux-permissive \
      kubernetes \
      -o fedora-25-kubernetes.qcow2

    KERNEL_ID=`glance image-create --name fedora-k8s-kernel \
                                   --visibility public \
                                   --disk-format=aki \
                                   --container-format=aki \
                                   --file=fedora-25-kubernetes.vmlinuz \
                                   | grep id | tr -d '| ' | cut --bytes=3-57`
    RAMDISK_ID=`glance image-create --name fedora-k8s-ramdisk \
                                    --visibility public \
                                    --disk-format=ari \
                                    --container-format=ari \
                                    --file=fedora-25-kubernetes.initrd \
                                    | grep id |  tr -d '| ' | cut --bytes=3-57`
    BASE_ID=`glance image-create --name fedora-k8s \
                                    --os-distro fedora \
                                    --visibility public \
                                    --disk-format=qcow2 \
                                    --container-format=bare \
                                    --property kernel_id=$KERNEL_ID \
                                    --property ramdisk_id=$RAMDISK_ID \
                                    --file=fedora-25-kubernetes.qcow2 \
                                    | grep -v kernel | grep -v ramdisk \
                                    | grep id | tr -d '| ' | cut --bytes=3-57`
