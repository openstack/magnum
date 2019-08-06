2. Edit the ``/etc/magnum/magnum.conf`` file:

   * In the ``[api]`` section, configure the host:

     .. code-block:: ini

        [api]
        ...
        host = CONTROLLER_IP

     Replace ``CONTROLLER_IP`` with the IP address on which you wish magnum api
     should listen.

   * In the ``[certificates]`` section, select ``barbican`` (or ``x509keypair`` if
     you don't have barbican installed):

     * Use barbican to store certificates:

       .. code-block:: ini

          [certificates]
          ...
          cert_manager_type = barbican

     .. important::

        Barbican is recommended for production environments.

     * To store x509 certificates in magnum's database:

       .. code-block:: ini

          [certificates]
          ...
          cert_manager_type = x509keypair

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

   * In the ``[keystone_authtoken]`` and ``[trust]`` sections, configure
     Identity service access:

     .. code-block:: ini

        [keystone_authtoken]
        ...
        memcached_servers = controller:11211
        auth_version = v3
        www_authenticate_uri = http://controller:5000/v3
        project_domain_id = default
        project_name = service
        user_domain_id = default
        password = MAGNUM_PASS
        username = magnum
        auth_url = http://controller:5000
        auth_type = password
        admin_user = magnum
        admin_password = MAGNUM_PASS
        admin_tenant_name = service

        [trust]
        ...
        trustee_domain_name = magnum
        trustee_domain_admin_name = magnum_domain_admin
        trustee_domain_admin_password = DOMAIN_ADMIN_PASS
        trustee_keystone_interface = KEYSTONE_INTERFACE

     Replace MAGNUM_PASS with the password you chose for the magnum user in the
     Identity service and DOMAIN_ADMIN_PASS with the password you chose for the
     ``magnum_domain_admin`` user.

     Replace KEYSTONE_INTERFACE with either ``public`` or ``internal``
     depending on your network configuration. If your instances cannot reach
     internal keystone endpoint which is often the case in production
     environments it should be set to ``public``. Default to ``public``

   * In the ``[oslo_messaging_notifications]`` section, configure the
     ``driver``:

     .. code-block:: ini

        [oslo_messaging_notifications]
        ...
        driver = messaging

   * In the ``[DEFAULT]`` section,
     configure ``RabbitMQ`` message queue access:

     .. code-block:: ini

        [DEFAULT]
        ...
        transport_url = rabbit://openstack:RABBIT_PASS@controller

     Replace ``RABBIT_PASS`` with the password you chose for the
     ``openstack`` account in ``RabbitMQ``.


