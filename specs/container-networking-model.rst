..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================
Magnum Container Networking Model
=================================

Launchpad Blueprint:

https://blueprints.launchpad.net/magnum/+spec/extensible-network-model

For Magnum to prosper, the project must support a range of networking tools
and techniques, while maintaining a simple, developer-focused user
experience. The first step in achieving this goal is to standardize the
process of allocating networking to containers, while providing an
abstraction for supporting various networking capabilities through
pluggable back-end implementations. This document recommends using Docker's
libnetwork library to implement container networking abstractions and
plugins. Since libnetwork is not a standard and the container ecosystem
is rapidly evolving, the Magnum community should continue evaluating
container networking options on a frequent basis.

Problem Description
===================

The container networking ecosystem is undergoing rapid changes. The
networking tools and techniques used in today's container deployments are
different than twelve months ago and will continue to evolve. For example,
Flannel [6]_, Kubernetes preferred networking implementation, was initially
released in July of 2014 and was not considered preferred until early 2015.

Furthermore, the various container orchestration engines have not
standardized on a container networking implementation and may never. For
example, Flannel is the preferred container networking implementation for
Kubernetes but not for Docker Swarm. Each container networking implementation
comes with its own API abstractions, data model, tooling, etc.. Natively
supporting each container networking implementation can be a burden on the
Magnum community and codebase. By supporting only a subset of container
networking implementations, the project may not be widely adopted or may
provide a suboptimal user experience.

Lastly, Magnum has limited support for advanced container networking
functionality. Magnum instantiates container networks behind the scenes
through Heat templates, exposing little-to-no user configurability. Some
users require the ability to customize their container environments,
including networking details. However, networking needs to "just work" for
users that require no networking customizations.

Roles
-----

The following are roles that the Magnum Container Networking Model takes
into consideration. Roles are an important reference point when creating
user stories. This is because each role provides different functions and
has different requirements.

1. Cloud Provider (CP): Provides standard OpenStack cloud infrastructure
   services, including the Magnum service.

2. Container Service Provider (CSP): Uses Magnum to deliver
   Containers-as-a-Service (CaaS) to users. CSPs are a consumer of CP
   services and a CaaS provider to users.

3. Users: Consume Magnum services to provision and manage clustered
   container environments and deploy apps within the container clusters.

The container ecosystem focuses on the developer user type. It is imperative
that the Magnum Container Networking Model meets the need of this user type.

These roles are not mutually exclusive. For example:

1. A CP can also be a CSP. In this case, the CP/CSP provisions and manages
   standard OpenStack services, the Magnum service, and provides CaaS
   services to users.

2. A User can also be a CSP. In this case, the user provisions their own
   baymodels, bays, etc. from the CP.

Definitions
-----------

COE
  Container Orchestration Engine

Baymodel
  An object that stores template information about the bay which is
  used to create new bays consistently.

Bay
  A Magnum resource that includes at least one host to run containers on,
  and a COE to manage containers created on hosts within the bay.

Pod
  Is the smallest deployable unit that can be created, scheduled, and
  managed within Kubernetes.

Additional Magnum definitions can be found in the Magnum Developer
documentation [2]_.

Use Cases
----------

This document does not intend to address each use case. The use cases are
provided as reference for the long-term development of the Magnum Container
Networking Model.

As a User:

1. I need to easily deploy containerized apps in an OpenStack cloud.
   My user experience should be similar to how I deploy containerized apps
   outside of an OpenStack cloud.

2. I need to have containers communicate with vm-based apps that use
   OpenStack networking.

3. I need the option to preserve the container's IP address so I can
   manage containers by IP's, not just ports.

4. I need to block unwanted traffic to/from my containerized apps.

5. I need the ability for my containerized apps to be highly available.

6. I need confidence that my traffic is secure from other tenants traffic.

As a CSP:

1. I need to easily deploy a bay for consumption by users. The bay must
   support the following:

   A. One or more hosts to run containers.
   B. The ability to choose between virtual or physical hosts to run
      containers.
   C. The ability to automatically provision networking to containers.

2. I need to provide clustering options that support different
   container/image, formats and technologies.

3. After deploying my initial cluster, I need the ability to provide ongoing
   management, including:

   A. The ability to add/change/remove networks that containers connect to.
   B. The ability to add/change/remove nodes within the cluster.

4. I need to deploy a Bay without admin rights to OpenStack services.

5. I need the freedom to choose different container networking tools and
   techniques offered by the container ecosystem beyond OpenStack.

As a CP:

1. I need to easily and reliably add the Magnum service to my existing
   OpenStack cloud environment.

2. I need to easily manage (monitor, troubleshoot, etc..) the Magnum
   service. Including the ability to mirror ports to capture traffic
   for analysis.

3. I need to make the Magnum services highly-available.

4. I need to make Magnum services highly performant.

5. I need to easily scale-out Magnum services as needed.

6. I need Magnum to be robust regardless of failures within the container
   orchestration engine.

Proposed Changes
================

