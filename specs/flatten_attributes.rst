..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
   License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================================
Flatten Cluster and ClusterTemplate Attributes
==============================================

Launchpad blueprint:

https://blueprints.launchpad.net/magnum/+spec/flatten-attributes

Including all user-specified attributes in Clusters and ClusterTemplates will
increase flexibility for users during ClusterTemplate definition and Cluster
creation.

Note that this spec only deals with changes to magnum's data model, not
API changes. Please see the NodeGroup spec for these details:

https://blueprints.launchpad.net/magnum/+spec/nodegroups


Problem Description
===================

Clusters rely on attributes from both the magnum Cluster and ClusterTemplate
resources, but the line between attributes that belong in one or the other is
not well-defined. Most attributes make sense where they are, but there will be
times that users will want to capture different attributes in a ClusterTemplate
or specify them during cluster creation. The current system has little
flexibility, with only keypairs able to exist in either.

Use Cases
=========

1. Users that want to specify attributes in ClusterTemplates that they can't
   right now, such as node count.

2. Users that want to specify/override attributes when creating a Cluster that
   they can't right now, since attributes that come from ClusterTemplates are
   currently unchangeable.


Proposed Change
===============

Give both Cluster and ClusterTemplate a copy of all user-specifed attributes.

The python object for ClusterTemplate will work much the same, just with more
attributes available.

The python object for Cluster will no longer (and should not) need to use
attributes from its ClusterTemplate, since it will have all the attributes it
needs and it is possible that some attributes will have been overridden in the
cluster-create request.

For example, `cluster.cluster_template.fixed_network` will become
`cluster.fixed_network`.


Alternatives
============

The shared fields can be added to the existing Cluster and ClusterTemplate
tables. This achieves the same effect, but brings with it the burden of
maintaining two sets of the same fields in different tables.


Data Model Impact
=================

A new database table, ClusterAttributes, will be added. The shared fields will
be moved to this table.

A foreign key to ClusterAttributes will be added to the Cluster and
ClusterTemplate tables. The relationship between Cluster and ClusterAttributes
is one-to-one. The same is true between ClusterTemplate and ClusterAttributes.
That is, Clusters and ClusterTemplates have their own separate copy of cluster
attributes.

Database tables before, with fields that will be shared marked:

    cluster:

    =================== =======
    Attribute           Shared?
    ------------------- -------
    id
    uuid
    project_id
    user_id
    name
    stack_id
    status
    status_reason
    api_address
    trust_id
    trustee_username
    trustee_user_id
    trustee_password
    coe_version
    container_version
    ca_cert_ref
    magnum_cert_ref
    cluster_template_id
    node_addresses
    master_addresses
    create_timeout      Yes
    discovery_url       Yes
    node_count          Yes
    master_count        Yes
    keypair             Yes
    =================== =======

    cluster_template:

    ===================== =======
    Attribute             Shared?
    --------------------- -------
    id
    uuid
    project_id
    user_id
    name
    public
    apiserver_port        Yes
    keypair_id            Yes
    labels                Yes
    external_network_id   Yes
    fixed_network         Yes
    fixed_subnet          Yes
    network_driver        Yes
    volume_driver         Yes
    dns_nameserver        Yes
    coe                   Yes
    http_proxy            Yes
    https_proxy           Yes
    no_proxy              Yes
    registry_enabled      Yes
    tls_disabled          Yes
    insecure_registry     Yes
    master_lb_enabled     Yes
    floating_ip_enabled   Yes
    image_id              Yes
    flavor_id             Yes
    docker_volume_size    Yes
    docker_storage_driver Yes
    cluster_distro        Yes
    server_type           Yes
    master_flavor_id      Yes
    ===================== =======

Database tables after:

    cluster:
     - id
     - uuid
     - project_id
     - user_id
     - name
     - stack_id
     - status
     - status_reason
     - api_address
     - trust_id
     - trustee_username
     - trustee_user_id
     - trustee_password
     - coe_version
     - container_version
     - ca_cert_ref
     - magnum_cert_ref
     - cluster_template_id
     - node_addresses
     - master_addresses
     - FK to cluster_attributes (new)

    cluster_template:
     - id
     - uuid
     - project_id
     - user_id
     - name
     - public
     - FK to cluster_attributes (new)

    cluster_attributes:
     - id (new)
     - apiserver_port
     - create_timeout
     - discovery_url
     - node_count
     - master_count
     - keypair_id
     - labels
     - external_network_id
     - fixed_network
     - fixed_subnet
     - network_driver
     - volume_driver
     - dns_nameserver
     - coe
     - http_proxy
     - https_proxy
     - no_proxy
     - registry_enabled
     - tls_disabled
     - insecure_registry
     - master_lb_enabled
     - floating_ip_enabled
     - image_id
     - flavor_id
     - docker_volume_size
     - docker_storage_driver
     - cluster_distro
     - server_type
     - master_flavor_id


REST API Impact
===============

None

Security Impact
===============

None identified


Notifications Impact
====================

None


Other End-user Impact
=====================

None


Performance Impact
==================

Negligible. Two-table joins should have minimal performance impact. There may
be cases where only the Cluster/ClusterTemplate or ClusterAttributes table
needs to be queried/written that will further offset the small performance
impact or even improve performance since these operations will be dealing with
narrower tables.


Other Deployer Impact
=====================

This change will require a database migration.


Developer Impact
================

Developers will not have to remember which attributes come from ClusterTemplate
because they will all be available in Cluster.


Implementation
==============

Assignee(s)
-----------

Spyros Trigazis (strigazi)


Work Items
----------

1. Database migration to add ClusterAttributes table.

2. Updates to python code.


Dependencies
============

None


Testing
=======

Unit tests will need to be updated, but functional tests will still pass as
this is an internal change.


Documentation Impact
====================

None for this spec, as the changes are internal.


References
==========

None
