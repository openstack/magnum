..
      Copyright 2014-2015 OpenStack Foundation
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

============================================
Welcome to Magnum's Developer Documentation!
============================================

Magnum is an OpenStack project which offers container orchestration engines
for deploying and managing containers as first class resources in OpenStack.

* **Free software:** under the `Apache license <http://www.apache.org/licenses/LICENSE-2.0>`_
* **Source:** http://git.openstack.org/cgit/openstack/magnum
* **Blueprints:** https://blueprints.launchpad.net/magnum
* **Bugs:** http://bugs.launchpad.net/magnum
* **REST Client:** http://git.openstack.org/cgit/openstack/python-magnumclient

Architecture
============

There are several different types of objects in the magnum system:

* **Cluster:** A collection of node objects where work is scheduled
* **ClusterTemplate:** An object stores template information about the cluster
  which is used to create new clusters consistently

Two binaries work together to compose the magnum system.  The first binary
(accessed by the python-magnumclient code) is the magnum-api REST server.  The
REST server may run as one process or multiple processes.  When a REST request
is sent to the client API, the request is sent via AMQP to the
magnum-conductor process.  The REST server is horizontally scalable.  At this
time, the conductor is limited to one process, but we intend to add horizontal
scalability to the conductor as well.

Features
========

* Abstractions for Clusters
* Integration with Kubernetes, Swarm, Mesos for backend container technology
* Integration with Keystone for multi-tenant security
* Integration with Neutron for Kubernetes multi-tenancy network security
* Integration with Cinder to provide volume service for containers

Developer Info
==============

.. toctree::
   :maxdepth: 1

   dev/quickstart
   policies.rst
   dev/cluster-type-definition.rst
   dev/kubernetes-load-balancer.rst
   dev/functional-test.rst
   dev/reno.rst
   dev/api_microversion.rst
   api_microversion_history.rst
   magnum-proxy.rst
   contributing
   heat-templates
   objects
   gmr.rst

Work In Progress
================

.. toctree::
   :maxdepth: 1

   troubleshooting-guide.rst
   userguide.rst
   configuring.rst
   install-guide-from-source.rst
