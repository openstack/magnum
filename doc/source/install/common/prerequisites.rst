Prerequisites
-------------

Before you install and configure the Container Infrastructure Management
service, you must create a database, service credentials, and API endpoints.

#. To create the database, complete these steps:

   * Use the database access client to connect to the database
     server as the ``root`` user:

     .. code-block:: console

        # mysql

   * Create the ``magnum`` database:

     .. code-block:: console

        CREATE DATABASE magnum;

   * Grant proper access to the ``magnum`` database:

     .. code-block:: console

        GRANT ALL PRIVILEGES ON magnum.* TO 'magnum'@'localhost' \
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
          --description "OpenStack Container Infrastructure Management Service" \
          container-infra
        +-------------+-------------------------------------------------------+
        | Field       | Value                                                 |
        +-------------+-------------------------------------------------------+
        | description | OpenStack Container Infrastructure Management Service |
        | enabled     | True                                                  |
        | id          | 194faf83e8fd4e028e5ff75d3d8d0df2                      |
        | name        | magnum                                                |
        | type        | container-infra                                       |
        +-------------+-------------------------------------------------------+

#. Create the Container Infrastructure Management service API endpoints:

   .. code-block:: console

      $ openstack endpoint create --region RegionOne \
        container-infra public http://CONTROLLER_IP:9511/v1
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
      | url          | http://CONTROLLER_IP:9511/v1     |
      +--------------+----------------------------------+

      $ openstack endpoint create --region RegionOne \
        container-infra internal http://CONTROLLER_IP:9511/v1
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
      | url          | http://CONTROLLER_IP:9511/v1     |
      +--------------+----------------------------------+

      $ openstack endpoint create --region RegionOne \
        container-infra admin http://CONTROLLER_IP:9511/v1
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
      | url          | http://CONTROLLER_IP:9511/v1     |
      +--------------+----------------------------------+

   Replace ``CONTROLLER_IP`` with the IP magnum listens to. Alternatively,
   you can use a hostname which is reachable by the Compute instances.

#. Magnum requires additional information in the Identity service to
   manage COE clusters. To add this information, complete these steps:

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

        $ openstack role add --domain magnum --user-domain magnum --user \
          magnum_domain_admin admin

     .. note::

        This command provides no output.
