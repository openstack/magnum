.. _dev-quickstart:

=====================
Developer Quick-Start
=====================

This is a quick walkthrough to get you started developing code for Magnum.
This assumes you are already familiar with submitting code reviews to
an OpenStack project.

.. seealso::

    https://wiki.openstack.org/wiki/GerritWorkflow

Install prerequisites::

    # Ubuntu/Debian:
    sudo apt-get install python-dev libssl-dev python-pip libmysqlclient-dev libxml2-dev libxslt-dev libpq-dev git git-review libffi-dev gettext python-tox

    # Fedora/RHEL:
    sudo yum install python-devel openssl-devel python-pip mysql-devel libxml2-devel libxslt-devel postgresql-devel git git-review libffi-devel gettext ipmitool

    # openSUSE/SLE 12:
    sudo zypper install git git-review libffi-devel libmysqlclient-devel libopenssl-devel libxml2-devel libxslt-devel postgresql-devel python-devel python-flake8 python-nose python-pip python-setuptools-git python-testrepository python-tox python-virtualenv gettext-runtime

    sudo easy_install nose
    sudo pip install virtualenv setuptools-git flake8 tox testrepository

If using RHEL and yum reports “No package python-pip available” and “No
package git-review available”, use the EPEL software repository. Instructions
can be found at `<http://fedoraproject.org/wiki/EPEL/FAQ#howtouse>`_.

You may need to explicitly upgrade virtualenv if you've installed the one
from your OS distribution and it is too old (tox will complain). You can
upgrade it individually, if you need to::

    sudo pip install -U virtualenv

Ironic source code should be pulled directly from git::

    # from your home or source directory
    cd ~
    git clone https://git.openstack.org/stackforge/magnum
    cd magnum

Set up a local environment for development and testing should be done with tox::

    # create a virtualenv for development
    tox -evenv -- echo 'done'

Activate the virtual environment whenever you want to work in it.
All further commands in this section should be run with the venv active::

    source .tox/venv/bin/activate

All unit tests should be run using tox. To run Magnum's entire test suite::

    # run all tests (unit and pep8)
    tox

To run a specific test, use a positional argument for the unit tests::

    # run a specific test for Python 2.7
    tox -epy27 -- test_conductor

You may pass options to the test programs using positional arguments::

    # run all the Python 2.7 unit tests (in parallel!)
    tox -epy27 -- --parallel

To run only the pep8/flake8 syntax and style checks::

    tox -epep8

When you're done, deactivate the virtualenv::

    deactivate

======================================
Exercising the Services Using DevStack
======================================

DevStack does not yet have Magnum support.  It is, however, necessary to
develop Magnum from a devstack environment at the present time.  Magnum depends
on Ironic to create and schedule bare metal machines.  These instructions show
how to use Ironic in a virtualized environment so only one machine is needed
to develop.

Clone DevStack::

    cd ~
    git clone https://github.com/openstack-dev/devstack.git devstack

Create devstack/localrc with minimal settings required to enable Ironic.
Magnum depends on Ironic for bare metal provisioning of an micro-OS containing
Kubernetes and Docker.  For Ironic, we recommend using the pxe+ssh driver::

    cd devstack
    cat >localrc <<END
    # Credentials
    ADMIN_PASSWORD=password
    DATABASE_PASSWORD=password
    RABBIT_PASSWORD=password
    SERVICE_PASSWORD=password
    SERVICE_TOKEN=password

    # Enable Ironic API and Ironic Conductor
    enable_service ironic
    enable_service ir-api
    enable_service ir-cond

    # Enable Neutron which is required by Ironic and disable nova-network.
    disable_service n-net
    enable_service q-svc
    enable_service q-agt
    enable_service q-dhcp
    enable_service q-l3
    enable_service q-meta
    enable_service neutron

    # Create 5 virtual machines to pose as Ironic's baremetal nodes.
    IRONIC_VM_COUNT=5
    IRONIC_VM_SSH_PORT=22
    IRONIC_BAREMETAL_BASIC_OPS=True

    # The parameters below represent the minimum possible values to create
    # functional nodes.
    IRONIC_VM_SPECS_RAM=1024
    IRONIC_VM_SPECS_DISK=10

    # Size of the ephemeral partition in GB. Use 0 for no ephemeral partition.
    IRONIC_VM_EPHEMERAL_DISK=0

    VIRT_DRIVER=ironic

    # By default, DevStack creates a 10.0.0.0/24 network for instances.
    # If this overlaps with the hosts network, you may adjust with the
    # following.
    NETWORK_GATEWAY=10.1.0.1
    FIXED_RANGE=10.1.0.0/24
    FIXED_NETWORK_SIZE=256

    # Log all output to files
    LOGFILE=$HOME/devstack.log
    SCREEN_LOGDIR=$HOME/logs
    IRONIC_VM_LOG_DIR=$HOME/ironic-bm-logs

    END

