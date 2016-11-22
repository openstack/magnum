=============
fedora-atomic
=============

Generates a Fedora Atomic image based on a public deployed tree. This element has been tested under Debian, Ubuntu, CentOS and Fedora operating systems.

Pre-requisites to run diskimage-builder
---------------------------------------
For diskimage-builder to work, following packages need to be
present:

* python-dev
* build-essential
* python-pip
* kpartx
* python-lzma
* qemu-utils
* yum
* yum-utils
* python-yaml

For Debian/Ubuntu systems, use::

    apt-get install python-dev build-essential python-pip kpartx python-lzma \
                    qemu-utils yum yum-utils python-yaml git curl

For CentOS and Fedora < 22, use::

    yum install python-dev build-essential python-pip kpartx python-lzma qemu-utils yum yum-utils python-yaml

For Fedora >= 22, use::

    dnf install python-devel @development-tools python-pip kpartx python-backports-lzma @virtualization yum yum-utils python-yaml

How to generate Fedora Atomic image
-----------------------------------
To generate an atomic image for Fedora 24 these commands can be
executed::

    git clone https://git.openstack.org/openstack/magnum
    git clone https://git.openstack.org/openstack/diskimage-builder.git
    git clone https://git.openstack.org/openstack/dib-utils.git

    export PATH="${PWD}/dib-utils/bin:$PATH"
    export PATH="${PWD}/diskimage-builder/bin:$PATH"

    export ELEMENTS_PATH="${PWD}/diskimage-builder/elements"
    export ELEMENTS_PATH="${ELEMENTS_PATH}:${PWD}/magnum/magnum/drivers/common/image"

    export DIB_RELEASE=24     # this can be switched to the desired version
    export DIB_IMAGE_SIZE=2.5 # we need to give a bit more space to loopback device

    disk-image-create fedora-atomic -o fedora-atomic

This element can consume already published trees, but you can use it
to consume your own generated trees. Documentation about creating own trees
can be found at `http://developers.redhat.com/blog/2015/01/08/creating-custom-atomic-trees-images-and-installers-part-1/ <http://developers.redhat.com/blog/2015/01/08/creating-custom-atomic-trees-images-and-installers-part-1/>`_

Environment Variables
---------------------

To properly reference the tree, the following env vars can be set:

FEDORA_ATOMIC_TREE_URL
  :Required: Yes
  :Description: Url for the public fedora-atomic tree to use. It can
                reference to own published trees.
  :Default: `https://kojipkgs.fedoraproject.org/atomic/24/ <https://kojipkgs.fedoraproject.org/atomic/24/>`_


FEDORA_ATOMIC_TREE_REF
  :Required: Yes
  :Description: Reference of the tree to install.
  :Default: d9c8b8a31238e857f010c6fdc282f5f611d3c8af3e78caa891f7edb85822771b

You can use the defaults or export your url and reference, like following::

    export FEDORA_ATOMIC_TREE_URL="https://kojipkgs.fedoraproject.org/atomic/24/"
    export FEDORA_ATOMIC_TREE_REF="$(curl https://kojipkgs.fedoraproject.org/atomic/24/refs/heads/fedora-atomic/f24/x86_64/docker-host)"
