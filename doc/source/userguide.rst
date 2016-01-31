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

Pod
  When using the Kubernetes container orchestration engine, a pod is the
  smallest deployable unit that can be created and managed. A pod is a
  co-located group of application containers that run with a shared context.
  When using Magnum, pods are created and managed within bays. Refer to the
  `Kubernetes User Guide
  <http://kubernetes.io/v1.0/docs/user-guide/pods.html>`__ for more
  information.

Replication controller
  A replication controller is used to ensure that at any given time a certain
  number of replicas of a pod are running. Pods are automatically created and
  deleted by the replication controller as necessary based on a template to
  ensure that the defined number of replicas exist. Refer to the `Kubernetes
  User Guide
  <http://kubernetes.io/v1.0/docs/user-guide/replication-controller.html>`__
  for more information.

Service
  A service is an additional layer of abstraction provided by the Kubernetes
  container orchestration engine which defines a logical set of pods and a
  policy for accessing them. This is useful because pods are created and
  deleted by a replication controller, for example, other pods needing to
  discover them can do so via the service abstraction. Refer to the
  `Kubernetes User Guide
  <http://kubernetes.io/v1.0/docs/user-guide/services.html>`__ for more
  information.

========
Overview
========
*To be filled in*

Magnum rationale, concept, compelling features

Bay Model
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
*To be filled in*

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

