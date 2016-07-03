..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================
Magnum Container Volume Integration Model
=========================================

Launchpad Blueprint:

https://blueprints.launchpad.net/magnum/+spec/magnum-integrate-with-cinder

Storage is a key part of any computing system. Containers in particular have
the interesting characteristic that local storage by default is ephemeral:
any changes to the file system disappear when the container is deleted. This
introduces the need for persistent storage to retain and share data between
containers, and this is currently an active area of development in all
container orchestration engines (COE).

As the component in OpenStack for managing COE's, Magnum must fully enable the
features for persistent storage in the COE's. To achieve this goal, we propose
in this specification to generalize the process for utilizing persistent
storage with containers so that it is applicable for different bay types.
Despite the complexity, we aim to maintain a good user experience by a simple
abstraction for working with various volume capabilities. For the rest of this
specification, we will use the term Volume to refer to persistent storage, and
Volume Driver as the plugin in a COE to support the particular persistent
storage.

Problem Description
===================

Containers requires full life cycle management such as create, run, stop,
delete,... and a key operation is to manage the data - making the data
persistent, reusing the data, sharing data between containers, etc.
In this area, the support for container volume is undergoing rapid change
to bring more integration with open source software and third party
storage solutions.

A clear evidence of this growth is the many plugin volume drivers [1]_ [4]_
such as NFS, GlusterFS, EBS, etc. They provide different functionality, use
different storage backend and have different requirements. The COE's are
naturally motivated to be flexible and allow as many choices as possible for
the users with respect to the storage backend. Since Magnum's role is to
support the COE's within OpenStack, the goal is to be transparent and enable
these same storage backends for the COE's through the COE's lifecycle
operation.

Currently, Magnum provides limited support for managing container volume
. The only option available is to specify the docker-volume-size for a
pre-allocated block storage in the COE to host the containers. Magnum
instantiates container volumes through Heat templates, exposing no other
mechanism to configure and operate on volumes. In practice, some users
require the ability to manage volumes easily in the COEs .

Note that we are not proposing to create a new volume management interface
in Magnum. After the users create the baymodel and bays, we assume that the
users would manage the volumes through existing techniques:

1. Log in to the COE, use COE specific CLI or GUI to manage volumes.

2. Use native tools to manage volumes.

The initial implementation will focus on OpenStack Cinder integration; as
other alternatives become available, contributors are welcome through
3rd-party maintained projects.


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

Volume
  storage that is persistent

Volume plugin
  COE specific code that supports the functionality of a type of volume.

Additional Magnum definitions can be found in the Magnum Developer
documentation[7]_ .

Use Cases
----------

This document does not intend to address all use cases. We list below a number
of use cases for 3 different roles; they should be useful as reference for the
long-term development of the Magnum Container Volume Integration.

As a User:

As mentioned above, our goal is to preserve the user experience specific to
the COE in managing the volumes.  Therefore, we expect the use cases for the
users will be fulfilled by the COE's themselves; Magnum will simply ensure
that the necessary supports are in place.

1. I need to easily create volume for containers to use as persistent
   data store.

2. I need the ability to create and mount a data volume container for cross
   container sharing.

3. I need to mount a host directory as a data volume.

4. I need to easily attach a known volume to container to use the
   existing data.

5. I need the ability to delete the volume.

6. I need to list and view the details of the volume

7. I need to modify the volume.


As a CSP:

1. I need to easily deploy a bay for consumption by users. The bay must
   support the following:

   A. One or more hosts to run containers.
   B. The ability to choose between virtual or physical hosts to
      run containers.
   C. The ability to automatically enable volume plugins to containers.

2. I need to provide clustering options that support different volume plugins
   per COE.

3. After deploying my initial cluster, I need the ability to provide lifecycle
   management, including:

   A. The ability to add/remove volumes that containers used.
   B. The ability to add/remove nodes within the cluster with the necessary
      adjustment to the volumes

As a CP:

1. I need to easily and reliably add the Magnum service to my existing
   OpenStack cloud environment.

2. I need to make the Magnum services highly-available.

3. I need to make Magnum services highly performant.

4. I need to easily scale-out Magnum services as needed.


Proposed Changes
================

We propose extending Magnum as follows.



