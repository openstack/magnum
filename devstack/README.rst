====================
DevStack Integration
====================

This directory contains the files necessary to integrate magnum with devstack.

Refer the quickstart guide at
http://docs.openstack.org/developer/magnum/dev/quickstart.html
for more information on using devstack and magnum.

Running devstack with magnum for the first time may take a long time as it
needs to download the Fedora Atomic qcow2 image (see
http://www.projectatomic.io/download/).

To install magnum into devstack, add the following settings to enable the
magnum plugin::

     cat > /opt/stack/devstack/local.conf << END
     [[local|localrc]]
     enable_plugin heat https://github.com/openstack/heat master
     enable_plugin magnum https://github.com/openstack/magnum master
     END

Additionally, you might need additional Neutron configurations for
your environment.
Please refer to the devstack documentation [#devstack_neutron]_ for details.

Then run devstack normally::

    cd /opt/stack/devstack
    ./stack.sh

.. [#devstack_neutron] https://docs.openstack.org/developer/devstack/guides/neutron.html
