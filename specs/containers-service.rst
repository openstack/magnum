..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================
Containers Service
==================

Launchpad blueprint:

https://blueprints.launchpad.net/nova/+spec/containers-service

Containers share many features in common with Nova instances. For the common
features, virt drivers for Nova can be used to surface basic instance
functionality. For features that go beyond what can be naturally fit within
a virt driver, we propose a new API service that allows for advanced features
to be added without conflating the worlds of instances and containers.

Some examples of containers specific features are setting of shell environment
variables, and accepting a shell command to execute at runtime. Capturing the
STDIO of the process(es) within a container, and tracking the return status
of processes are all beyond the scope of what was contemplated for Nova. All
of these features will be implemented in the Containers Service.


Problem description
===================
Container technology is rapidly gaining popularity as a way to bundle and
deploy applications. Recognizing and adapting to this trend will position
OpenStack to be useful not only to clouds that employ bare metal and virtual
machine instances, but can remain competitive in offering container services
as well.

Nova's concepts of an instance, and the actions that may be taken on it do not
match completely with containers.

Use cases
---------
1. App Consolidation. End-user wants to run multiple small applications in
   separate operating system environments, but wants to optimize for efficiency
   to control hosting costs. Each application belongs to the same tenant, so
   security isolation between applications is nice-to-have but not critical.
   Isolation is desired primarily for simplified management of the execution
   environment for each application.
2. App Portability. End-user wants to create a single container image, and
   deploy the same image to multiple hosting environments, including OpenStack.
   Other environments may include local servers, dedicated servers, private
   clouds, and public clouds. Switching environments requires passing database
   connection strings by environment variables at the time a container starts
   to allow the application to use the services available in each environment
   without changing the container image.
3. Docker Compatibility. End-user has a Dockerfile used to build an application
   and its runtime environment and dependencies in a Docker container image.
   They want an easy way to run the Docker resulting image on an OpenStack
   cloud.
4. LXC Compatibility. End-user wants an easy way to remotely create multiple
   LXC containers within a single Nova instance.
5. OpenVZ Compatibility. End-user wants an easy way to remotely create multiple
   OpenVZ containers within a single Nova instance.
6. Containers-Centric World View. End-user wants to communicate with a single
   OpenStack API, and request the addition of containers, without the need to
   be concerned with keeping track of how many containers are already running
   on a given Nova instance, and when more need to be created. They want to
   simply create and remove containers, and allow the appropriate resource
   scheduling to happen automatically.
7. Platform Integration. Cloud operator already has an OpenStack cloud, and
   wants to add a service/application centric management system on top.
   Examples of such systems are Cloud Foundry, Kubernetes, Apache Mesos, etc.
   The selected system is already Docker compatible. Allow this cloud operator
   easy integration with OpenStack to run applications in containers. The
   Cloud Operator now harnesses the power of both the management system, and
   OpenStack, and does not need to manage a second infrastructure for his/her
   application hosting needs. All details involving the integration of
   containers with Nova instances is managed by OpenStack.
8. Container network. End-user wants to define a custom overlay network for
   containers, and wants to have admin privilege to manage the network
   topology. Building a container network can decouple application deployment
   and management from the underlying network infrastructure, and enable
   additional usage scenario, such as (i) software-defined networking, and
   (ii) extending the container network (i.e. connecting various resources from
   multiple hosting environments). End-users want a single service that could
   help them build the container network, and dynamically modify the network
   topology by adding or removing containers to or from the network.
9. Permit secure use of native REST APIs. Provide two models of operation with
   Magnum.  The first model allows Magnum to manage the lifecycle of Pods,
   ReplicationControllers, and Services.  The second model allows end-users to
   manage the lifecycle of Pods, ReplicationControllers, and Services by
   providing direct secure access to the native ReST APIs in Kubernetes and
   possibly Docker.

Long Term Use Cases
-------------------
These use cases have been identified by the community as important, but
unlikely to be tackled in short term (especially prior to incubation). We wish
to adapt to these use cases in long term, but this is not a firm project
commitment.

1. Multi-region/multi-cloud support. End-user wants to deploy applications to
   multiple regions/clouds, and dynamically relocate deployed applications
   across different regions/clouds. In particular, they want a single service
   that could help them (i) provision nodes from multiple regions/clouds, thus
   running containers on top of them, and (ii) dynamically relocate containers
   (e.g. through container migration) between nodes regardless of the
   underlying infrastructure.

