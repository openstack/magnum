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

If using RHEL and yum reports “No package python-pip available” and “No
package git-review available”, use the EPEL software repository. Instructions
can be found at `<http://fedoraproject.org/wiki/EPEL/FAQ#howtouse>`_.

You may need to explicitly upgrade virtualenv if you've installed the one
from your OS distribution and it is too old (tox will complain). You can
upgrade it individually, if you need to::

    sudo pip install -U virtualenv

Magnum source code should be pulled directly from git::

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
on Nova, Heat, and Neutron to create and schedule virtual machines to simulate
bare-metal.  For milestone #2 we intend to introduce support for Ironic
deployment of baremetal nodes.

This session has only been tested on Ubuntu 14.04 (Trusty) and Fedora 21.
We recommend users to select one of them if it is possible.

NB: Magnum depends on a command line tool in kubernetes called kubectl
to execute its operations with Kubernetes.  We are addressing this in milestone
#2 by implementing a native ReST client for Kubernetes.  In the meantime, the
required action is to install kubectl manually.

Install binary distribution of kubectl distributed by Google::

    wget https://github.com/GoogleCloudPlatform/kubernetes/releases/download/v0.7.0/kubernetes.tar.gz
    tar -xzvf kubernetes.tar.gz
    sudo cp -a kubernetes/platforms/linux/amd64/kubectl /usr/bin/kubectl

Clone DevStack::

    cd ~
    git clone https://github.com/openstack-dev/devstack.git devstack

Create devstack/localrc with minimal settings required to enable Heat
and Neutron, refer to http://docs.openstack.org/developer/devstack/guides/neutron.html
for more detailed neutron configuration.::

    cd devstack
    cat >localrc <<END
    # Modify to your environment
    FLOATING_RANGE=192.168.1.224/27
    PUBLIC_NETWORK_GATEWAY=192.168.1.225
    PUBLIC_INTERFACE=em1

    # Credentials
    ADMIN_PASSWORD=password
    DATABASE_PASSWORD=password
    RABBIT_PASSWORD=password
    SERVICE_PASSWORD=password
    SERVICE_TOKEN=password

    enable_service rabbit

    # Enable Neutron which is required by Magnum and disable nova-network.
    disable_service n-net
    enable_service q-svc
    enable_service q-agt
    enable_service q-dhcp
    enable_service q-l3
    enable_service q-meta
    enable_service neutron

    FIXED_RANGE=10.0.0.0/24

    Q_USE_SECGROUP=True
    ENABLE_TENANT_VLANS=True
    TENANT_VLAN_RANGE=

    PHYSICAL_NETWORK=public
    OVS_PHYSICAL_BRIDGE=br-ex

    # Log all output to files
    LOGFILE=$HOME/devstack.log
    SCREEN_LOGDIR=$HOME/logs

    END
    ./stack.sh

At this time, Magnum has only been tested with the Fedora Atomic micro-OS.
Magnum will likely work with other micro-OS platforms, but each one requires
individual support in the heat template.

The next step is to store the Fedora Atomic micro-OS in glance.  The steps for
updating Fedora Atomic images are a bit detailed.  Fortunately one of the core
developers has made Atomic images avaliable via the web:

Create a new shell, and source the devstack openrc script::

    source ~/devstack/openrc admin admin

    cd ~
    wget https://fedorapeople.org/groups/heat/kolla/fedora-21-atomic.qcow2
    glance image-create --name fedora21-atomic \
                        --is-public True \
                        --disk-format qcow2 \
                        --container-format bare < fedora-21-atomic.qcow2
    test -f ~/.ssh/id_rsa.pub || ssh-keygen
    nova keypair-add --pub-key ~/.ssh/id_rsa.pub testkey

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
    sudo mkdir -p /etc/magnum/templates
    sudo cp -r etc/magnum/templates/heat-kubernetes \
          /etc/magnum/templates/

