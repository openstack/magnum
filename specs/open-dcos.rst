..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================
Magnum and Open DC/OS Integration
=================================

Launchpad Blueprint:

https://blueprints.launchpad.net/magnum/+spec/mesos-dcos

Open DC/OS [1]_ is a distributed operating system based on the Apache Mesos
distributed systems kernel. It enables the management of multiple machines as
if they were a single computer. It automates resource management, schedules
process placement, facilitates inter-process communication, and simplifies
the installation and management of distributed services. Its included web
interface and available command-line interface (CLI) facilitate remote
management and monitoring of the cluster and its services.

Open DC/OS now supports both docker containerizer and mesos containerizer.
The mesos containerizer support both docker and AppC image spec, the mesos
containerizer can manage docker containers well even if docker daemon is not
running.

End user can install Open DC/OS with different ways, such as vagrant, cloud,
local etc. For cloud, the Open DC/OS only supports AWS now, end user can
deploy a DC/OS cluster quickly with a template. For local install, there
are many steps to install a Open DC/OS cluster.

Problem Description
===================

COEs (Container Orchestration Engines) are the first class citizen in Magnum,
there are different COEs in Magnum now including Kubernetes, Swarm and Mesos.
All of those COEs are focusing docker container management, the problem is
that the concept of container is not only limited in docker container, but
also others, such as AppC, linux container etc, Open DC/OS is planning to
support different containers by leveraging Mesos unified container feature
and the Open DC/OS has a better management console for container orchestration.

Currently, Magnum provides limited support for Mesos Bay as there is only one
framework named as Marathon running on top of Mesos. Compared with Open DC/OS,
the current Mesos Bay lack the following features:

1. App Store for application management. The Open DC/OS has a universe to
   provide app store functions.

2. Different container technology support. The Open DC/OS support different
   container technologies, such as docker, AppC etc, and may introduce OCI
   support in future. Introducing Open DC/OS Bay can enable Magnum to support
   more container technologies.

3. Better external storage integration. The Open DC/OS is planning to introduce
   docker volume isolator support in next release, the docker volume isolator
   is leveraging docker volume driver API to integrate with 3rd party
   distributed storage platforms, such as OpenStack Cinder, GlusterFS, Ceph
   etc.

4. Better network management. The Open DC/OS is planning to introduce CNI
   network isolator in next release, the CNI network isolator is leveraging CNI
   technologies to manage network for containers.

5. Loosely coupled with docker daemon. The Open DC/OS can work well for docker
   container even if docker daemon is not running. The docker daemon now have
   some issues in large scale cluster, so this approach avoids the limitation
   of the docker daemon but still can enable end user get some docker features
   in large scale cluster.


Proposed Changes
================

We propose extending Magnum as follows.

1. Leverage bay driver work and structure this new COE as a bay driver.

2. Leverage mesos-slave-flags [3]_ to customize Open DC/OS.

   Here is an example of creating an Open DC/OS baymodel that uses
   docker/volume as isolator, linux as launcher and docker as image
   provider: ::

     magnum baymodel-create --name dcosbaymodel \
                            --image-id dcos-centos-7.2 \
                            --keypair-id testkey \
                            --external-network-id 1hsdhs88sddds889 \
                            --dns-nameserver 8.8.8.8 \
                            --flavor-id m1.small \
                            --docker-volume-size 5 \
                            --coe dcos \
                            --labels isolation=docker/volume,\
                                     launcher=linux, \
                                     image_providers=docker

   Magnum will validate the labels together with the driver specified before
   creating the bay and will return an error if the validation fails.

   Magnum will continue to CRUD bays in the same way:

     magnum bay-create --name dcosbay --baymodel dcosbaymodel --node-count 1

3. Keep the old Mesos Bay and add a new Open DC/OS Bay. Once the Open DC/OS Bay
   is stable, deprecate the Mesos Bay.

4. Update unit and functional tests to support Open DC/OS Bay, it is also an
   option to verify the Open DC/OS Bay in gate.

5. Preserve the user experience by ensuring that any operation on Open DC/OS
   Bay will be identical between a COE deployed by Magnum and a COE deployed
   by other methods.


REST API Impact
---------------

There will be no REST API exposed from Magnum for end user to operate Open
DC/OS, end user can logon to Open DC/OS dashboard or call Open DC/OS REST
API directly to manage the containers or the applications.

Implementation
==============

Assignee(s)
-----------

Primary assignee:

- Guang Ya Liu (jay-lau-513)

Other contributors:

- Qun Wang (wangqun)
- Gao Jin Cao


Work Items
----------

1. Build VM image for Open DC/OS Bay.
2. Add Open DC/OS Bay driver.
3. Add Heat template for Open DC/OS Bay.
4. Add Open DC/OS Bay monitor.
5. Document how to use the Open DC/OS Bay.

Dependencies
============

1. This blueprint will focus on running on Open DC/OS in CentOS 7.2.

2. Depend on blueprint

https://blueprints.launchpad.net/magnum/+spec/mesos-slave-flags

Testing
=======

Each commit will be accompanied with unit tests. There will also be
functional tests which will be used as part of a cross-functional gate
test for Magnum.

Documentation Impact
====================

The Magnum Developer Quickstart document will be updated to support the Open
DC/OS Bay introduced by including a short example and a full documentation
with all the explanation for the labels in the user guide. Additionally,
background information on how to use the Open DC/OS Bay will be included.

References
==========

.. [1] https://dcos.io/docs/1.7/overview/what-is-dcos/
.. [2] https://dcos.io/install/
.. [3] https://blueprints.launchpad.net/magnum/+spec/mesos-slave-flags
