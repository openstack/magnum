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
    nova flavor-create  m1.magnum 100 2048 8 1

    source /opt/stack/devstack/openrc demo demo
    nova keypair-add --pub-key ~/.ssh/id_rsa.pub default

Install required packages::

    sudo pip install -U -r test-requirements.txt

Run the test
============

Run this command::

    tox -e functional -- --concurrency=1
