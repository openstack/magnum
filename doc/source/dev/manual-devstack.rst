.. _manual-install:

==================================
Manually Adding Magnum to DevStack
==================================

If you are getting started with magnum it is recommended you follow the
:ref:`quickstart` to get up and running with magnum. This guide covers
a more in-depth process to setup magnum with devstack.

Magnum depends on nova, glance, heat, barbican, and neutron to create and
schedule virtual machines to simulate bare-metal. Full bare-metal support
is still under active development.

This session has only been tested on Ubuntu 14.04 (Trusty) and Fedora 20/21.
We recommend users to select one of them if it is possible.

Clone devstack::

    cd ~
    git clone https://git.openstack.org/openstack-dev/devstack

Configure devstack with the minimal settings required to enable heat
and neutron::

    cd devstack
    cat > local.conf << END
    [[local|localrc]]
    # Modify to your environment
    FIXED_RANGE=10.0.0.0/24
    FLOATING_RANGE=192.168.1.224/27
    PUBLIC_NETWORK_GATEWAY=192.168.1.225
    PUBLIC_INTERFACE=em1
    PHYSICAL_NETWORK=public
    OVS_PHYSICAL_BRIDGE=br-ex
    ENABLE_TENANT_VLANS=True
    TENANT_VLAN_RANGE=1000:1999

    # Credentials
    ADMIN_PASSWORD=password
    DATABASE_PASSWORD=password
    RABBIT_PASSWORD=password
    SERVICE_PASSWORD=password
    SERVICE_TOKEN=password

    enable_service rabbit

    # Ensure we are using neutron networking rather than nova networking
    disable_service n-net
    enable_service q-svc
    enable_service q-agt
    enable_service q-dhcp
    enable_service q-l3
    enable_service q-meta
    # Note: Default template uses LBaaS.
    enable_service q-lbaas
    enable_service neutron

    # Enable heat services
    enable_service h-eng
    enable_service h-api
    enable_service h-api-cfn
    enable_service h-api-cw

    # Enable barbican services
    enable_plugin barbican https://git.openstack.org/openstack/barbican
    enable_plugin neutron-lbaas https://git.openstack.org/openstack/neutron-lbaas

    VOLUME_BACKING_FILE_SIZE=20G
    END

**NOTE:** Update PUBLIC_INTERFACE and other parameters as appropriate for
your system.

More devstack configuration information can be found at
http://docs.openstack.org/developer/devstack/configuration.html

More neutron configuration information can be found at
http://docs.openstack.org/developer/devstack/guides/neutron.html

Optionally, you can enable ceilometer in devstack. If ceilometer is enabled,
magnum will periodically send metrics to ceilometer. If you need this feature,
add the following line to your `local.conf` file::

    enable_plugin ceilometer git://git.openstack.org/openstack/ceilometer