1. Currently, Magnum supports Flannel [6]_ as the only multi-host container
   networking implementation. Although Flannel has become widely accepted
   for providing networking capabilities to Kubernetes-based container
   clusters, other networking tools exist and future tools may develop.

   This document proposes extending Magnum to support specifying a
   container networking implementation through a combination of user-facing
   baymodel configuration flags. Configuration parameters that are common
   across Magnum or all networking implementations will be exposed as unique
   flags. For example, a flag named network-driver can be used to instruct
   Magnum which network driver to use for implementing a baymodel
   container/pod network. network driver examples may include:

     flannel, weave, calico, midonet, netplugin, etc..

   Here is an example of creating a baymodel that uses Flannel as the
   network driver: ::

     magnum baymodel-create --name k8sbaymodel \
                            --image-id fedora-21-atomic-5 \
                            --keypair-id testkey \
                            --external-network-id 1hsdhs88sddds889 \
                            --dns-nameserver 8.8.8.8 \
                            --flavor-id m1.small \
                            --docker-volume-size 5 \
                            --coe kubernetes \
                            --network-driver flannel

   If no network-driver parameter is supplied by the user, the baymodel is
   created using the default network driver of the specified Magnum COE.
   Each COE must support a default network driver and each driver must
   provide reasonable default configurations that allow users to instantiate
   a COE without supplying labels. The default network driver for each COE
   should be consistent with existing Magnum default settings. Where current
   defaults do not exist, the defaults should be consistent with upstream
   network driver projects.

2. Each network driver supports a range of configuration parameters that
   should be observed by Magnum. This document suggests using an attribute
   named "labels" for supplying driver-specific configuration parameters.
   Labels consist of one or more arbitrary key/value pairs. Here is an
   example of using labels to change default settings of the Flannel
   network driver: ::

     magnum baymodel-create --name k8sbaymodel \
                            --image-id fedora-21-atomic-5 \
                            --keypair-id testkey \
                            --external-network-id ${NIC_ID} \
                            --dns-nameserver 8.8.8.8 \
                            --flavor-id m1.small \
                            --docker-volume-size 5 \
                            --coe kubernetes \
                            --network-driver flannel \
                            --labels flannel_network_cidr=10.0.0.0/8,\
                                     flannel_network_subnetlen=22,\
                                     flannel_backend=vxlan

   With Magnum's current implementation, this document would support
   labels for the Kubernetes COE type. However, labels are applicable
   beyond Kubernetes, as the Docker daemon, images and containers now
   support labels as a mechanism for providing custom metadata. The labels
   attribute within Magnum should be extended beyond Kubernetes pods, so a
   single mechanism can be used to pass arbitrary metadata throughout the
   entire system. A blueprint [2]_ has been registered to expand the scope
   of labels for Magnum. This document intends on adhering to the
   expand-labels-scope blueprint.

   Note: Support for daemon-labels was added in Docker 1.4.1. Labels for
   containers and images were introduced in Docker 1.6.0

   If the --network-driver flag is specified without any labels, default
   configuration values of the driver will be used by the baymodel. These
   defaults are set within the Heat template of the associated COE. Magnum
   should ignore label keys and/or values not understood by any of the
   templates during the baymodel operation.

   Magnum will continue to CRUD bays in the same way:

     magnum bay-create --name k8sbay --baymodel k8sbaymodel --node-count 1

3. Update python-magnumclient to understand the new Container Networking
   Model attributes. The client should also be updated to support passing
   the --labels flag according to the expand-labels-scope blueprint [2]_.

4. Update the conductor template definitions to support the new Container
   Networking Model attributes.

5. Refactor Heat templates to support the Magnum Container Networking Model.
   Currently, Heat templates embed Flannel-specific configuration within
   top-level templates. For example, the top-level Kubernetes Heat
   template [8]_ contains the flannel_network_subnetlen parameter. Network
   driver specific configurations should be removed from all top-level
   templates and instead be implemented in one or more template fragments.
   As it relates to container networking, top-level templates should only
   expose the labels and generalized parameters such as network-driver.
   Heat templates, template definitions and definition entry points should
   be suited for composition, allowing for a range of supported labels. This
   document intends to follow the refactor-heat-templates blueprint [3]_ to
   achieve this goal.

6. Update unit and functional tests to support the new attributes of the
   Magnum Container Networking Model.

7. The spec will not add support for natively managing container networks.
   Due to each network driver supporting different API operations, this
   document suggests that Magnum not natively manage container networks at
   this time and instead leave this job to native tools. References [4]_ [5]_
   [6]_ [7]_.
   provide additional details to common labels operations.

8. Since implementing the expand-labels-scope blueprint [2]_ may take a while,
   exposing network functionality through baymodel configuration parameters
   should be considered as an interim solution.

Alternatives
------------


1. Observe all networking configuration parameters, including labels
   within a configuration file instead of exposing the labels attribute to
   the user.

2. Only support a single networking implementation such as Flannel. Flannel
   is currently supported for the Kubernetes COE type. It can be ported to
   support the swarm COE type.

