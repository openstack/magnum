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

    apt-get install python-dev build-essential python-pip kpartx python-lzma qemu-utils yum yum-utils python-yaml

For CentOS and Fedora < 22, use::

    yum install python-dev build-essential python-pip kpartx python-lzma qemu-utils yum yum-utils python-yaml

For Fedora >= 22, use::

    dnf install python-dev build-essential python-pip kpartx python-lzma qemu-utils yum yum-utils python-yaml

diskimage-builder can be installed using pip::

    pip install diskimage-builder

How to generate Fedora Atomic image
-----------------------------------
To generate an atomic image for Fedora 23 these commands can be
executed::

    export ELEMENTS_PATH=/path/to/diskimage-builder/elements:/path/to/magnum/elements
    export DIB_RELEASE=23     # this can be switched to the desired version
    export DIB_IMAGE_SIZE=2   # we need to give a bit more space to loopback device
    disk-image-create fedora-atomic

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
  :Default: `https://dl.fedoraproject.org/pub/fedora/linux/atomic/23/ <https://dl.fedoraproject.org/pub/fedora/linux/atomic/23/>`_


FEDORA_ATOMIC_TREE_REF
  :Required: Yes
  :Description: Reference of the tree to install.
  :Default: 954bdbeebebfa87b625d9d7bd78c81400bdd6756fcc3205987970af4b64eb678
