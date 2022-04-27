.. _glossary:

========
Glossary
========

Magnum Terminology
~~~~~~~~~~~~~~~~~~

.. glossary::

   Cluster (previously Bay)
     A cluster is the construct in which Magnum launches container orchestration
     engines. After a cluster has been created the user is able to add containers
     to it either directly, or in the case of the Kubernetes container
     orchestration engine within pods - a logical construct specific to that
     implementation. A cluster is created based on a ClusterTemplate.

   ClusterTemplate (previously BayModel)
     A ClusterTemplate in Magnum is roughly equivalent to a flavor in Nova. It
     acts as a template that defines options such as the container orchestration
     engine, keypair and image for use when Magnum is creating clusters using
     the given ClusterTemplate.

   Container Orchestration Engine (COE)
     A container orchestration engine manages the lifecycle of one or more
     containers, logically represented in Magnum as a cluster. Magnum supports a
     number of container orchestration engines, each with their own pros and cons,
     including Docker Swarm and Kubernetes.

   Labels
     Labels is a general method to specify supplemental parameters that are
     specific to certain COE or associated with certain options.  Their
     format is key/value pair and their meaning is interpreted by the
     drivers that uses them.

   Cluster Drivers
     A cluster driver is a collection of python code, heat templates, scripts,
     images, and documents for a particular COE on a particular distro. Magnum
     presents the concept of ClusterTemplates and clusters. The implementation
     for a particular cluster type is provided by the cluster driver. In other
     words, the cluster driver provisions and manages the infrastructure for the
     COE.

Kubernetes Terminology
~~~~~~~~~~~~~~~~~~~~~~

Kubernetes uses a range of terminology that we refer to in this guide. We
define these common terms for your reference:

.. glossary::

   Pod
     When using the Kubernetes container orchestration engine, a pod is the
     smallest deployable unit that can be created and managed. A pod is a
     co-located group of application containers that run with a shared context.
     When using Magnum, pods are created and managed within clusters. Refer to the
     `pods section <https://kubernetes.io/docs/concepts/workloads/pods/pod-overview/>`_ in
     `Kubernetes Tasks`_ for more information.

   Replication controller
     A replication controller is used to ensure that at any given time a certain
     number of replicas of a pod are running. Pods are automatically created and
     deleted by the replication controller as necessary based on a template to
     ensure that the defined number of replicas exist. Refer to the `replication
     controller section
     <https://kubernetes.io/docs/tasks/run-application/rolling-update-replication-controller/>`_ in
     the `Kubernetes Tasks`_ for more information.

   Service
     A service is an additional layer of abstraction provided by the Kubernetes
     container orchestration engine which defines a logical set of pods and a
     policy for accessing them. This is useful because pods are created and
     deleted by a replication controller, for example, other pods needing to
     discover them can do so via the service abstraction. Refer to the
     `services section
     <https://kubernetes.io/docs/concepts/services-networking/service/>`_ in
     `Kubernetes Concepts`_ for more information.

.. _Kubernetes Tasks: https://kubernetes.io/docs/tasks/
.. _Kubernetes Concepts: https://kubernetes.io/docs/concepts/