3. Add support for managing container networks. This will require adding
   abstractions for each supported network driver or creating an
   abstraction layer that covers all possible network drivers.

4. Use the Kuryr project [10]_ to provide networking to Magnum containers.
   Kuryr currently contains no documentation or code, so this alternative
   is highly unlikely if the Magnum community requires a pluggable
   container networking implementation in the near future. However, Kuryr
   could become the long-term solution for container networking within
   OpenStack. A decision should be made by the Magnum community whether
   to move forward with Magnum's own container networking model or to wait
   for Kuryr to mature. In the meantime, this document suggests the Magnum
   community become involved in the Kuryr project.

Data Model Impact
-----------------

This document adds the labels and network-driver attribute to the baymodel
database table. A migration script will be provided to support the attribute
being added. ::

    +-------------------+-----------------+---------------------------------------------+
    |    Attribute      |     Type        |             Description                     |
    +===================+=================+=============================================+
    |     labels        | JSONEncodedDict | One or more arbitrary key/value pairs       |
    +-------------------+-----------------+---------------------------------------------+
    |    network-driver |    string       | Container networking backend implementation |
    +-------------------+-----------------+---------------------------------------------+

REST API Impact
---------------

This document adds the labels and network-driver attribute to the BayModel
API class. ::

    +-------------------+-----------------+---------------------------------------------+
    |    Attribute      |     Type        |             Description                     |
    +===================+=================+=============================================+
    |     labels        | JSONEncodedDict | One or more arbitrary key/value pairs       |
    +-------------------+-----------------+---------------------------------------------+
    |    network-driver |    string       | Container networking backend implementation |
    +-------------------+-----------------+---------------------------------------------+

Security Impact
---------------

Supporting more than one network driver increases the attack
footprint of Magnum.

Notifications Impact
--------------------

None

Other End User Impact
---------------------

Most end users will never use the labels configuration flag
and simply use the default network driver and associated
configuration options. For those that wish to customize their
container networking environment, it will be important to understand
what network-driver and labels are supported, along with their
associated configuration options, capabilities, etc..

Performance Impact
------------------

Performance will depend upon the chosen network driver and its
associated configuration. For example, when creating a baymodel with
"--network-driver flannel" flag, Flannel's default configuration
will be used. If the default for Flannel is an overlay networking technique
(i.e. VXLAN), then networking performance will be less than if Flannel used
the host-gw configuration that does not perform additional packet
encapsulation to/from containers. If additional performance is required
when using this driver, Flannel's host-gw configuration option could be
exposed by the associated Heat template and instantiated through the labels
attribute.

Other Deployer Impact
---------------------

Currently, container networking and OpenStack networking are different
entities. Since no integration exists between the two, deployers/operators
will be required to manage each networking environment individually.
However, Magnum users will continue to deploy baymodels, bays, containers,
etc. without having to specify any networking parameters. This will be
accomplished by setting reasonable default parameters within the Heat
templates.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
Daneyon Hansen (danehans)

Other contributors:
Ton Ngo (Tango)
Hongbin Lu (hongbin)

Work Items
----------

1. Extend the Magnum API to support new baymodel attributes.
2. Extend the Client API to support new baymodel attributes.
3. Extend baymodel objects to support new baymodel attributes. Provide a
   database migration script for adding attributes.
4. Refactor Heat templates to support the Magnum Container Networking Model.
5. Update Conductor template definitions and definition entry points to
   support Heat template refactoring.
6. Extend unit and functional tests to support new baymodel attributes.

Dependencies
============

Although adding support for these new attributes does not depend on the
following blueprints, it's highly recommended that the Magnum Container
Networking Model be developed in concert with the blueprints to maintain
development continuity within the project.

1. Common Plugin Framework Blueprint [1]_.

2. Expand the Scope of Labels Blueprint [9]_.

3. Refactor Heat Templates, Definitions and Entry Points Blueprint [3]_.

Testing
=======

Each commit will be accompanied with unit tests. There will also be
functional tests which will be used as part of a cross-functional gate
test for Magnum.

Documentation Impact
====================

The Magnum Developer Quickstart document will be updated to support the
configuration flags introduced by this document. Additionally, background
information on how to use these flags will be included.

References
==========

.. [1] https://blueprints.launchpad.net/magnum/+spec/common-plugin-framework
.. [2] http://docs.openstack.org/developer/magnum/
.. [3] https://blueprints.launchpad.net/magnum/+spec/refactor-heat-templates
.. [4] https://github.com/docker/libnetwork/blob/master/docs/design.md
.. [5] https://github.com/GoogleCloudPlatform/kubernetes/blob/master/docs/design/networking.md
.. [6] https://github.com/coreos/flannel
.. [7] https://github.com/coreos/rkt/blob/master/Documentation/networking.md
.. [8] https://github.com/openstack/magnum/blob/master/magnum/templates/kubernetes/kubecluster.yaml
.. [9] https://blueprints.launchpad.net/magnum/+spec/expand-labels-scope
.. [10] https://github.com/openstack/kuryr
