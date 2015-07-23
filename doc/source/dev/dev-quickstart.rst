.. _dev-quickstart:

=====================
Developer Quick-Start
=====================

This is a quick walkthrough to get you started developing code for magnum.
This assumes you are already familiar with submitting code reviews to an
OpenStack project.

.. seealso::

   http://docs.openstack.org/infra/manual/developers.html

Setup Dev Environment
=====================

Install OS-specific prerequisites::

    # Ubuntu/Debian:
    sudo apt-get update
    sudo apt-get install python-dev libssl-dev python-pip libmysqlclient-dev \
                         libxml2-dev libxslt-dev libpq-dev git git-review \
                         libffi-dev gettext

    # Fedora/RHEL:
    sudo yum install python-devel openssl-devel python-pip mysql-devel \
                     libxml2-devel libxslt-devel postgresql-devel git \
                     git-review libffi-devel gettext

    # openSUSE/SLE 12:
    sudo zypper install git git-review libffi-devel libmysqlclient-devel \
                        libopenssl-devel libxml2-devel libxslt-devel \
                        postgresql-devel python-devel \
                        python-pip gettext-runtime

Install common prerequisites::

    sudo pip install virtualenv flake8 tox testrepository

Note: If using RHEL and yum reports "No package python-pip available" and "No
package git-review available", use the EPEL software repository. Instructions
can be found at the http://fedoraproject.org/wiki/EPEL/FAQ#howtouse page.

You may need to explicitly upgrade virtualenv if you've installed the one
from your OS distribution and it is too old (tox will complain). You can
upgrade it individually, if you need to::

    sudo pip install -U virtualenv

Magnum source code should be pulled directly from git::

    # from your home or source directory
    cd ~
    git clone https://git.openstack.org/openstack/magnum
    cd magnum

Set up a local environment for development and testing with tox::

    # create a virtualenv for development
    tox -evenv -- python -V

Activate the virtual environment whenever you want to work in it.
All further commands in this section should be run with the venv active::

    source .tox/venv/bin/activate

All unit tests should be run using tox. To run magnum's entire test suite::

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

Exercising the Services Using Devstack
======================================

Devstack can be configured to enable magnum support. It is easy to develop
magnum with the devstack environment. Magnum depends on nova, glance, heat and
neutron to create and schedule virtual machines to simulate bare-metal (full
bare-metal support is under active development).

Note: Running devstack within a virtual machine with magnum enabled is not
recommended at this time.

This session has only been tested on Ubuntu 14.04 (Trusty) and Fedora 20/21.
We recommend users to select one of them if it is possible.

For in-depth guidance on adding magnum manually to a devstack instance, please
refer to the :ref:`dev-manual-install` guide.

Clone devstack::

    # Create a root directory for devstack if needed
    sudo mkdir -p /opt/stack
    sudo chown $USER /opt/stack

    git clone https://git.openstack.org/openstack-dev/devstack /opt/stack/devstack

We will run devstack with minimal local.conf settings required to enable
magnum, heat, and neutron (neutron is enabled by default in devstack since
Kilo, and heat is enabled by the magnum plugin)::

    cat > /opt/stack/devstack/local.conf << END
    [[local|localrc]]
    DATABASE_PASSWORD=password
    RABBIT_PASSWORD=password
    SERVICE_TOKEN=password
    SERVICE_PASSWORD=password
    ADMIN_PASSWORD=password
    # magnum requires the following to be set correctly
    PUBLIC_INTERFACE=eth1
    enable_plugin magnum https://github.com/openstack/magnum
    VOLUME_BACKING_FILE_SIZE=20G
    END

Note: Update PUBLIC_INTERFACE as appropriate for your system.

More devstack configuration information can be found at
http://docs.openstack.org/developer/devstack/configuration.html

More neutron configuration information can be found at
http://docs.openstack.org/developer/devstack/guides/neutron.html

