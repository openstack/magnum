.. _install:

Install and configure
~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure the Container
Infrastructure Management service, code-named magnum, on the controller node.

This section assumes that you already have a working OpenStack environment with
at least the following components installed: Compute, Image Service, Identity,
Networking, Block Storage, Orchestration and Neutron/LBaaS. See `OpenStack
Install Guides <http://docs.openstack.org/#install-guides>`__ for all the above
services apart from Neutron/LBaaS. For Neutron/LBaaS see
`Neutron/LBaaS/HowToRun
<https://wiki.openstack.org/wiki/Neutron/LBaaS/HowToRun>`__.

To store certificates, you can use Barbican (which is recommended) or save
them locally on the controller node. To install Barbican see `Setting up a
Barbican Development Environment <http://docs.openstack.org/developer/barbican/
setup/dev.html#configuring-barbican>`__

Optionally, you can install the following components: Object Storage to make
private Docker registries available to users and Telemetry to send periodically
magnum related metrics. See `OpenStack Install Guides
<http://docs.openstack.org /#install-guides>`__.

.. note::

   Installation and configuration vary by distribution.

.. important::

   Magnum creates VM clusters on the Compute service (nova), called bays. These
   VMs must have basic Internet connectivity and must be able to reach magnum's
   API server. Make sure that Compute and Network services are configured
   accordingly.

.. toctree::
   :maxdepth: 2

   install-obs.rst
   install-rdo.rst