1. The new attribute volume-driver for a baymodel specifies the volume backend
   driver to use when deploying a bay.

  Volume drivers may include:

     rexray, flocker, nfs, glusterfs, etc..

  Here is an example of creating a Docker Swarm baymodel that uses rexray [5]_
  [6]_ as the volume driver: ::


     magnum baymodel-create --name swarmbaymodel \
                            --image-id fedora-21-atomic-5 \
                            --keypair-id testkey \
                            --external-network-id 1hsdhs88sddds889 \
                            --dns-nameserver 8.8.8.8 \
                            --flavor-id m1.small \
                            --docker-volume-size 5 \
                            --coe swarm\
                            --network-driver flannel \
                            --volume-driver rexray

  When a Swarm bay is created with this bay model, the REX-Ray storage
  subsystem will be installed, configured and started on the Swarm nodes,
  then the REX-Ray volume plugin will be registered in Docker. When a container
  is created with rexray as the volume driver, the container will have full
  access to the REX-Ray capabilities such as creating, mounting, deleting
  volumes [6]_. REX-Ray in turn will interface with Cinder to manage the
  volumes in OpenStack.

  Here is an example of creating a Kubernetes baymodel that uses Cinder [2]_
  [3]_ as the volume driver: ::

    magnum baymodel-create --name k8sbaymodel \
                            --image-id fedora-21-atomic-5 \
                            --keypair-id testkey \
                            --external-network-id 1hsdhs88sddds889 \
                            --dns-nameserver 8.8.8.8 \
                            --flavor-id m1.small \
                            --docker-volume-size 5 \
                            --coe kubernetes\
                            --network-driver flannel \
                            --volume-driver cinder

  When the Kubernetes bay is created using this bay model, the kubelet will be
  configured so that an existing Cinder volume can be mounted in a pod by
  specifying the volume ID in the pod manifest as follows: ::

    volumes:
    - name: mysql-persistent-storage
      cinder:
        volumeID: bd82f7e2-wece-4c01-a505-4acf60b07f4a
        fsType: ext4



Here is an example of creating a mesos baymodel that uses rexray as the
volume driver: ::

    magnum baymodel-create --name mesosbaymodel \
                            --image-id ubuntu-mesos\
                            --keypair-id testkey \
                            --external-network-id 1hsdhs88sddds889 \
                            --dns-nameserver 8.8.8.8 \
                            --flavor-id m1.small \
                            --coe mesos\
                            --network-driver docker \
                            --volume-driver rexray

When the mesos bay is created using this bay model, the mesos bay will be
configured so that an existing Cinder volume can be mounted in a container
by configuring the parameters to mount the cinder volume in the json file. ::

    "parameters": [
       { "key": "volume-driver", "value": "rexray" },
       { "key": "volume", "value": "redisdata:/data" }
    ]

If no volume-driver parameter is supplied by the user, the baymodel is
created using the default volume driver of the particular COE.
Magnum will provide a default volume driver for each COE as well as the
reasonable default configuration for each driver so that
users can instantiate a COE without supplying a volume driver and
associated labels. Generally the defaults should be consistent with upstream
volume driver projects.

2. Each volume driver supports a range of configuration parameters that are
   handled by the "labels" attribute.

  Labels consist of one or more arbitrary key/value pairs.
  Here is an example of using labels to choose ¡°storage-provider¡± for
  rexray driver.
  Volume driver: ::

     magnum baymodel-create --name k8sbaymodel \
                            --image-id fedora-21-atomic-5 \
                            --keypair-id testkey \
                            --external-network-id ${NIC_ID} \
                            --dns-nameserver 8.8.8.8 \
                            --flavor-id m1.small \
                            --docker-volume-size 5 \
                            --coe kubernetes \
                            --volume-driver rexray \
                            --labels storage-provider=openstack \
                                [, key2=value2...]


  If the --volume-driver flag is specified without any labels, default
  configuration values of the driver will be used by the baymodel.

  Magnum will validate the labels together with the driver specified before
  creating the bay and will return an error if the validation fails.

  Magnum will continue to CRUD bays in the same way:

     magnum bay-create --name k8sbay --baymodel k8sbaymodel --node-count 1

3. Update python-magnumclient to handle the new container volume-
   driver attributes.

4. Update the conductor template definitions to support the new container
   volume-driver model attributes.

5. Refactor Heat templates to support the Magnum volume driver plugin.
   Configurations specific to volume drivers should be
   implemented in one or more template fragments.
   Top-level templates should only
   expose the labels and generalized parameters such as volume-driver.
   Heat templates, template definitions and definition entry points should
   be designed for composition, allowing for a range of supported labels.

6. Update unit and functional tests to support the new attributes of the
   Magnum container volume driver.

7. Preserve the user experience by ensuring that any operation on volume will
   be identical between a COE deployed by Magnum and a COE deployed by other
   methods.


Alternatives
------------

1. Without the support proposed, the user will need to manually enable and
   configure the volume plugin.  This will require the user to log into the
   nodes in the cluster and understand the low level infrastructure of the
   cluster as deployed by the heat templates.
2. We can add full support for managing container volume in Magnum user
   interface itself. This will require adding abstractions for each supported
   COE volume plugins driver or creating an abstraction layer that covers all
   possible COE volume drivers.

Data Model Impact
-----------------

This document adds the volume-driver attribute to the baymodel
database table. A migration script will be provided to support the attribute
being added. ::

    +-------------------+-----------------+---------------------------------------------+
    |    Attribute      |     Type        |             Description                     |
    +===================+=================+=============================================+
    +-------------------+-----------------+---------------------------------------------+
    | volume-driver     |    string       | Container volume backend implementation     |
    +-------------------+-----------------+---------------------------------------------+

