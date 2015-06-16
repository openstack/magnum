.. _dev-quickstart:

=====================
Developer Quick-Start
=====================

This is a quick walkthrough to get you started developing code for Magnum.
This assumes you are already familiar with submitting code reviews to
an OpenStack project.

.. seealso::

   http://docs.openstack.org/infra/manual/developers.html

Setup Dev Environment
=====================

Install prerequisites::

    # Ubuntu/Debian:
    sudo apt-get update
    sudo apt-get install python-dev libssl-dev python-pip libmysqlclient-dev \
                         libxml2-dev libxslt-dev libpq-dev git git-review \
                         libffi-dev gettext python-tox

    # Fedora/RHEL:
    sudo yum install python-devel openssl-devel python-pip mysql-devel \
                     libxml2-devel libxslt-devel postgresql-devel git \
                     git-review libffi-devel gettext

    # openSUSE/SLE 12:
    sudo zypper install git git-review libffi-devel libmysqlclient-devel \
                        libopenssl-devel libxml2-devel libxslt-devel \
                        postgresql-devel python-devel python-flake8 \
                        python-nose python-pip python-setuptools-git \
                        python-testrepository python-tox python-virtualenv \
                        gettext-runtime

    sudo easy_install nose
    sudo pip install virtualenv setuptools-git flake8 tox testrepository

If using RHEL and yum reports "No package python-pip available" and "No
package git-review available", use the EPEL software repository. Instructions
can be found at `<http://fedoraproject.org/wiki/EPEL/FAQ#howtouse>`_.

You may need to explicitly upgrade virtualenv if you've installed the one
from your OS distribution and it is too old (tox will complain). You can
upgrade it individually, if you need to::

    sudo pip install -U virtualenv

Magnum source code should be pulled directly from git::

    # from your home or source directory
    cd ~
    git clone https://git.openstack.org/openstack/magnum
    cd magnum

Set up a local environment for development and testing should be done with tox::

    # create a virtualenv for development
    tox -evenv -- python -V

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

To discover and interact with templates, please refer to
`<http://git.openstack.org/cgit/openstack/magnum/tree/contrib/templates/example/README.rst>`_


Exercising the Services Using DevStack
======================================

DevStack can be configured to enable Magnum support. It is easy to develop Magnum
with devstack environment. Magnum depends on Nova, Glance, Heat and Neutron to
create and schedule virtual machines to simulate bare-metal. For bare-metal fully
support, it is still under active development.

This session has only been tested on Ubuntu 14.04 (Trusty) and Fedora 20/21.
We recommend users to select one of them if it is possible.

Clone DevStack::

    # Create dir to run devstack from, if not done so already
    sudo mkdir -p /opt/stack
    sudo chown $USER /opt/stack

    git clone https://github.com/openstack-dev/devstack.git /opt/stack/devstack

Copy devstack/localrc with minimal settings required to enable Heat
and Neutron, refer to http://docs.openstack.org/developer/devstack/guides/neutron.html
for more detailed neutron configuration.

To install magnum into devstack, add following settings to local.conf. You need to
make customized setting according to your environment requirement, refer devstack
guide for details.::

     cat > /opt/stack/devstack/local.conf << END
     [[local|localrc]]
     enable_plugin magnum https://github.com/openstack/magnum
     DATABASE_PASSWORD=password
     RABBIT_PASSWORD=password
     SERVICE_TOKEN=password
     SERVICE_PASSWORD=password
     ADMIN_PASSWORD=password
     PUBLIC_INTERFACE=eth1
     VOLUME_BACKING_FILE_SIZE=20G
     END

Or, if you already have localrc in /opt/stack/devstack/, then ::

     cat >> /opt/stack/devstack/localrc << END
     enable_plugin magnum https://github.com/openstack/magnum
     PUBLIC_INTERFACE=eth1
     VOLUME_BACKING_FILE_SIZE=20G
     END

Note: Replace eth1 with your public interface for Neutron to use.

Create a local.sh make final networking changes after devstack has spawned. This
will allow Bays spawned by Magnum to access the internet through PUBLIC_INTERFACE.::

    cat > /opt/stack/devstack/local.sh << END_LOCAL_SH
    #!/bin/sh
    sudo iptables -t nat -A POSTROUTING -o br-ex -j MASQUERADE
    END_LOCAL_SH
    chmod 755 /opt/stack/devstack/local.sh

Run DevStack::

    cd /opt/stack/devstack
    ./stack.sh

After the script finishes, two magnum process (magnum-api and magnum-conductor)
will be running on a stack screen. If you make some code changes and want to
test their effects, just restart either magnum-api or magnum-conductor.

At this time, Magnum has only been tested with the Fedora Atomic micro-OS.
Magnum will likely work with other micro-OS platforms, but each one requires
individual support in the heat template.

