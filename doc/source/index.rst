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

* **Bay:** A collection of node objects where work is scheduled
* **BayModel:** An object stores template information about the bay which is
  used to create new bays consistently
* **Node:** A baremetal or virtual machine where work executes
* **Pod:** A collection of containers running on one physical or virtual
  machine
* **Service:** An abstraction which defines a logical set of pods and a policy
  by which to access them
* **ReplicationController:** An abstraction for managing a group of pods to
  ensure a specified number of resources are running
* **Container:** A Docker container

Two binaries work together to compose the magnum system.  The first binary
(accessed by the python-magnumclient code) is the magnum-api REST server.  The
REST server may run as one process or multiple processes.  When a REST request
is sent to the client API, the request is sent via AMQP to the
magnum-conductor process.  The REST server is horizontally scalable.  At this
time, the conductor is limited to one process, but we intend to add horizontal
scalability to the conductor as well.

The magnum-conductor process runs on a controller machine and connects to a
Kubernetes or Docker REST API endpoint.  The Kubernetes and Docker REST API
endpoints are managed by the bay object.

When service or pod objects are created, Kubernetes may be directly contacted
via the Kubernetes REST API.  When container objects are acted upon, the
Docker REST API may be directly contacted.

Features
========

* Abstractions for bays, containers, nodes, pods, replication controllers, and
  services
* Integration with Kubernetes and Docker for backend container technology
* Integration with Keystone for multi-tenant security
* Integration with Neutron for Kubernetes multi-tenancy network security

Developer Info
==============

.. toctree::
   :maxdepth: 1

   dev/dev-quickstart
   dev/dev-manual-devstack
   dev/dev-build-atomic-image.rst
   dev/dev-kubernetes-load-balancer.rst
   contributing
   heat-templates
   objects
