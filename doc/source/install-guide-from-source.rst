.. _install:

==========================
Install Magnum from source
==========================

Install and configure
~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure the Container
Infrastructure Management service, code-named magnum, on the controller node.

This section assumes that you already have a working OpenStack environment with
at least the following components installed: Compute, Image Service, Identity,
Networking, Block Storage, Orchestration and Neutron/LBaaS. See `OpenStack
Install Guides <http://docs.openstack.org/#install-guides>`__ for all the above
services apart from Neutron/LBaaS. For Neutron/LBaaS see
`Neutron/LBaaS/HowToRun
<https://wiki.openstack.org/wiki/Neutron/LBaaS/HowToRun>`__.

To store certificates, you can use Barbican (which is recommended) or save
them locally on the controller node. To install Barbican see `Setting up a
Barbican Development Environment <http://docs.openstack.org/developer/barbican/
setup/dev.html#configuring-barbican>`__

Optionally, you can install the following components: Object Storage to make
private Docker registries available to users and Telemetry to send periodically
magnum related metrics. See `OpenStack Install Guides
<http://docs.openstack.org /#install-guides>`__.

.. important::

   Magnum creates VM clusters on the Compute service (nova), called bays. These
   VMs must have basic Internet connectivity and must be able to reach magnum's
   API server. Make sure that Compute and Network services are configured
   accordingly.

Prerequisites
-------------

Before you install and configure the Container Infrastructure Management
service, you must create a database, service credentials, and API endpoints.

#. To create the database, complete these steps:

   * Use the database access client to connect to the database
     server as the ``root`` user:

     .. code-block:: console

        $ mysql -u root -p

   * Create the ``magnum`` database:

     .. code-block:: console

        CREATE DATABASE magnum;

   * Grant proper access to the ``magnum`` database:

     .. code-block:: console

        GRANT ALL PRIVILEGES ON magnum.* TO 'magnum'@'controller' \
          IDENTIFIED BY 'MAGNUM_DBPASS';
        GRANT ALL PRIVILEGES ON magnum.* TO 'magnum'@'%' \
          IDENTIFIED BY 'MAGNUM_DBPASS';

     Replace ``MAGNUM_DBPASS`` with a suitable password.

   * Exit the database access client.

#. Source the ``admin`` credentials to gain access to
   admin-only CLI commands:

   .. code-block:: console

      $ . admin-openrc

#. To create the service credentials, complete these steps:

   * Create the ``magnum`` user:

     .. code-block:: console


        $ openstack user create --domain default \
          --password-prompt magnum
        User Password:
        Repeat User Password:
        +-----------+----------------------------------+
        | Field     | Value                            |
        +-----------+----------------------------------+
        | domain_id | default                          |
        | enabled   | True                             |
        | id        | a8ebafc275c54d389dfc1bff8b4fe286 |
        | name      | magnum                           |
        +-----------+----------------------------------+

   * Add the ``admin`` role to the ``magnum`` user:

     .. code-block:: console

        $ openstack role add --project service --user magnum admin

     .. note::

        This command provides no output.

   * Create the ``magnum`` service entity:

     .. code-block:: console

        $ openstack service create --name magnum \
          --description "Container Infrastructure Management Service" \
          container-infra
        +-------------+-------------------------------------------------------+
        | Field       | Value                                                 |
        +-------------+-------------------------------------------------------+
        | description | OpenStack Container Infrastructure Management service |
        | enabled     | True                                                  |
        | id          | 194faf83e8fd4e028e5ff75d3d8d0df2                      |
        | name        | magnum                                                |
        | type        | container-infra                                       |
        +-------------+-------------------------------------------------------+

