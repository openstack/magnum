Kubernetes elements
===================

This directory contains `[diskimage-builder](https://github.com/openstack/diskimage-builder)`
elements to build an image which contains kubernetes required to use kubecluster-fedora-ironic.yaml.

An example fedora based image and uploaded to glance with the following:

    git clone https://git.openstack.org/openstack/magnum
    git clone https://git.openstack.org/openstack/diskimage-builder.git
    git clone https://git.openstack.org/openstack/tripleo-image-elements.git
    git clone https://git.openstack.org/openstack/heat-templates.git
    git clone https://git.openstack.org/openstack/dib-utils.git
    export PATH="${PWD}/dib-utils/bin:$PATH"
    export ELEMENTS_PATH=tripleo-image-elements/elements:heat-templates/hot/software-config/elements
    export ELEMENTS_PATH=${ELEMENTS_PATH}:magnum/etc/magnum/templates/kubernetes/elements
    export DIB_RELEASE=21
    diskimage-builder/bin/disk-image-create baremetal \
      fedora selinux-permissive \
      os-collect-config \
      os-refresh-config \
      os-apply-config \
      heat-config-script \
      kubernetes \
      -o fedora-21-kubernetes.qcow2

    KERNEL_ID=`glance image-create --name fedora-k8s-kernel --visibility public --disk-format=aki --container-format=aki --file=fedora-21-kubernetes.vmlinuz | grep id | tr -d '| ' | cut --bytes=3-57`
    RAMDISK_ID=`glance image-create --name fedora-k8s-ramdisk --visibility public --disk-format=ari --container-format=ari --file=fedora-21-kubernetes.initrd | grep id |  tr -d '| ' | cut --bytes=3-57`
    BASE_ID=`glance image-create --name fedora-k8s --visibility public --disk-format=qcow2 --container-format=bare --property kernel_id=$KERNEL_ID --property ramdisk_id=$RAMDISK_ID --file=fedora-21-kubernetes.qcow2 | grep -v kernel | grep -v ramdisk | grep id | tr -d '| ' | cut --bytes=3-57`
