.. _dev-manual-install:

Manually Adding Magnum to DevStack
==================================

If you are getting started with Magnum it is recommended you follow the
:ref:`dev-quickstart` to get up and running with Magnum. This guide covers
a more in-depth process to setup Magnum with devstack.

Magnum depends on Nova, Glance, Heat, and Neutron to create and schedule
virtual machines to simulate bare-metal. For milestone #2 we intend to
introduce support for Ironic deployment of baremetal nodes.

This session has only been tested on Ubuntu 14.04 (Trusty) and Fedora 20/21.
We recommend users to select one of them if it is possible.

NB: Magnum depends on a command line tool in Kubernetes called kubectl
to execute its operations with Kubernetes. We are addressing this in milestone
#2 by implementing a native ReST client for Kubernetes.  In the meantime, the
required action is to install kubectl manually.

Install binary distribution of kubectl distributed by Google::

    wget https://github.com/GoogleCloudPlatform/kubernetes/releases/download/v0.15.0/kubernetes.tar.gz
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

    # Enable Heat services
    enable_service h-eng
    enable_service h-api
    enable_service h-api-cfn
    enable_service h-api-cw

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
    cat > local.sh << END_LOCAL_SH
    #!/bin/sh
    sudo iptables -t nat -A POSTROUTING -o br-ex -j MASQUERADE
    END_LOCAL_SH
    chmod 755 local.sh

    ./stack.sh

At this time, Magnum has only been tested with the Fedora Atomic micro-OS.
Magnum will likely work with other micro-OS platforms, but each one requires
individual support in the heat template.

The next step is to store the Fedora Atomic micro-OS in glance.  The steps for
updating Fedora Atomic images are a bit detailed.  Fortunately one of the core
developers has made Atomic images available via the web:

If using the m-1 tag or tarball, please use the documentation shipped with the
milestone as the current master instructions are slightly incompatible.

Create a new shell, and source the devstack openrc script::

    source ~/devstack/openrc admin admin

    cd ~
    wget https://fedorapeople.org/groups/magnum/fedora-21-atomic-3.qcow2
    glance image-create --name fedora-21-atomic-3 \
                        --is-public True \
                        --disk-format qcow2 \
                        --property os-distro='fedora-atomic'\
                        --container-format bare < fedora-21-atomic-3.qcow2
    test -f ~/.ssh/id_rsa.pub || ssh-keygen
    nova keypair-add --pub-key ~/.ssh/id_rsa.pub testkey

Next, create a database in MySQL for Magnum::

    mysql -h 127.0.0.1 -u root -ppassword mysql <<EOF
    CREATE DATABASE IF NOT EXISTS magnum DEFAULT CHARACTER SET utf8;
    GRANT ALL PRIVILEGES ON magnum.* TO
        'root'@'%' IDENTIFIED BY 'password'
    EOF

Next, clone and install Magnum::

    cd ~
    git clone https://github.com/openstack/magnum
    cd magnum
    sudo pip install -e .

Next configure Magnum::

    # create the magnum conf directory
    sudo mkdir -p /etc/magnum

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
    git clone https://github.com/openstack/python-magnumclient
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
                             --adminurl=http://127.0.0.1:9511/v1 \
                             --region RegionOne


Next start the API service::

    magnum-api

Finally start the conductor service in a new window::

    magnum-conductor

Magnum should now be up and running. Further steps on utilizing Magnum and
deploying containers can be found in guide :ref:`dev-quickstart`.