Next configure Magnum::
    # If using milestone #1, please use the documentation shipped with the milestone
    # as the current master instructions are slightly incompatible.

    # copy sample config and modify it as necessary
    sudo cp etc/magnum/magnum.conf.sample /etc/magnum/magnum.conf

    # enable debugging output
    sudo sed -i "s/#debug\s*=.*/debug=true/" /etc/magnum/magnum.conf

    # enable more verbose output
    sudo sed -i "s/#verbose\s*=.*/verbose=true/" /etc/magnum/magnum.conf

    # set RabbitMQ userid
    sudo sed -i "s/#rabbit_userid\s*=.*/rabbit_userid=stackrabbit/" /etc/magnum/magnum.conf

    # set RabbitMQ password
    sudo sed -i "s/#rabbit_password\s*=.*/rabbit_password=password/" /etc/magnum/magnum.conf

    # set SQLAlchemy connection string to connect to MySQL
    sudo sed -i "s/#connection\s*=.*/connection=mysql:\/\/root:password@localhost\/magnum/" /etc/magnum/magnum.conf

    # set Keystone account username
    sudo sed -i "s/#admin_user\s*=.*/admin_user=admin/" /etc/magnum/magnum.conf

    # set Keystone account password
    sudo sed -i "s/#admin_password\s*=.*/admin_password=password/" /etc/magnum/magnum.conf

    # set admin Identity API endpoint
    sudo sed -i "s/#identity_uri\s*=.*/identity_uri=http:\/\/127.0.0.1:35357/" /etc/magnum/magnum.conf

    # set public Identity API endpoint
    sudo sed -i "s/#auth_uri\s*=.*/auth_uri=http:\/\/127.0.0.1:5000\/v2.0/" /etc/magnum/magnum.conf

Next, clone and install the client::

    cd ~
    git clone https://github.com/stackforge/python-magnumclient
    cd python-magnumclient
    sudo pip install -e .

Next, configure the database for use with Magnum::

    magnum-db-manage upgrade

Finally, configure the keystone endpoint::

    keystone service-create --name=magnum \
                            --type=container \
                            --description="Magnum Container Service"
    keystone endpoint-create --service=magnum \
                             --publicurl=http://127.0.0.1:9511/v1 \
                             --internalurl=http://127.0.0.1:9511/v1 \
                             --adminurl=http://127.0.0.1:9511/v1


Next start the API service::

    magnum-api

Next start the conductor service in a new window::

    magnum-conductor

To get started, list the available commands and resources::

    magnum help

First create a baymodel, which is similar in nature to a flavor.  It informs
Magnum in which way to construct a bay.::

    NIC_ID=$(neutron net-show public | awk '/ id /{print $4}')
    magnum baymodel-create --name testbaymodel --image-id fedora21-atomic \
                           --keypair-id testkey \
                           --external-network-id $NIC_ID \
                           --dns-nameserver 8.8.8.8 --flavor-id m1.small

Next create a bay. Use the baymodel UUID as a template for bay creation.
This bay will result in one master kubernetes node and three minion nodes.::

    BAYMODEL_UUID=$(magnum baymodel-list | awk '/ testbaymodel /{print $2}')
    magnum bay-create --name testbay --baymodel-id $BAYMODEL_UUID --node-count 2

The existing bays can be listed as follows::

    magnum bay-list

If you make some code changes and want to test their effects,
just restart either magnum-api or magnum-conductor.  the -e option to
pip install will link to the location from where the source code
was installed.

Magnum uses heat to orchestrate.  Heat reports CREATE_COMPLETE when it is
done orchestrating.  Do not create containers, pods, services, or replication
controllers before Heat finishes orchestrating the bay.  They will likely
not be created, causing Magnum to become confused.

See blueprint:
https://blueprints.launchpad.net/magnum/+spec/magnum-bay-status


    heat stack-list

    +--------------------------------------+------------+-----------------+----------------------+
    | id                                   | stack_name | stack_status    | creation_time        |
    +--------------------------------------+------------+-----------------+----------------------+
    | 8eb10314-e6b8-400f-8d4c-c0f5762eecea | testbay    | CREATE_COMPLETE | 2015-01-17T17:06:27Z |
    +--------------------------------------+------------+-----------------+----------------------+


To start a kubernetes pod, use Kolla as an example repo::

    cd ~
    git clone http://github.com/stackforge/kolla

    cd kolla/k8s/pod
    BAY_UUID=$(magnum bay-list | awk '/ testbay /{print $2}')
    magnum pod-create --manifest ./mariadb-pod.yaml --bay-id $BAY_UUID

To start a kubernetes service, use Kolla as an example repo::

    cd ../service
    magnum service-create --manifest ./mariadb-service.yaml --bay-id $BAY_UUID

To start a kubernetes replication controller, use Kolla as an example repo::

    cd ../replication
    magnum rc-create --manifest ./nova-compute-replicationyaml --bay-id $BAY_UUID

Full lifecycle and introspection operations for each object are supported.  For
exmaple, magnum bay-create magnum baymodel-delete, magnum rc-show, magnum service-list.

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
