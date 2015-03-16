====================
Devstack Integration
====================

This directory contains the files necessary to integrate Magnum with devstack.

Refer the quickstart guide for more information on using devstack and magnum.

Running devestack with magnum for the first time may take a long time as it
needs to download an atomic fedora 21 qcow image. If you already have this image
you can copy it to /opt/stack/devstack/files/fedora-21-atomic.qcow2 to save you
this time.

To install magnum into devstack: ::

    git clone https://git.openstack.org/stackforge/magnum /opt/stack/magnum
    git clone https://git.openstack.org/openstack-dev/devstack /opt/stack/devstack

    # copy example localrc, modify as necessary
    cp /opt/stack/magnum/contrib/devstack/localrc.example /opt/stack/devstack/localrc

    cd /opt/stack/magnum
    ./contrib/devstack/prepare_devstack.sh

Run devstack as normal: ::

    cd /opt/stack/devstack
    ./stack.sh