#. Create the Container Infrastructure Management service API endpoints:

   .. code-block:: console

      $ openstack endpoint create --region RegionOne \
        container-infra public http://controller:9511/v1
      +--------------+----------------------------------+
      | Field        | Value                            |
      +--------------+----------------------------------+
      | enabled      | True                             |
      | id           | cb137e6366ad495bb521cfe92d8b8858 |
      | interface    | public                           |
      | region       | RegionOne                        |
      | region_id    | RegionOne                        |
      | service_id   | 0f7f62a1f1a247d2a4cb237642814d0e |
      | service_name | magnum                           |
      | service_type | container-infra                  |
      | url          | http://controller:9511/v1        |
      +--------------+----------------------------------+

      $ openstack endpoint create --region RegionOne \
        container-infra internal http://controller:9511/v1
      +--------------+----------------------------------+
      | Field        | Value                            |
      +--------------+----------------------------------+
      | enabled      | True                             |
      | id           | 17cbc3b6f51449a0a818118d6d62868d |
      | interface    | internal                         |
      | region       | RegionOne                        |
      | region_id    | RegionOne                        |
      | service_id   | 0f7f62a1f1a247d2a4cb237642814d0e |
      | service_name | magnum                           |
      | service_type | container-infra                  |
      | url          | http://controller:9511/v1        |
      +--------------+----------------------------------+

      $ openstack endpoint create --region RegionOne \
        container-infra admin http://controller:9511/v1
      +--------------+----------------------------------+
      | Field        | Value                            |
      +--------------+----------------------------------+
      | enabled      | True                             |
      | id           | 30f8888e6b6646d7b5cd14354c95a684 |
      | interface    | admin                            |
      | region       | RegionOne                        |
      | region_id    | RegionOne                        |
      | service_id   | 0f7f62a1f1a247d2a4cb237642814d0e |
      | service_name | magnum                           |
      | service_type | container-infra                  |
      | url          | http://controller:9511/v1        |
      +--------------+----------------------------------+

#. Magnum requires additional information in the Identity service to
   manage COE clusters (bays). To add this information, complete these
   steps:

   * Create the ``magnum`` domain that contains projects and users:

     .. code-block:: console

        $ openstack domain create --description "Owns users and projects \
          created by magnum" magnum
          +-------------+-------------------------------------------+
          | Field       | Value                                     |
          +-------------+-------------------------------------------+
          | description | Owns users and projects created by magnum |
          | enabled     | True                                      |
          | id          | 66e0469de9c04eda9bc368e001676d20          |
          | name        | magnum                                    |
          +-------------+-------------------------------------------+

   * Create the ``magnum_domain_admin`` user to manage projects and users
     in the ``magnum`` domain:

     .. code-block:: console

        $ openstack user create --domain magnum --password-prompt \
          magnum_domain_admin
          User Password:
          Repeat User Password:
          +-----------+----------------------------------+
          | Field     | Value                            |
          +-----------+----------------------------------+
          | domain_id | 66e0469de9c04eda9bc368e001676d20 |
          | enabled   | True                             |
          | id        | 529b81cf35094beb9784c6d06c090c2b |
          | name      | magnum_domain_admin              |
          +-----------+----------------------------------+

   * Add the ``admin`` role to the ``magnum_domain_admin`` user in the
     ``magnum`` domain to enable administrative management privileges
     by the ``magnum_domain_admin`` user:

     .. code-block:: console

        $ openstack role add --domain magnum --user magnum_domain_admin admin

     .. note::

        This command provides no output.

Install and configure components
--------------------------------

#. Install OS-specific prerequisites:

   * Ubuntu 14.04 (trusty) or higher, Debian 8:

     .. code-block:: console

        # apt-get update
        # apt-get install python-dev libssl-dev libxml2-dev \
                          libmysqlclient-dev libxslt-dev libpq-dev git \
                          libffi-dev gettext build-essential

   * Fedora 21 / Centos 7 / RHEL 7

     .. code-block:: console

        # yum install python-devel openssl-devel mysql-devel \
                      libxml2-devel libxslt-devel postgresql-devel git \
                      libffi-devel gettext gcc

   * Fedora 22 or higher

     .. code-block:: console

        # dnf install python-devel openssl-devel mysql-devel \
                      libxml2-devel libxslt-devel postgresql-devel git \
                      libffi-devel gettext gcc

   * openSUSE Leap 42.1

     .. code-block:: console

        # zypper install git libffi-devel libmysqlclient-devel \
                         libopenssl-devel libxml2-devel libxslt-devel \
                         postgresql-devel python-devel gettext-runtime gcc