Create a local.sh to automatically make necessary networking changes during
the devstack deployment process. This will allow bays spawned by magnum to
access the internet through PUBLIC_INTERFACE::

    cat > local.sh << 'END_LOCAL_SH'
    #!/bin/sh
    ROUTE_TO_INTERNET=$(ip route get 8.8.8.8)
    OBOUND_DEV=$(echo ${ROUTE_TO_INTERNET#*dev} | awk '{print $1}')
    sudo iptables -t nat -A POSTROUTING -o $OBOUND_DEV -j MASQUERADE
    END_LOCAL_SH
    chmod 755 local.sh

Run devstack::

    ./stack.sh

**NOTE:** If using the m-1 tag or tarball, please use the documentation
shipped with the milestone as the current master instructions are slightly
incompatible.

Prepare your session to be able to use the various openstack clients including
magnum, neutron, and glance. Create a new shell, and source the devstack openrc
script::

    source ~/devstack/openrc admin admin

Magnum has been tested with the Fedora Atomic micro-OS and CoreOS. Magnum will
likely work with other micro-OS platforms, but each requires individual
support in the heat template.

Store the Fedora Atomic micro-OS in glance. Download the qcow2 Atomic image
from https://fedorapeople.org/groups/magnum/fedora-atomic-latest.qcow2 and
then upload it to glance::

    glance image-create --name fedora-atomic-latest \
                        --visibility public \
                        --disk-format qcow2 \
                        --os-distro fedora-atomic \
                        --container-format bare < fedora-atomic-latest.qcow2

Create a domain and domain admin for trust::

    TRUSTEE_DOMAIN_ID=$(
        openstack domain create magnum \
            --description "Owns users and projects created by magnum" \
            -f value -c id
    )
    TRUSTEE_DOMAIN_ADMIN_ID=$(
        openstack user create trustee_domain_admin \
            --password "password" \
            --domain=${TRUSTEE_DOMAIN_ID} \
            --or-show \
            -f value -c id
    )
    openstack --os-identity-api-version 3 role add \
              --user $TRUSTEE_DOMAIN_ADMIN_ID --domain $TRUSTEE_DOMAIN_ID \
              admin

Create a keypair for use with the baymodel::

    test -f ~/.ssh/id_rsa.pub || ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa
    nova keypair-add --pub-key ~/.ssh/id_rsa.pub testkey

Create a database in MySQL for magnum::

    mysql -h 127.0.0.1 -u root -ppassword mysql <<EOF
    CREATE DATABASE IF NOT EXISTS magnum DEFAULT CHARACTER SET utf8;
    GRANT ALL PRIVILEGES ON magnum.* TO
        'root'@'%' IDENTIFIED BY 'password'
    EOF

Clone and install magnum::

    cd ~
    git clone https://git.openstack.org/openstack/magnum
    cd magnum
    sudo pip install -e .

Configure magnum::

    # create the magnum conf directory
    sudo mkdir -p /etc/magnum

    # generate sample config file and modify it as necessary
    tox -egenconfig
    sudo cp etc/magnum/magnum.conf.sample /etc/magnum/magnum.conf

    # copy policy.json
    sudo cp etc/magnum/policy.json /etc/magnum/policy.json

    # enable debugging output
    sudo sed -i "s/#debug\s*=.*/debug=true/" /etc/magnum/magnum.conf

    # set RabbitMQ userid
    sudo sed -i "s/#rabbit_userid\s*=.*/rabbit_userid=stackrabbit/" \
             /etc/magnum/magnum.conf

    # set RabbitMQ password
    sudo sed -i "s/#rabbit_password\s*=.*/rabbit_password=password/" \
             /etc/magnum/magnum.conf

    # set SQLAlchemy connection string to connect to MySQL
    sudo sed -i "s/#connection\s*=.*/connection=mysql:\/\/root:password@localhost\/magnum/" \
             /etc/magnum/magnum.conf

    # set Keystone account username
    sudo sed -i "s/#admin_user\s*=.*/admin_user=admin/" \
             /etc/magnum/magnum.conf

    # set Keystone account password
    sudo sed -i "s/#admin_password\s*=.*/admin_password=password/" \
             /etc/magnum/magnum.conf

    # set admin Identity API endpoint
    sudo sed -i "s/#identity_uri\s*=.*/identity_uri=http:\/\/127.0.0.1:35357/" \
             /etc/magnum/magnum.conf

    # set public Identity API endpoint
    sudo sed -i "s/#auth_uri\s*=.*/auth_uri=http:\/\/127.0.0.1:5000\/v2.0/" \
             /etc/magnum/magnum.conf

    # set trustee domain id
    sudo sed -i "s/#trustee_domain_name\s*=.*/trustee_domain_name=magnum/" \
             /etc/magnum/magnum.conf

    # set trustee domain admin id
    sudo sed -i "s/#trustee_domain_admin_name\s*=.*/trustee_domain_admin_name=trustee_domain_admin/" \
             /etc/magnum/magnum.conf

    # set trustee domain admin password
    sudo sed -i "s/#trustee_domain_admin_password\s*=.*/trustee_domain_admin_password=password/" \
             /etc/magnum/magnum.conf

    # set correct region name to clients
    sudo sed -i "s/#region_name\s*=.*/region_name=RegionOne/" \
             /etc/magnum/magnum.conf

    # set oslo messaging notifications driver (if using ceilometer)
    sudo sed -i "s/#driver\s*=.*/driver=messaging/" \
             /etc/magnum/magnum.conf

Clone and install the magnum client::

    cd ~
    git clone https://git.openstack.org/openstack/python-magnumclient
    cd python-magnumclient
    sudo pip install -e .

Configure the database for use with magnum. Please note that DB migration
does not work for SQLite backend. The SQLite database does not
have any support for the ALTER statement needed by relational schema
based migration tools. Hence DB Migration will not work for SQLite
backend::

    magnum-db-manage upgrade

Configure the keystone endpoint::

    openstack service create --name=magnum \
                              --description="Container Infrastructure Management Service" \
                              container-infra
    openstack endpoint create --region=RegionOne \
                              container-infra public http://127.0.0.1:9511/v1
    openstack endpoint create --region=RegionOne \
                              container-infra internal http://127.0.0.1:9511/v1
    openstack endpoint create --region=RegionOne \
                              container-infra admin http://127.0.0.1:9511/v1


Start the API service in a new screen::

    magnum-api

Start the conductor service in a new screen::

    magnum-conductor

Magnum should now be up and running!

Further details on utilizing magnum and deploying containers can be found in
the guide :ref:`quickstart`.
