2. Edit the ``/etc/magnum/magnum.conf``:

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

     * To use local store for certificates, you have to specify the directory
       to use:

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

3. Populate Magnum database:

   .. code-block:: console

      # su -s /bin/sh -c "magnum-db-manage upgrade" magnum

4. Update heat policy to allow magnum list stacks. Edit your heat policy file,
   usually ``/etc/heat/policy.json``:

   .. code-block:: ini

      ...
      stacks:global_index: "role:admin",

   Now restart heat.