2. Create magnum user and necessary directories:

   * Create user:

     .. code-block:: console

        # groupadd --system magnum
        # useradd --home-dir "/var/lib/magnum" \
              --create-home \
              --system \
              --shell /bin/false \
              -g magnum \
              magnum

   * Create directories:

     .. code-block:: console

        # mkdir -p /var/log/magnum
        # mkdir -p /etc/magnum

   * Set ownership to directories:

     .. code-block:: console

        # chown magnum:magnum /var/log/magnum
        # chown magnum:magnum /var/lib/magnum
        # chown magnum:magnum /etc/magnum

3. Install virtualenv and python prerequisites:

   * Install virtualenv and create one for magnum's installation:

     .. code-block:: console

        # easy_install -U virtualenv
        # su -s /bin/sh -c "virtualenv /var/lib/magnum/env" magnum

   * Install python prerequisites:

     .. code-block:: console

        # su -s /bin/sh -c "/var/lib/magnum/env/bin/pip install tox pymysql \
          python-memcached" magnum

4. Clone and install magnum:

   .. code-block:: console

      # cd /var/lib/magnum
      # git clone https://git.openstack.org/openstack/magnum.git
      # chown -R magnum:magnum magnum
      # cd magnum
      # su -s /bin/sh -c "/var/lib/magnum/env/bin/pip install -r requirements.txt" magnum
      # su -s /bin/sh -c "/var/lib/magnum/env/bin/python setup.py install" magnum

5. Copy policy.json and api-paste.ini:

   .. code-block:: console

      # su -s /bin/sh -c "cp etc/magnum/policy.json /etc/magnum" magnum
      # su -s /bin/sh -c "cp etc/magnum/api-paste.ini /etc/magnum" magnum

6. Generate a sample configuration file:

   .. code-block:: console

      # su -s /bin/sh -c "/var/lib/magnum/env/bin/tox -e genconfig" magnum
      # su -s /bin/sh -c "cp etc/magnum/magnum.conf.sample \
        /etc/magnum/magnum.conf" magnum