Prepare your session to be able to use the various openstack clients including
magnum, neutron and glance. Create a new shell, and source the devstack openrc
script::

    source /opt/stack/devstack/openrc admin admin

The fedora-21-atomic-3 image will automatically be added to glance.  You can
add additional images to use manually through glance. To verify the image
created when installing DevStack::

    glance image-list
    +--------------------------------------+---------------------------------+-------------+------------------+-----------+--------+
    | ID                                   | Name                            | Disk Format | Container Format | Size      | Status |
    +--------------------------------------+---------------------------------+-------------+------------------+-----------+--------+
    | 7f5b6a15-f2fd-4552-aec5-952c6f6d4bc7 | cirros-0.3.4-x86_64-uec         | ami         | ami              | 25165824  | active |
    | bd3c0f92-669a-4390-a97d-b3e0a2043362 | cirros-0.3.4-x86_64-uec-kernel  | aki         | aki              | 4979632   | active |
    | 843ce0f7-ae51-4db3-8e74-bcb860d06c55 | cirros-0.3.4-x86_64-uec-ramdisk | ari         | ari              | 3740163   | active |
    | 02c312e3-2d30-43fd-ab2d-1d25622c0eaa | fedora-21-atomic-3              | qcow2       | bare             | 770179072 | active |
    +--------------------------------------+---------------------------------+-------------+------------------+-----------+--------+

You need to define and register a keypair for use when creating baymodel's::

    cd ~
    test -f ~/.ssh/id_rsa.pub || ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa
    nova keypair-add --pub-key ~/.ssh/id_rsa.pub testkey

To get started, list the available commands and resources::

    magnum help

First create a baymodel, which is similar in nature to a flavor.  The
coe (Container Orchestration Engine) needs to be specified for baymodel.
The baymodel informs Magnum in which way to construct a bay.::

    NIC_ID=$(neutron net-show public | awk '/ id /{print $4}')
    magnum baymodel-create --name testbaymodel --image-id fedora-21-atomic-3 \
                           --keypair-id testkey \
                           --external-network-id $NIC_ID \
                           --dns-nameserver 8.8.8.8 --flavor-id m1.small \
                           --docker-volume-size 5 --coe kubernetes

Next create a bay. Use the baymodel UUID as a template for bay creation.
This bay will result in one master kubernetes node and two minion nodes.::

    magnum bay-create --name testbay --baymodel testbaymodel --node-count 2

The existing bays can be listed as follows::

    magnum bay-list

Bays will have an initial status of CREATE_IN_PROGRESS.  Magnum will update
the status to CREATE_COMPLETE when it is done creating the bay.  Do not create
containers, pods, services, or replication controllers before Magnum finishes
creating the bay. They will likely not be created, causing Magnum to become
confused.

    magnum bay-list

    +--------------------------------------+---------+------------+-----------------+
    | uuid                                 | name    | node_count | status          |
    +--------------------------------------+---------+------------+-----------------+
    | 9dccb1e6-02dc-4e2b-b897-10656c5339ce | testbay | 2          | CREATE_COMPLETE |
    +--------------------------------------+---------+------------+-----------------+

Kubernetes provides a number of examples you can use to check that things
are working. You may need to clone kubernetes by::

    wget https://github.com/GoogleCloudPlatform/kubernetes/releases/download/v0.15.0/kubernetes.tar.gz
    tar -xvzf kubernetes.tar.gz

(No require to install it, we just use the example file)
Here's how to set up the replicated redis example. First, create
a pod for the redis-master::

    cd kubernetes/examples/redis/v1beta3
    magnum pod-create --manifest ./redis-master.yaml --bay testbay

Now turn up a service to provide a discoverable endpoint for the redis sentinels
in the cluster::

    magnum service-create --manifest ./redis-sentinel-service.yaml --bay testbay

To make it a replicated redis cluster create replication controllers for the redis
slaves and sentinels::

    sed -i 's/\(replicas: \)1/\1 2/' redis-controller.yaml
    magnum rc-create --manifest ./redis-controller.yaml --bay testbay

    sed -i 's/\(replicas: \)1/\1 2/' redis-sentinel-controller.yaml
    magnum rc-create --manifest ./redis-sentinel-controller.yaml --bay testbay

Full lifecycle and introspection operations for each object are supported.  For
example, magnum bay-create, magnum baymodel-delete, magnum rc-show, magnum service-list.

Now run bay-show command to get the IP of the bay host on which the redis-master is
running on::

    $ magnum bay-show testbay
    +----------------+--------------------------------------+
    | Property       | Value                                |
    +----------------+--------------------------------------+
    | status         | CREATE_COMPLETE                      |
    | uuid           | 7d59afb0-1c24-4cae-93fc-4692f5438d34 |
    | created_at     | 2015-05-11T05:13:42+00:00            |
    | updated_at     | 2015-05-11T05:15:32+00:00            |
    | api_address    | 192.168.19.85                        |
    | baymodel_id    | 0a79f347-54e5-406c-bc20-4cd4ee1fcea0 |
    | node_count     | 1                                    |
    | node_addresses | [u'192.168.19.86']                   |
    | discovery_url  | None                                 |
    | name           | testbay                              |
    +----------------+--------------------------------------+

