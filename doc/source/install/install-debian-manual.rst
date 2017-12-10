.. _install-debian-manual:

Install and configure for Debian
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure the Container
Infrastructure Management service for Debian.

.. include:: common/prerequisites.rst

Install and configure components
--------------------------------

#. Install the common and library packages:

   .. code-block:: console

      # DEBIAN_FRONTEND=noninteractive apt-get install magnum-api magnum-conductor

.. include:: common/configure_2_edit_magnum_conf.rst

.. include:: common/configure_3_populate_database.rst

Finalize installation
---------------------

* Restart the Container Infrastructure Management services:

  .. code-block:: console

     # service magnum-api restart
     # service magnum-conductor restart
