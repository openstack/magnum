.. _verify:

Verify operation
~~~~~~~~~~~~~~~~

Verify operation of the Container Infrastructure Management service.

.. note::

   Perform these commands on the controller node.

#. Source the ``admin`` tenant credentials:

   .. code-block:: console

      $ . admin-openrc

#. To list out the health of the internal services, namely conductor, of
   magnum, use:

   .. code-block:: console

      $ openstack coe service list
      +----+-----------------------+------------------+-------+
      | id | host                  | binary           | state |
      +----+-----------------------+------------------+-------+
      | 1  | controller            | magnum-conductor | up    |
      +----+-----------------------+------------------+-------+

   .. note::

      This output should indicate a ``magnum-conductor`` component
      on the controller node.