REST API Impact
---------------

This document adds volume-driver attribute to the BayModel
API class. ::

    +-------------------+-----------------+---------------------------------------------+
    |    Attribute      |     Type        |             Description                     |
    +===================+=================+=============================================+
    +-------------------+-----------------+---------------------------------------------+
    | volume-driver     |    string       | Container volume backend implementation     |
    +-------------------+-----------------+---------------------------------------------+

Security Impact
---------------

Supporting volume drivers can potentially increase the attack surface
on containers.

Notifications Impact
--------------------

None

Other End User Impact
---------------------

There is no impact if the user does not use a volume driver.
We anticipate that most users would not use the labels for volume
and would simply use the default volume driver and associated
configuration options. For those who wish to customize their
container volume driver environment, it will be important to understand
what volume-driver and labels are supported, along with their
associated configuration options, capabilities, etc..

Performance Impact
------------------

There is no impact if the user does not use a volume driver.
When a volume driver is used, the performance will depend upon the specific
volume driver and its associated storage backends.  For example, Kubernetes
supports Cinder and awsEBS; the two types of volumes can have different
performance.

An example of the second case is a docker swarm bay with
"--volume-driver rexray" where the rexray driver's storage provider is
OpenStack cinder. The resulting performance for container may vary depending
on the storage backends. As listed in [8]_ , Cinder supports many storage
drivers. Besides this, different container volume driver can also cause
performance variance.


High-Availability Impact
------------------------------



+-----------------+--------------------+--------------------------+
|       COE       |      Master HA     |   Pod/Container/App  HA  |
+=================+====================+==========================+
|    Kubernetes   |         No         |          Yes             |
+-----------------+--------------------+--------------------------+
|   Docker Swarm  |         No         |          Yes             |
+-----------------+--------------------+--------------------------+
|       Mesos     |         No         |          No              |
+-----------------+--------------------+--------------------------+

"No" means that  the volume doesn't affect the high-availability.
"Yes" means that the volume affect the high-availability.

Kubernetes does support pod high-availability through the replication
controller, however, this doesn't work when a pod with volume attached
fails. Refer the link [11]_  for details.

Docker swarm doesn't support the containers rescheduling when a node fails, so
volume can not be automatically detached by volume driver. Refer the
link [12]_  for details.

Mesos supports the application high-availability when a node fails, which
means application would be started on new node, and volumes can be
automatically attached to the new node by the volume driver.

Other Deployer Impact
---------------------

Currently, both Kubernetes and Docker community have supported some volume
plugins. The changes proposed will enable these volume plugins in Magnum.
However, Magnum users will be able to continue to deploy baymodels, bays,
containers, etc. without having to specify any parameters for volume.
This will be accomplished by setting reasonable default parameters within
the Heat templates.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:

- Kai Qiang Wu (Kennan)

Other contributors:

- Qun Wang (wangqun)
- Ton Ngo (Tango)


Work Items
----------

1. Extend the Magnum API to support new baymodel attributes.
2. Extend the Client API to support new baymodel attributes.
3. Extend baymodel objects to support new baymodel attributes. Provide a
   database migration script for adding attributes.
4. Refactor Heat templates to support the Magnum container volume driver.
5. Update Conductor template definitions and definition entry points to
   support Heat template refactoring.
6. Extend unit and functional tests to support new baymodel attributes.
7. Document how to use the volume drivers with examples.

Dependencies
============

Although adding support for these new attributes does not depend on the
following blueprints, it's highly recommended that the Magnum Container
Networking Model be developed in concert with the blueprints to maintain
development continuity within the project.
https://blueprints.launchpad.net/magnum/+spec/ubuntu-image-build

Kubernetes with cinder support need Kubernetes version >= 1.1.1
Swarm need version >= 1.8.3, as Kubernetes 1.1.1 upgraded to that version

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

.. [1] http://kubernetes.io/v1.1/docs/user-guide/volumes.html
.. [2] http://kubernetes.io/v1.1/examples/mysql-cinder-pd/
.. [3] https://github.com/kubernetes/kubernetes/tree/master/pkg/volume/cinder
.. [4] http://docs.docker.com/engine/extend/plugins/
.. [5] https://github.com/emccode/rexray
.. [6] http://rexray.readthedocs.org/en/stable/user-guide/storage-providers/openstack
.. [7] http://docs.openstack.org/developer/magnum/
.. [8] http://docs.openstack.org/liberty/config-reference/content/section_volume-drivers.html
.. [9] http://docs.openstack.org/admin-guide-cloud/blockstorage_multi_backend.html#
.. [10] http://docs.openstack.org/user-guide-admin/dashboard_manage_volumes.html
.. [11] https://github.com/kubernetes/kubernetes/issues/14642
.. [12] https://github.com/docker/swarm/issues/1488
