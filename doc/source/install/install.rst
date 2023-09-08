.. _install:

Install and configure
~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure the Container
Infrastructure Management service, code-named magnum, on the controller node.

This section assumes that you already have a working OpenStack environment with
at least the following components installed: Identity service, Image service,
Compute service, Networking service, Block Storage service and Orchestration
service. See `OpenStack Install Guides <https://docs.openstack.org/
#install-guides>`__.

To provide access to Kubernetes using the native client (kubectl) magnum uses
TLS certificates. To store the certificates, it is recommended to use the
`Key Manager service, code-named barbican
<https://docs.openstack.org/project-install-guide/key-manager/draft/>`__,
or you can save them in magnum's database.

Optionally, you can install the following components:

- `Load Balancer as a Service (LBaaS v2) <https://docs.openstack.org/
  ocata/networking-guide/config-lbaas.html>`__ to create clusters with multiple
  masters
- `Bare Metal service
  <https://docs.openstack.org/ironic/latest/install/index.html/>`__
  to create baremetal clusters
- `Object Storage service
  <https://docs.openstack.org/swift/latest/install/index.html>`__
  to make private Docker registries available to
  users
- `Telemetry Data Collection service
  <https://docs.openstack.org/ceilometer/latest/install/index.html>`__
  to periodically send magnum-related metrics

.. note::

   Installation and configuration vary by distribution.

.. important::

   Magnum creates clusters of compute instances on the Compute service (nova).
   These instances must have basic Internet connectivity and must be able to
   reach magnum's API server. Make sure that the Compute and Network services
   are configured accordingly.

.. toctree::
   :maxdepth: 2

   install-debian-manual.rst
   install-obs.rst
   install-rdo.rst
   install-ubuntu.rst
   install-guide-from-source.rst