The output indicates the redis-master is running on the
bay host with IP address 192.168.19.86. To access the redis master::

    ssh minion@192.168.19.86
    REDIS_ID=$(docker ps | grep redis:v1 | grep k8s_master | awk '{print $1}')
    docker exec -i -t $REDIS_ID redis-cli

    127.0.0.1:6379> set replication:test true
    OK
    ^D

    exit

Now log into one of the other container hosts and access a redis slave from there::

    ssh minion@$(nova list | grep 10.0.0.4 | awk '{print $13}')
    REDIS_ID=$(docker ps | grep redis:v1 | grep k8s_redis | tail -n +2 | awk '{print $1}')
    docker exec -i -t $REDIS_ID redis-cli

    127.0.0.1:6379> get replication:test
    "true"
    ^D

    exit

There are four redis instances, one master and three slaves, running across the bay,
replicating data between one another.

Building and using a Swarm bay
==============================
Create a baymodel. It is very similar to the Kubernetes baymodel,
it is only missing some Kubernetes specific arguments and uses 'swarm' as the
coe. ::

    NIC_ID=$(neutron net-show public | awk '/ id /{print $4}')
    magnum baymodel-create --name swarmbaymodel --image-id fedora-21-atomic-3 \
                           --keypair-id testkey \
                           --external-network-id $NIC_ID \
                           --dns-nameserver 8.8.8.8 --flavor-id m1.small \
                           --coe swarm

Finally, create the bay. Use the baymodel 'swarmbaymodel' as a template for
bay creation. This bay will result in one swarm manager node and two extra
agent nodes. ::

    magnum bay-create --name swarmbay --baymodel swarmbaymodel --node-count 2

Now that we have a swarm bay we can start interacting with it. First we need
to get it's uuid. ::

    $ magnum bay-show swarmbay
    +---------------+------------------------------------------+
    | Property      | Value                                    |
    +---------------+------------------------------------------+
    | status        | CREATE_COMPLETE                          |
    | uuid          | eda91c1e-6103-45d4-ab09-3f316310fa8e     |
    | created_at    | 2015-04-20T19:05:27+00:00                |
    | updated_at    | 2015-04-20T19:06:08+00:00                |
    | baymodel_id   | a93ee8bd-fec9-4ea7-ac65-c66c1dba60af     |
    | node_count    | 2                                        |
    | discovery_url |                                          |
    | name          | swarmbay                                 |
    +---------------+------------------------------------------+

Next we will create a container in this bay. This container will ping the
address 8.8.8.8 four times. ::

    $ BAY_UUID=$(magnum bay-list | awk '/ swarmbay /{print $2}')
    $ magnum container-create --name testcontainer --image_id cirros\
                              --bay $BAY_UUID\
                              --command "ping -c 4 8.8.8.8"
    +------------+----------------------------------------+
    | Property   | Value                                  |
    +------------+----------------------------------------+
    | uuid       | 25485358-ae9b-49d1-a1e1-1af0a7c3f911   |
    | links      | ...                                    |
    | bay_uuid   | eda91c1e-6103-45d4-ab09-3f316310fa8e   |
    | updated_at | None                                   |
    | image_id   | cirros                                 |
    | command    | ping -c 4 8.8.8.8                      |
    | created_at | 2015-04-22T20:21:11+00:00              |
    | name       | test-container                         |
    +------------+----------------------------------------+

At this point, the container exists, but it has not been started yet. Let's
start it then check it's output. ::

    $ magnum container-start test-container
    $ magnum container-logs test-container
    PING 8.8.8.8 (8.8.8.8): 56 data bytes
    64 bytes from 8.8.8.8: seq=0 ttl=40 time=25.513 ms
    64 bytes from 8.8.8.8: seq=1 ttl=40 time=25.348 ms
    64 bytes from 8.8.8.8: seq=2 ttl=40 time=25.226 ms
    64 bytes from 8.8.8.8: seq=3 ttl=40 time=25.275 ms

    --- 8.8.8.8 ping statistics ---
    4 packets transmitted, 4 packets received, 0% packet loss
    round-trip min/avg/max = 25.226/25.340/25.513 ms

Now that we're done with the container, we can delete it. ::

    magnum container-delete test-container

Building developer documentation
================================

If you would like to build the documentation locally, eg. to test your
documentation changes before uploading them for review, run these
commands to build the documentation set::

    # activate your development virtualenv
    source .tox/venv/bin/activate

    # build the docs
    tox -edocs

Now use your browser to open the top-level index.html located at::

    magnum/doc/build/html/index.html