At this time, Magnum has only been tested with the Fedora Atomic micro-OS.
Magnum will likely work with other micro-OS platforms, but each one requires
individual support.

The next step is to store the Fedora Atomic micro-OS in glance.  The steps for
making the Atomic images for Ironic are a bit detailed, but fortunately one
of the core Magnum developers has written some simple scripts to automate
the process::

    cd ~
    git clone http://github.com/sdake/fedora-atomic-to-liveos-pxe
    cd fedora-atomic-to-liveos-pxe
    wget http://dl.fedoraproject.org/pub/alt/stage/21_RC5/Cloud/Images/x86_64/Fedora-Cloud-Atomic-20141203-21.x86_64.qcow2
    ./convert.sh
    ./register-with-glance.sh

Next, create a database in MySQL for Magnum::

    mysql -h 127.0.0.1 -u root -ppassword mysql <<EOF
    CREATE DATABASE IF NOT EXISTS magnum DEFAULT CHARACTER SET utf8;
    GRANT ALL PRIVILEGES ON magnum.* TO
        'root'@'%' IDENTIFIED BY 'password'
    EOF

Next, clone and install magnum::

    cd ~
    git clone https://github.com/stackforge/magnum
    cd magnum
    sudo pip install -e .

Next, clone and install the client::

    cd ~
    git clone https://github.com/stackforge/python-magnumclient
    cd python-magnumclient
    sudo pip install -e .

Next configure the database connection for Magnum::

    sed -i "s/#connection=.*/connection=mysql:\/\/root:password@localhost\/magnum/" etc/magnum/magnum.conf.sample

Next, configure the database for use with Magnum::

    magnum-db-manage upgrade

Finally, configure the keystone endpoint::

    keystone service-create --name=container \
                            --type=container \
                            --description="Magnum Container Service"
    keystone endpoint-create --service=container \
                             --publicurl=http://127.0.0.1:9511/v1 \
                             --internalurl=http://127.0.0.1:9511/v1 \
                             --adminurl=http://127.0.0.1:9511/v1


Next start the API service::

    magnum-api

Next start the ackend service in a new window::

    magnum-conductor

Create a new shell, and source the devstack openrc script::

    . ~/repos/devstack/openrc admin admin

To get started, list the available commands and resources::

    magnum help

A bay can be created with 3 nodes.  One node will be configured as a master
Kubernetes node, while the remaining two nodes will be configured as minions::

    magnum bay-create --name=cats --type=baremetal --image_id=<IMAGE_ID_FROM_GLANCE_REGISTRATION_SCRIPT> --node_count=3

The existing bays can be listed as follows::

    magnum bay-list

If you make some code changes and want to test their effects,
just restart either magnum-api or magnum-conductor.  the -e option to
pip install will link to the location from where the source code
was installed.

================================
Building developer documentation
================================

If you would like to build the documentation locally, eg. to test your
documentation changes before uploading them for review, run these
commands to build the documentation set::

    # activate your development virtualenv
    source .tox/venv/bin/activate

    # build the docs
    tox -egendocs

Now use your browser to open the top-level index.html located at::

    magnum/doc/build/html/index.html
