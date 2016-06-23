.. _install-rdo:

Install and configure for Red Hat Enterprise Linux and CentOS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure the Container
Infrastructure Management service for Red Hat Enterprise Linux 7 and CentOS 7.

.. include:: common_prerequisites.rst

Install and configure components
--------------------------------

#. Install the packages:

   .. code-block:: console

      # yum install openstack-magnum-api openstack-magnum-conductor

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
