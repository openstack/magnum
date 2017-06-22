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
* curl

For Debian/Ubuntu systems, use::

    apt-get install python-dev build-essential python-pip kpartx python-lzma \
                    qemu-utils yum yum-utils python-yaml git curl

For CentOS and Fedora < 22, use::

    yum install python-dev build-essential python-pip kpartx python-lzma qemu-utils yum yum-utils python-yaml curl

For Fedora >= 22, use::

    dnf install python-devel @development-tools python-pip kpartx python-backports-lzma @virtualization yum yum-utils python-yaml curl

How to generate Fedora Atomic image
-----------------------------------
To generate an atomic image for Fedora 25 these commands can be
executed::

    # Install diskimage-builder in virtual environment
    virtualenv .
    . bin/activate
    pip install diskimage-builder
    git clone https://git.openstack.org/openstack/magnum
    git clone https://git.openstack.org/openstack/dib-utils.git

    export PATH="${PWD}/dib-utils/bin:$PATH"

    export ELEMENTS_PATH=$(python -c 'import os, diskimage_builder, pkg_resources;print(os.path.abspath(pkg_resources.resource_filename(diskimage_builder.__name__, "elements")))')
    export ELEMENTS_PATH="${ELEMENTS_PATH}:${PWD}/magnum/magnum/drivers/common/image"

    export DIB_RELEASE=25     # this can be switched to the desired version
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
  :Default: ``https://kojipkgs.fedoraproject.org/atomic/${DIB_RELEASE}/``


FEDORA_ATOMIC_TREE_REF
  :Required: Yes
  :Description: Reference of the tree to install.
  :Default: ``$(curl ${FEDORA_ATOMIC_TREE_URL}/refs/heads/fedora-atomic/${DIB_RELEASE}/x86_64/docker-host)``

You can use the defaults or export your url and reference, like following::

    export FEDORA_ATOMIC_TREE_URL="https://kojipkgs.fedoraproject.org/atomic/25/"
    export FEDORA_ATOMIC_TREE_REF="$(curl https://kojipkgs.fedoraproject.org/atomic/25/refs/heads/fedora-atomic/25/x86_64/docker-host)"