Proposed change
===============
Add a new API service for CRUD and advanced management of containers.
If cloud operators only want to offer basic instance features for their
containers, they may use nova with an alternate virt-driver, such as
libvirt/lxc or nova-docker. For those wanting a full-featured container
experience, they may offer the Containers Service API as well, in combination
with Nova instances that contain an OpenStack agent that connects to the
containers service through a security controlled agent (daemon) that allows
the OpenStack control plane to provision and control containers running on
Compute Hosts.

The Containers Service will call the Nova API to create one or more Nova
instances inside which containers will be created. The Nova instances may
be of any type, depending on the virt driver(s) chosen by the cloud operator.
This includes bare-metal, virtual machines, containers, and potentially other
instance types.

This allows the following configurations of containers in OpenStack.

* Containers in Virtual Machine Instances
* Containers in Bare Metal Instances
* Containers in Container Instances (nested)

The concept of nesting containers is currently possible if the parent container
runs in privileged mode. Patches to the linux kernel are being developed to
allow nesting of non-privileged containers as well, which provides a higher
level of security.

The spirit of this plan aims to duplicate as little as possible between Nova
and the Containers Service. Common components like the scheduler are expected
to be abstracted into modules, such as Gantt that can be shared by multiple
projects. Until Gantt is ready for use by the Containers Service, we will
implement only two provisioning schemes for containers:

1. Create a container on a specified instance by using a nova instance guid.
2. Auto-create instances (applies only until the Gantt scheduler is used)
   2.1. Fill them sequentially until full.
   2.2. Remove them automatically when they become empty.

The above orchestration will be implemented using Heat. This requires some
kind of hypervisor painting (such as host aggregates) for security reasons.

The diagram below offers an overview of the system architecture. The OSC box
indicates an OpenStack client, which will communicate with the Containers
Service through a REST API. The containers service may silently create Nova
instances if one with enough capacity to host the requested container is not
already known to the Containers service. The containers service will maintain
a database "Map" of containers, and what Nova instance each belongs to. Nova
creates instances. Instances are created in Nova, and containers belong only
to the Containers Service, and run within a Nova instance. If the instance
includes the agent software "A", then it may be included in the inventory of
the Containers service. Instances that do not contain an agent may not interact
with the Containers Service, and can be controlled only by a Nova virt driver.

::

                            +---------+
                            |   OSC   |
                            +----+----+
                                 |
                            +----+----+
 +-------- Nova -------+  +-+  REST   +-- Containers -+
 |                     |  | +---------+    Service    |
 |                     |  |                           |
 |           +-------+ +--+ +-----+                   |
 |           | Gantt | |  | | Map |                   |
 |           +-------+ |  | +-----+                   |
 |                     |  |                           |
 +-----------+---------+  +---------------+-----------+
             |                            |
 +-----------+----+ Compute Host ---------|-----------+
 |                                    +---+---+       |
 |                               +----+ Relay +---+   |
 |                               |    +-------+   |   |
 |                               |                |   |
 | +-- Instance --+ +-- Instance |-+ +-- Instance |-+ |
 | |              | |            | | |            | | |
 | |              | |        +---+ | |        +---+ | |
 | |              | |        |   | | |        |   | | |
 | |              | |        | A | | |        | A | | |
 | |              | |        |   | | |        |   | | |
 | |              | |        +---+ | |        +---+ | |
 | |              | |              | |              | |
 | |              | | +---+  +---+ | | +---+  +---+ | |
 | |              | | |   |  |   | | | |   |  |   | | |
 | |              | | | C |  | C | | | | C |  | C | | |
 | |              | | |   |  |   | | | |   |  |   | | |
 | |              | | +---+  +---+ | | +---+  +---+ | |
 | |              | |              | |              | |
 | +--------------+ +--------------+ +--------------+ |
 |                                                    |
 +----------------------------------------------------+
 +---+
 |   |
 | A | = Agent
 |   |
 +---+
 +---+
 |   |
 | C | = Container
 |   |
 +---+


Design Principles
-----------------
1. Leverage existing OpenStack projects for what they are good at. Do not
   duplicate functionality, or copy code that can be otherwise accessed through
   API calls.
2. Keep modifications to Nova to a minimum.
3. Make the user experience for end users simple and familiar.
4. Allow for implementation of all features containers are intended to offer.


Alternatives
------------

1. Extending Nova's existing feature set to offer container features
1.1. Container features don't fit into Nova's idea of compute (VM/Server)
2. A completely separate containers service forked from Nova.
2.1. Would result in large overlap and duplication in features and code


Data model impact
-----------------
For Nova, None. All new data planned will be in the Containers Service.


