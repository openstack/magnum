.. _install-obs:

Install and configure for openSUSE and SUSE Linux Enterprise
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure the Container
Infrastructure Management service for openSUSE Leap 42.1 and SUSE Linux
Enterprise Server 12 SP1.

.. include:: common_prerequisites.rst

Install and configure components
--------------------------------

#. Install the packages:

   .. code-block:: console

      # zypper install openstack-magnum-api openstack-magnum-conductor

.. include:: common_configure.rst

Finalize installation
---------------------

#. Start Magnum services and configure them to start when
   the system boots:

   .. code-block:: console

      # systemctl enable openstack-magnum-api.service \
        openstack-magnum-conductor.service
      # systemctl start openstack-magnum-api.service \
        openstack-magnum-conductor.service
