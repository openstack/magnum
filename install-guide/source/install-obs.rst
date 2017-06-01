.. _install-obs:

Install and configure for openSUSE and SUSE Linux Enterprise
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure the Container
Infrastructure Management service for openSUSE Leap 42.2 and SUSE Linux
Enterprise Server 12 SP2.

.. include:: common/prerequisites.rst

Install and configure components
--------------------------------

#. Install the packages:

   .. code-block:: console

      # zypper install openstack-magnum-api openstack-magnum-conductor python-magnumclient

.. include:: common/configure_2_edit_magnum_conf.rst

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
