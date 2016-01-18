===========================
Run functional test locally
===========================

This is a guide for developers who want to run functional tests in their local
machine.

Prerequisite
============

You need to follow the developer quickstart guide to deploy Magnum in a
devstack environment

`<http://docs.openstack.org/developer/magnum/dev/dev-quickstart.html>`_

Preparation
===========

Navigate to Magnum directory::

    cd /opt/stack/magnum

Prepare a config file for functional test::

    cp /opt/stack/tempest/etc/tempest.conf /opt/stack/magnum/etc/tempest.conf
    cp functional_creds.conf.sample functional_creds.conf

    # update the IP address
    HOST=$(cat /etc/magnum/magnum.conf | awk '/^host = /{print $3}')
    sed -i "s/127.0.0.1/$HOST/" functional_creds.conf

    # update admin password
    source /opt/stack/devstack/openrc admin admin
    iniset functional_creds.conf admin pass $OS_PASSWORD

    # update demo password
    source /opt/stack/devstack/openrc demo demo
    iniset functional_creds.conf auth password $OS_PASSWORD

Create the necessary keypair and flavor::

    source /opt/stack/devstack/openrc admin admin
    nova keypair-add --pub-key ~/.ssh/id_rsa.pub default
    nova flavor-create  m1.magnum 100 1024 8 1

    source /opt/stack/devstack/openrc demo demo
    nova keypair-add --pub-key ~/.ssh/id_rsa.pub default

You may need to explicitly upgrade required packages if you've installed them
before and their versions become too old::

    UPPER_CONSTRAINTS=/opt/stack/requirements/upper-constraints.txt
    sudo pip install -c $UPPER_CONSTRAINTS -U -r test-requirements.txt

Run the test
============

We'v splited functional testing per COE.

Use follow command lines to check what functional testing is supported::

    cd /opt/stack/magnum
    cat tox.ini | grep functional- | awk -F: '{print $2}' | sed s/]//

To do some specify functional testing, for example, test kubernetes functional
cases::

    tox -e functional-k8s -- --concurrency=1

Test specified case of kubernetes functional cases::

    tox -e functional-k8s -- --concurrency=1 <test path>


The following is an example for test path::

    magnum.tests.functional.k8s.v1.test_k8s_python_client.TestBayModelResource.test_baymodel_create_and_delete

We also have api tests being added.  To run those, go to
tempest directory (tempest is installed with devstack by default), install
magnum, and execute tempest tox::

    cd /opt/stack/tempest
    tox -eall-plugin magnum.tests.functional.api.v1 -- --concurrency=1
