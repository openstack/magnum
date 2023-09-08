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
* **Source:** https://opendev.org/openstack/magnum
* **Blueprints:** https://blueprints.launchpad.net/magnum
* **Bugs:** https://bugs.launchpad.net/magnum
* **REST Client:** https://opendev.org/openstack/python-magnumclient

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
* Integration with Kubernetes for backend container technology
* Integration with Keystone for multi-tenant security
* Integration with Neutron for Kubernetes multi-tenancy network security
* Integration with Cinder to provide volume service for containers

Installation Guide
==================
.. toctree::
   :maxdepth: 1

   install/index

User Documentation
==================
.. toctree::
   :maxdepth: 1

   user/index
   user/monitoring.rst
   user/glossary.rst

Contributor Guide
=================
.. toctree::
   :maxdepth: 1

   contributor/index

Admin Guide
===========
.. toctree::
   :maxdepth: 1

   admin/index

CLI Guide
=========
.. toctree::
   :maxdepth: 1

   cli/index

Sample Configurations and Policies
==================================

.. toctree::
   :maxdepth: 1

   configuration/index

Work In Progress
================

.. toctree::
   :maxdepth: 1

   admin/troubleshooting-guide.rst
   user/index.rst
   admin/configuring.rst