7. Edit the ``/etc/magnum/magnum.conf``:

   * In the ``[api]`` section, configure the host:

     .. code-block:: ini

        [api]
        ...
        host = controller

   * In the ``[certificates]`` section, select ``barbican`` (or ``local`` if
     you don't have barbican installed):

     * Use barbican to store certificates:

       .. code-block:: ini

          [certificates]
          ...
          cert_manager_type = barbican

     .. important::

       Barbican is recommended for production environments, local store should
       be used for evaluation purposes.

     * To use local store for certificates, you have to create and specify the
       directory to use:

       .. code-block:: console

          # su -s /bin/sh -c  "mkdir -p /var/lib/magnum/certificates/" magnum

       .. code-block:: ini

          [certificates]
          ...
          cert_manager_type = local
          storage_path = /var/lib/magnum/certificates/

   * In the ``[cinder_client]`` section, configure the region name:

     .. code-block:: ini

        [cinder_client]
        ...
        region_name = RegionOne

   * In the ``[database]`` section, configure database access:

     .. code-block:: ini

        [database]
        ...
        connection = mysql+pymysql://magnum:MAGNUM_DBPASS@controller/magnum

     Replace ``MAGNUM_DBPASS`` with the password you chose for
     the magnum database.

   * In the ``[keystone_authtoken]`` and ``trust`` sections, configure
     Identity service access:

     .. code-block:: ini

        [keystone_authtoken]
        ...
        memcached_servers = controller:11211
        auth_version = v3
        auth_uri = http://controller:5000/v3
        project_domain_id = default
        project_name = service
        user_domain_id = default
        password = MAGNUM_PASS
        username = magnum
        auth_url = http://controller:35357
        auth_type = password

        [trust]
        ...
        trustee_domain_id = 66e0469de9c04eda9bc368e001676d20
        trustee_domain_admin_id = 529b81cf35094beb9784c6d06c090c2b
        trustee_domain_admin_password = DOMAIN_ADMIN_PASS

     ``trustee_domain_id`` is the id of the ``magnum`` domain and
     ``trustee_domain_admin_id`` is the id of the ``magnum_domain_admin`` user.
     Replace MAGNUM_PASS with the password you chose for the magnum user in the
     Identity service and DOMAIN_ADMIN_PASS with the password you chose for the
     ``magnum_domain_admin`` user.

   * In the ``[oslo_concurrency]`` section, configure the ``lock_path``:

     .. code-block:: ini

        [oslo_concurrency]
        ...
        lock_path = /var/lib/magnum/tmp

   * In the ``[oslo_messaging_notifications]`` section, configure the
     ``driver``:

     .. code-block:: ini

        [oslo_messaging_notifications]
        ...
        driver = messaging

   * In the ``[oslo_messaging_rabbit]`` section, configure RabbitMQ message
     queue access:

     .. code-block:: ini

        [oslo_messaging_rabbit]
        ...
        rabbit_host = controller
        rabbit_userid = openstack
        rabbit_password = RABBIT_PASS

     Replace RABBIT_PASS with the password you chose for the openstack account
     in RabbitMQ.

   .. note::

      Make sure that ``/etc/magnum/magnum.conf`` still have the correct
      permissions. You can set the permissions again with:

      # chown magnum:magnum /etc/magnum/magnum.conf

8. Populate Magnum database:

   .. code-block:: console

      # su -s /bin/sh -c "/var/lib/magnum/env/bin/magnum-db-manage upgrade" magnum

9. Update heat policy to allow magnum list stacks. Edit your heat policy file,
   usually ``/etc/heat/policy.json``:

   .. code-block:: ini

      ...
      stacks:global_index: "role:admin",

   Now restart heat.

10. Set magnum for log rotation:

   .. code-block:: console

      # cd /var/lib/magnum/magnum
      # cp doc/examples/etc/logrotate.d/magnum.logrotate /etc/logrotate.d/magnum

Finalize installation
---------------------

#. Create init scripts and services:

   * Ubuntu 14.04 (trusty):

     .. code-block:: console

        # cd /var/lib/magnum/magnum
        # cp doc/examples/etc/init/magnum-api.conf \
          /etc/init/magnum-api.conf
        # cp doc/examples/etc/init/magnum-conductor.conf \
          /etc/init/magnum-conductor.conf

   * Ubuntu 14.10 or higher, Fedora 21 or higher/RHEL 7/CentOS 7,  openSUSE
     Leap 42.1 or Debian 8:

     .. code-block:: console

        # cd /var/lib/magnum/magnum
        # cp doc/examples/etc/systemd/system/magnum-api.service \
          /etc/systemd/system/magnum-api.service
        # cp doc/examples/etc/systemd/system/magnum-conductor.service \
          /etc/systemd/system/magnum-conductor.service

#. Start magnum-api and magnum-conductor

   * Ubuntu 14.04 (trusty):

     .. code-block:: console

        # start magnum-api
        # start magnum-conductor

   * Ubuntu 14.10 or higher, Fedora 21 or higher/RHEL 7/CentOS 7,  openSUSE
     Leap 42.1 or Debian 8:

     .. code-block:: console

        # systemctl enable magnum-api
        # systemctl enable magnum-conductor

     .. code-block:: console

        # systemctl start magnum-api
        # systemctl start magnum-conductor

#. Verify that magnum-api and magnum-conductor services are running

   * Ubuntu 14.04 (trusty):

     .. code-block:: console

        # status magnum-api
        # status magnum-conductor

   * Ubuntu 14.10 or higher, Fedora 21 or higher/RHEL 7/CentOS 7,  openSUSE
     Leap 42.1 or Debian 8:

     .. code-block:: console

        # systemctl status magnum-api
        # systemctl status magnum-conductor