REST API impact
---------------
For Nova, none. All new API calls will be implemented in the Containers
Service. The OpenStack Containers Service API will be a superset of
functionality offered by the, The `Docker Remote API:
<https://docs.docker.com/reference/api/docker_remote_api/>`_
with additionals to make is suitable for general use regardless of the backend
container technology used, and to be compatible with OpenStack multi-tenancy
and Keystone authentication.

Specific Additions:

1. Support for the X-Auth-Project-Id HTTP request header to allow for
   multi-tenant use.
2. Support for the X-Auth-Token HTTP request header to allow for authentication
   with keystone.

If either of the above headers are missing, a 401 Unauthorized response will
be generated.

Docker CLI clients may communicate with a Swarmd instance that is configured
to use the OpenStack Containers API as the backend for libswarm. This will
allow for tool compatibility with the Docker ecosystem using the officially
supported means for integration of a distributed system.

The scope of the full API will cause this spec to be too long to review, so
the intent is to deal with the specific API design as a series of Gerrit
reviews that submit API code as Not Implemented stubs with docstrings that
clearly document the design, so allow for approval, and further implementation.

Security impact
---------------
Because Nova will not be changed, there should be no security impacts to Nova.
The Containers Service implementation, will have the following security related
issues:

* Need to authenticate against keystone using python-keystoneclient.
* A trust token from Nova will be needed in order for the Containers Service
  to call the Nova API on behalf of a user.
* Limits must be implemented to control resource consumption in accordance with
  quotas.
* Providing STDIO access may generate a considerable amount of network chatter
  between containers and clients through the relay. This could lead to
  bandwidth congestion at the relays, or API nodes. An approach similar to
  how we handle serial console access today will need to be considered to
  mitigate this concern.

Using containers implies a range of security considerations for cloud
operators. These include:

* Containers in the same instance share an operating system. If the kernel is
  exploited using a security vulnerability, processes in once container may
  escape the constraints of the container and potentially access other
  resources on the host, including contents of other containers.
* Output of processes may be persisted by the containers service in order to
  allow asynchronous collection of exit status, and terminal output. Such
  content may include sensitive information. Features may be added to mitigate
  the risk of this data being replicated in log messages, including errors.
* Creating containers usually requires root access. This means that the Agent
  may need to be run with special privileges, or be given a method to
  escalate privileges using techniques such as sudo.
* User provided data is passed through the API. This will require sensible
  data input validation.


Notifications impact
--------------------

Contemplated features (in subsequent release cycles):

* Notify the end user each time a Nova instance is created or deleted by
  the Containers service, if (s)he has registered for such notifications.
* Notify the user each on CRUD of containers containing start and end
  notifications. (compute.container.create/delete/etc)
* Notify user periodically of existence of container service managed
  containers (ex compute.container.exists)


Other end user impact
---------------------

The user interface will be a REST API. On top of that API will be an
implementation of the libswarm API to allow for tools designed to use Docker
to treat OpenStack as an upstream system.


Performance Impact
------------------

The Nova API will be used to create instances as needed. If the Container to
Instance ratio is 10, then the Nova API will be called at least once for every
10 calls to the Containers Service. Instances that are left empty will be
automatically deleted, so in the example of a 10:1 ratio, the Nova API will be
called to perform a delete for every 10 deletes in the Container Service.
Depending on the configuration, the ratio may be as low as 1:1.
The Containers Service will only access Nova through its API, not by accessing
its database.



Other deployer impact
---------------------

Deployers may want to adjust the default flavor used for Nova Instances created
by the Containers Service.

There should be no impact on users of prior releases, as this introduces a new
API.

Developer impact
----------------

Minimal. There will be minimal changes required in Nova, if any.


Implementation
==============


Assignee(s)
-----------

Primary assignee:
aotto

Other contributors:
andrew-melton
ewindisch


Work Items
----------

1. Agent
2. Relay
3. API Service
4. IO Relays


Dependencies
============

1. <Links to Agent Blueprint and Spec here, once ready>
2. Early implementations may use libswarm, or a python port of libswarm to
   implement Docker API compatibility.

Testing
=======

Each commit will be accompanied with unit tests, and Tempest functional tests.


Documentation Impact
====================

A set of documentation for this new service will be required.


References
==========

* Link to high level draft proposal from the Nova Midcycle Meetup for Juno:
  `PDF <https://wiki.openstack.org/w/images/5/51/Containers_Proposal.pdf>`_
* `Libswarm Source <https://github.com/docker/libswarm>`_
