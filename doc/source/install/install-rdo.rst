.. _install-rdo:

Install and configure for Red Hat Enterprise Linux and CentOS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure the Container
Infrastructure Management service for Red Hat Enterprise Linux 7 and CentOS 7.

.. include:: common/prerequisites.rst

Install and configure components
--------------------------------

#. Install the packages:

   .. code-block:: console

      # yum install openstack-magnum-api openstack-magnum-conductor python-magnumclient

.. include:: common/configure_2_edit_magnum_conf.rst

* Additionally, edit the ``/etc/magnum/magnum.conf`` file:

  * In the ``[oslo_concurrency]`` section, configure the ``lock_path``:

    .. code-block:: ini

       [oslo_concurrency]
       ...
       lock_path = /var/lib/magnum/tmp

.. include:: common/configure_3_populate_database.rst

Finalize installation
---------------------

* Start the Container Infrastructure Management services and configure
  them to start when the system boots:

  .. code-block:: console

     # systemctl enable openstack-magnum-api.service \
       openstack-magnum-conductor.service
     # systemctl start openstack-magnum-api.service \
       openstack-magnum-conductor.service
