Mesos elements
==============

This directory contains `[diskimage-builder](https://github.com/openstack/diskimage-builder)`
elements to build an image which contains mesos and its frameworks required to
use the heat template mesoscluster.yaml.

Currently, only Ubuntu 14.04 is supported. An example Ubuntu based image can be
built and uploaded to glance as follows:

    sudo apt-get update
    sudo apt-get install git qemu-utils python-pip
    sudo pip install pyyaml

    git clone https://git.openstack.org/openstack/magnum
    git clone https://git.openstack.org/openstack/diskimage-builder.git
    git clone https://git.openstack.org/openstack/dib-utils.git
    export PATH="${PWD}/dib-utils/bin:$PATH"
    export ELEMENTS_PATH=magnum/magnum/templates/heat-mesos/elements
    export DIB_RELEASE=trusty

    diskimage-builder/bin/disk-image-create ubuntu vm docker mesos \
        -o ubuntu-mesos.qcow2

    glance image-create --name ubuntu-mesos --visibility public \
        --disk-format=qcow2 --container-format=bare \
        --property os_distro=ubuntu --file=ubuntu-mesos.qcow2