Create a local.sh to automatically make necessary networking changes during
the devstack deployment process. This will allow bays spawned by magnum to
access the internet through PUBLIC_INTERFACE::

    cat > /opt/stack/devstack/local.sh << 'END_LOCAL_SH'
    #!/bin/sh
    ROUTE_TO_INTERNET=$(ip route get 8.8.8.8)
    OBOUND_DEV=$(echo ${ROUTE_TO_INTERNET#*dev} | awk '{print $1}')
    sudo iptables -t nat -A POSTROUTING -o $OBOUND_DEV -j MASQUERADE
    END_LOCAL_SH
    chmod 755 /opt/stack/devstack/local.sh

Run devstack::

    cd /opt/stack/devstack
    ./stack.sh

Note: This will take a little extra time when the Fedora Atomic micro-OS
image is downloaded for the first time.

At this point, two magnum process (magnum-api and magnum-conductor) will be
running on devstack screens. If you make some code changes and want to
test their effects, just stop and restart magnum-api and/or magnum-conductor.

Prepare your session to be able to use the various openstack clients including
magnum, neutron, and glance. Create a new shell, and source the devstack openrc
script::

    source /opt/stack/devstack/openrc admin admin

Magnum has been tested with the Fedora Atomic micro-OS and CoreOS. Magnum will
likely work with other micro-OS platforms, but each requires individual
support in the heat template.

The Fedora Atomic micro-OS image will automatically be added to glance.  You
can add additional images manually through glance. To verify the image created
when installing devstack use::

    glance image-list

    +--------------------------------------+---------------------------------+-------------+------------------+-----------+--------+
    | ID                                   | Name                            | Disk Format | Container Format | Size      | Status |
    +--------------------------------------+---------------------------------+-------------+------------------+-----------+--------+
    | 7f5b6a15-f2fd-4552-aec5-952c6f6d4bc7 | cirros-0.3.4-x86_64-uec         | ami         | ami              | 25165824  | active |
    | bd3c0f92-669a-4390-a97d-b3e0a2043362 | cirros-0.3.4-x86_64-uec-kernel  | aki         | aki              | 4979632   | active |
    | 843ce0f7-ae51-4db3-8e74-bcb860d06c55 | cirros-0.3.4-x86_64-uec-ramdisk | ari         | ari              | 3740163   | active |
    | 02c312e3-2d30-43fd-ab2d-1d25622c0eaa | fedora-21-atomic-3              | qcow2       | bare             | 770179072 | active |
    +--------------------------------------+---------------------------------+-------------+------------------+-----------+--------+

To list the available commands and resources for magnum, use::

    magnum help

Create a keypair for use with the baymodel::

    test -f ~/.ssh/id_rsa.pub || ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa
    nova keypair-add --pub-key ~/.ssh/id_rsa.pub testkey

Create a baymodel. This is similar in nature to a flavor and describes
to magnum how to construct the bay. The coe (Container Orchestration Engine)
and keypair need to be specified for the baymodel::

    NIC_ID=$(neutron net-show public | awk '/ id /{print $4}')
    echo ${NIC_ID}

    magnum baymodel-create --name k8sbaymodel \
                           --image-id fedora-21-atomic-3 \
                           --keypair-id testkey \
                           --external-network-id ${NIC_ID} \
                           --dns-nameserver 8.8.8.8 \
                           --flavor-id m1.small \
                           --docker-volume-size 5 \
                           --coe kubernetes

Create a bay. Use the baymodel name as a template for bay creation.
This bay will result in one master kubernetes node and one minion node::

    magnum bay-create --name k8sbay --baymodel k8sbaymodel --node-count 1

Bays will have an initial status of CREATE_IN_PROGRESS.  Magnum will update
the status to CREATE_COMPLETE when it is done creating the bay.  Do not create
containers, pods, services, or replication controllers before magnum finishes
creating the bay. They will likely not be created, and may cause magnum to
become confused.

The existing bays can be listed as follows::

    magnum bay-list

    +--------------------------------------+---------+------------+-----------------+
    | uuid                                 | name    | node_count | status          |
    +--------------------------------------+---------+------------+-----------------+
    | 9dccb1e6-02dc-4e2b-b897-10656c5339ce | k8sbay  | 1          | CREATE_COMPLETE |
    +--------------------------------------+---------+------------+-----------------+

More detailed information for a given bay is obtained via::

    magnum bay-show k8sbay

After a bay is created, you can dynamically add/remove node(s) to/from the bay
by updating the node_count attribute. For example, to add one more node::

    magnum bay-update k8sbay replace node_count=2

Bays in the process of updating will have a status of UPDATE_IN_PROGRESS.
Magnum will update the status to UPDATE_COMPLETE when it is done updating
the bay.

Note: Reducing node_count will remove all the existing containers on the
nodes that are deleted.

Heat can be used to see detailed information on the status of a stack or
specific bay::

    heat stack-list

Monitoring bay status in detail (e.g., creating, updating)::

    BAY_HEAT_NAME=$(heat stack-list | awk "/\sk8sbay-/{print \$4}")
    echo ${BAY_HEAT_NAME}
    heat resource-list ${BAY_HEAT_NAME}

A bay can be deleted as follows::

    magnum bay-delete k8sbay

Note: If you choose to reduce the node_count, magnum will first try to remove
empty nodes with no containers running on them. If you reduce node_count by
more than the number of empty nodes, magnum must remove nodes that have running
containers on them. This action will delete those containers. We strongly
recommend using a replication controller before reducing the node_count so
any removed containers can be automatically recovered on your remaining nodes.

Using Kubernetes
================

Kubernetes provides a number of examples you can use to check that things are
working. You may need to clone kubernetes using::

    wget https://github.com/GoogleCloudPlatform/kubernetes/releases/download/v0.15.0/kubernetes.tar.gz
    tar -xvzf kubernetes.tar.gz

Note: We do not need to install Kubernetes, we just need the example file
from the tarball.

Here's how to set up the replicated redis example. First, create
a pod for the redis-master::

    cd kubernetes/examples/redis/v1beta3
    magnum pod-create --manifest ./redis-master.yaml --bay k8sbay

Now create a service to provide a discoverable endpoint for the redis
sentinels in the cluster::

    magnum service-create --manifest ./redis-sentinel-service.yaml --bay k8sbay

To make it a replicated redis cluster create replication controllers for the
redis slaves and sentinels::

    sed -i 's/\(replicas: \)1/\1 2/' redis-controller.yaml
    magnum rc-create --manifest ./redis-controller.yaml --bay k8sbay

    sed -i 's/\(replicas: \)1/\1 2/' redis-sentinel-controller.yaml
    magnum rc-create --manifest ./redis-sentinel-controller.yaml --bay k8sbay

Full lifecycle and introspection operations for each object are supported.
For example, magnum bay-create, magnum baymodel-delete, magnum rc-show,
magnum service-list.

Now run bay-show command to get the IP of the bay host on which the
redis-master is running::

    magnum bay-show k8sbay

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
    | name           | k8sbay                               |
    +----------------+--------------------------------------+

The output indicates the redis-master is running on the bay host with IP
address 192.168.19.86. To access the redis master::

    ssh minion@192.168.19.86
    REDIS_ID=$(sudo docker ps | grep redis:v1 | grep k8s_master | awk '{print $1}')
    sudo docker exec -i -t $REDIS_ID redis-cli

    127.0.0.1:6379> set replication:test true
    OK
    ^D

    exit

Log into one of the other container hosts and access a redis slave from it::

    ssh minion@$(nova list | grep 10.0.0.4 | awk '{print $13}')
    REDIS_ID=$(sudo docker ps | grep redis:v1 | grep k8s_redis | tail -n +2 | awk '{print $1}')
    sudo docker exec -i -t $REDIS_ID redis-cli

    127.0.0.1:6379> get replication:test
    "true"
    ^D

    exit

Now there are four redis instances (one master and three slaves) running
across the bay, replicating data between one another.

Building and Using a Swarm Bay
==============================

Create a baymodel. It is very similar to the Kubernetes baymodel, except for
the absence of some Kubernetes-specific arguments and the use of 'swarm'
as the coe::

    NIC_ID=$(neutron net-show public | awk '/ id /{print $4}')
    magnum baymodel-create --name swarmbaymodel \
                           --image-id fedora-21-atomic-3 \
                           --keypair-id testkey \
                           --external-network-id ${NIC_ID} \
                           --dns-nameserver 8.8.8.8 \
                           --flavor-id m1.small \
                           --coe swarm

Finally, create the bay. Use the baymodel 'swarmbaymodel' as a template for
bay creation. This bay will result in one swarm manager node and two extra
agent nodes::

    magnum bay-create --name swarmbay --baymodel swarmbaymodel --node-count 2

Now that we have a swarm bay we can start interacting with it::

    magnum bay-show swarmbay

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
address 8.8.8.8 four times::

    magnum container-create --name testcontainer \
                            --image cirros \
                            --bay swarmbay \
                            --command "ping -c 4 8.8.8.8"

    +------------+----------------------------------------+
    | Property   | Value                                  |
    +------------+----------------------------------------+
    | uuid       | 25485358-ae9b-49d1-a1e1-1af0a7c3f911   |
    | links      | ...                                    |
    | bay_uuid   | eda91c1e-6103-45d4-ab09-3f316310fa8e   |
    | updated_at | None                                   |
    | image      | cirros                                 |
    | command    | ping -c 4 8.8.8.8                      |
    | created_at | 2015-04-22T20:21:11+00:00              |
    | name       | test-container                         |
    +------------+----------------------------------------+

At this point the container exists but it has not been started yet. To start
it and check its output run the following::

    magnum container-start test-container
    magnum container-logs test-container

    PING 8.8.8.8 (8.8.8.8): 56 data bytes
    64 bytes from 8.8.8.8: seq=0 ttl=40 time=25.513 ms
    64 bytes from 8.8.8.8: seq=1 ttl=40 time=25.348 ms
    64 bytes from 8.8.8.8: seq=2 ttl=40 time=25.226 ms
    64 bytes from 8.8.8.8: seq=3 ttl=40 time=25.275 ms

    --- 8.8.8.8 ping statistics ---
    4 packets transmitted, 4 packets received, 0% packet loss
    round-trip min/avg/max = 25.226/25.340/25.513 ms

Now that we're done with the container we can delete it::

    magnum container-delete test-container

Building and Using a Mesos Bay
==============================

Provisioning a mesos bay requires a Ubuntu-based image with some packages
pre-installed. To build and upload such image, please refer to
`<http://git.openstack.org/cgit/openstack/magnum/tree/magnum/templates/heat-mesos/elements/README.md>`_

Then, create a baymodel by using 'mesos' as the coe, with the rest of arguments
similar to the Kubernetes baymodel::

    NIC_ID=$(neutron net-show public | awk '/ id /{print $4}')
    magnum baymodel-create --name mesosbaymodel --image-id ubuntu-mesos \
                           --keypair-id testkey \
                           --external-network-id $NIC_ID \
                           --dns-nameserver 8.8.8.8 --flavor-id m1.small \
                           --coe mesos

Finally, create the bay. Use the baymodel 'mesosbaymodel' as a template for
bay creation. This bay will result in one mesos master node and two mesos
slave nodes::

    magnum bay-create --name mesosbay --baymodel mesosbaymodel --node-count 2

Now that we have a mesos bay we can start interacting with it. First we need
to make sure the bay's status is 'CREATE_COMPLETE'::

    $ magnum bay-show mesosbay
    +----------------+--------------------------------------+
    | Property       | Value                                |
    +----------------+--------------------------------------+
    | status         | CREATE_COMPLETE                      |
    | uuid           | ff727f0d-72ca-4e2b-9fef-5ec853d74fdf |
    | created_at     | 2015-06-09T20:21:43+00:00            |
    | updated_at     | 2015-06-09T20:28:18+00:00            |
    | api_address    | 172.24.4.115                         |
    | baymodel_id    | 92dbda62-32d4-4435-88fc-8f42d514b347 |
    | node_count     | 2                                    |
    | node_addresses | [u'172.24.4.116', u'172.24.4.117']   |
    | status_reason  | Stack CREATE completed successfully  |
    | discovery_url  | None                                 |
    | name           | mesosbay                             |
    +----------------+--------------------------------------+

Next we will create a container in this bay by using the REST API of Marathon.
This container will ping the address 8.8.8.8::

    $ cat > mesos.json << END
    {
      "container": {
        "type": "DOCKER",
        "docker": {
          "image": "cirros"
        }
      },
      "id": "ubuntu",
      "instances": 1,
      "cpus": 0.5,
      "mem": 512,
      "uris": [],
      "cmd": "ping 8.8.8.8"
    }
    END
    $ MASTER_IP=$(magnum bay-show mesosbay | awk '/ api_address /{print $4}')
    $ curl -X POST -H "Content-Type: application/json" \
        http://${MASTER_IP}:8080/v2/apps -d@mesos.json

Using the Marathon web console (at http://<master>:8080/), you will see the
application you created.

Building Developer Documentation
================================

To build the documentation locally (e.g., to test documentation changes
before uploading them for review) chdir to the magnum root folder and
run tox::

    tox -edocs

Note: The first time you run this will take some extra time as it
creates a virtual environment to run in.

When complete, the documentation can be accesed from::

    doc/build/html/index.html
