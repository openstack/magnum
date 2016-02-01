=================
Magnum User Guide
=================

This guide is intended for users who use Magnum to deploy and manage clusters
of hosts for a Container Orchestration Engine.  It describes the infrastructure
that Magnum creates and how to work with them.

Section 1-3 describe Magnum itself, including an overview, the CLI and Horizon
interface.  Section 4-8 describe the Container Orchestration Engine's supported
along with a guide on how to select one that best meets your needs.  Section
9-14 describe the low level OpenStack infrastructure that is created and
managed by Magnum to support the Container Orchestration Engine's.

========
Contents
========

#. `Overview`_
#. `Python Client`_
#. `Horizon Interface`_
#. `Choosing COE`_
#. `Native clients`_
#. `Kubernetes`_
#. `Swarm`_
#. `Mesos`_
#. `Transport Layer Security`_
#. `Networking`_
#. `High Availability`_
#. `Scaling`_
#. `Storage`_
#. `Image Management`_

===========
Terminology
===========

Bay
  A bay is the construct in which Magnum launches container orchestration
  engines. After a bay has been created the user is able to add containers to
  it either directly, or in the case of the Kubernetes container orchestration
  engine within pods - a logical construct specific to that implementation. A
  bay is created based on a baymodel.

Baymodel
  A baymodel in Magnum is roughly equivalent to a flavor in Nova. It acts as a
  template that defines options such as the container orchestration engine,
  keypair and image for use when Magnum is creating bays using the given
  baymodel.

Container Orchestration Engine (COE)
  A container orchestration engine manages the lifecycle of one or more
  containers, logically represented in Magnum as a bay. Magnum supports a
  number of container orchestration engines, each with their own pros and cons,
  including Docker Swarm, Kubernetes, and Mesos.

========
Overview
========
*To be filled in*

Magnum rationale, concept, compelling features

BayModel
---------
*To be filled in*

Bay
---
*To be filled in*

=============
Python Client
=============
*To be filled in*

=================
Horizon Interface
=================
*To be filled in with screenshots*

============
Choosing COE
============
*To be filled in*

Buyer's guide with example use case, can use this as model:

http://www.openstack.org/software/project-navigator

==============
Native clients
==============
*To be filled in*

==========
Kubernetes
==========
*To be filled in*

=====
Swarm
=====
*To be filled in*

=====
Mesos
=====
*To be filled in*

========================
Transport Layer Security
========================
*To be filled in*

Native Client Configuration guide for each COE

==========
Networking
==========

There are two components that make up the networking in a cluster.

1. The Neutron infrastructure for the cluster: this includes the
   private network, subnet, ports, routers, load balancers, etc.

2. The networking model presented to the containers: this is what the
   containers see in communicating with each other and to the external
   world. Typically this consists of a driver deployed on each node.

The two components are deployed and managed separately.  The Neutron
infrastructure is the integration with OpenStack; therefore, it
is stable and more or less similar across different COE
types.  The networking model, on the other hand, is specific to the
COE type and is still under active development in the various
COE communities, for example,
`Docker libnetwork <https://github.com/docker/libnetwork>`_ and
`Kubernetes Container Networking
<https://github.com/kubernetes/kubernetes/blob/release-1.1/docs/design/networking.md>`_.
As a result, the implementation for the networking models is evolving and
new models are likely to be introduced in the future.

For the Neutron infrastructure, the following configuration can
be set in the baymodel:

external-network-id
  The external Neutron network ID to connect to this bay. This
  is used to connect the cluster to the external internet, allowing
  the nodes in the bay to access external URL for discovery, image
  download, etc.  If not specified, the default value is "public" and this
  is valid for a typical devstack.

fixed-network
  The Neutron network to use as the private network for the bay nodes.
  If not specified, a new Neutron private network will be created.

dns-nameserver
  The DNS nameserver to use for this bay.  This is an IP address for
  the server and it is used to configure the Neutron subnet of the
  cluster (dns_nameservers).  If not specified, the default DNS is
  8.8.8.8, the publicly available DNS.

http-proxy, https-proxy, no-proxy
  The proxy for the nodes in the bay, to be used when the cluster is
  behind a firewall and containers cannot access URL's on the external
  internet directly.  For the parameter http-proxy and https-proxy, the
  value to provide is a URL and it will be set in the environment
  variable HTTP_PROXY and HTTPS_PROXY respectively in the nodes.  For
  the parameter no-proxy, the value to provide is an IP or list of IP's
  separated by comma.  Likewise, the value will be set in the
  environment variable NO_PROXY in the nodes.

For the networking model to the container, the following configuration
can be set in the baymodel:

network-driver
  The network driver name for instantiating container networks.
  Currently, the following network drivers are supported:

  +--------+-------------+-----------+-------------+
  | Driver | Kubernetes  |   Swarm   |    Mesos    |
  +========+=============+===========+=============+
  | Flannel| supported   | supported | unsupported |
  +--------+-------------+-----------+-------------+
  | Docker | unsupported | supported | supported   |
  +--------+-------------+-----------+-------------+

  If not specified, the default driver is Flannel for Kubernetes, and
  Docker for Swarm and Mesos.

Particular network driver may require its own set of parameters for
configuration, and these parameters are specified through the labels
in the baymodel.  Labels are arbitrary key=value pairs.

When Flannel is specified as the network driver, the following
optional labels can be added:

flannel_network_cidr
  IPv4 network in CIDR format to use for the entire Flannel network.
  If not specified, the default is 10.100.0.0/16.

flannel_network_subnetlen
  The size of the subnet allocated to each host. If not specified, the
  default is 24.

flannel_backend
  The type of backend for Flannel.  Possible values are *udp, vxlan,
  host-gw*.  If not specified, the default is *udp*.  Selecting the
  best backend depends on your networking.  Generally, *udp* is
  the most generally supported backend since there is little
  requirement on the network, but it typically offers the lowest
  performance.  The *vxlan* backend performs better, but requires
  vxlan support in the kernel so the image used to provision the
  nodes needs to include this support.  The *host-gw* backend offers
  the best performance since it does not actually encapsulate
  messages, but it requires all the nodes to be on the same L2
  network.  The private Neutron network that Magnum creates does
  meet this requirement;  therefore if the parameter *fixed_network*
  is not specified in the baymodel, *host-gw* is the best choice for
  the Flannel backend.


=================
High Availability
=================
*To be filled in*

=======
Scaling
=======
*To be filled in*

Include Autoscaling

=======
Storage
=======
*To be filled in*

================
Image Management
================
*To be filled in*

