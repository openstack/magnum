============================
Magnum Troubleshooting Guide
============================

This guide is intended for users who use Magnum to deploy and manage
clusters of hosts for a Container Orchestration Engine.  It describes
common failure conditions and techniques for troubleshooting.  To help
the users quickly identify the relevant information, the guide is
organized as a list of failure symptoms: each has some suggestions
with pointers to the details for troubleshooting.


================
Failure symptoms
================

My bay-create takes a really long time
  If you are using devstack on a small VM, bay-create will take a long
  time and may eventually fail because of insufficient resources.
  Another possible reason is that a process on one of the nodes is hung
  and heat is still waiting on the signal.  In this case, it will eventually
  fail with a timeout, but since heat has a long default timeout, you can
  look at the `heat stacks`_ and check the WaitConditionHandle resources.

Kubernetes bay-create fails
  Check the `heat stacks`_, log into the master nodes and check the
  `Kubernetes services`_ and `etcd service`_.

Swarm bay-create fails
  Check the `heat stacks`_, log into the master nodes and check the `Swarm
  services`_ and `etcd service`_.

Mesos bay-create fails
  Check the `heat stacks`_, log into the master nodes and check the `Mesos
  services`_.

I get the error "Timed out waiting for a reply" when deploying a pod
  Verify the `Kubernetes services`_ and `etcd service`_ are running on the
  master nodes.

I deploy pods on Kubernetes bay but the status stays "Pending"
  The pod status is "Pending" while the Docker image is being downloaded,
  so if the status does not change for a long time, log into the minion
  node and check for `Cluster internet access`_.

Swarm bay is created successfully but I cannot deploy containers
  Check the `Swarm services`_ and `etcd service`_ on the master nodes.

Mesos bay is created successfully but I cannot deploy containers on Marathon
  Check the `Mesos services`_ on the master node.

I get a "Protocol violation" error when deploying a container
  For Kubernetes, check the `Kubernetes services`_ to verify that
  kube-apiserver is running to accept the request.
  Check `TLS`_ and `Barbican service`_.

My bay-create fails with a resource error on docker_volume
  Check for available volume space on Cinder and the `request volume
  size`_ in the heat template.
  Run "nova volume-list" to check the volume status.


=======================
Troubleshooting details
=======================

Heat stacks
-----------
*To be filled in*

A bay is deployed by a set of heat stacks:  one top level stack and several
nested stack.  The stack names are prefixed with the bay name and the nested
stack names contain descriptive internal names like *kube_masters*,
*kube_minions*.

To list the status of all the stacks for a bay:

    heat stack-list -n | grep *bay-name*

If the bay has failed, then one or more of the heat stacks would have failed.
From the stack list above, look for the stacks that failed, then
look for the particular resource(s) that failed in the failed stack by:

    heat resource-list *failed-stack-name* | grep "FAILED"

The resource_type of the failed resource should point to the OpenStack
service, e.g. OS::Cinder::Volume.  Check for more details on the failure by:

    heat resource-show *failed-stack-name* *failed-resource-name*

The resource_status_reason may give an indication on the failure, although
in some cases it may only say "Unknown".

If the failed resource is OS::Heat::WaitConditionHandle, this indicates that
one of the services that are being started on the node is hung.  Log into the
node where the failure occurred and check the respective `Kubernetes
services`_, `Swarm services`_ or `Mesos services`_.  If the failure is in
other scripts, look for them as `Heat software resource scripts`_.



TLS
---
*To be filled in*


Barbican service
----------------
*To be filled in*


Cluster internet access
-----------------------
*To be filled in*

(DNS, external network)


etcd service
------------
*To be filled in*


flannel service
---------------
*To be filled in*


Kubernetes services
-------------------
*To be filled in*

(How to introspect k8s when heat works and k8s does not)

Additional `Kubenetes troubleshooting guide
<http://kubernetes.io/v1.0/docs/troubleshooting.html>`_ is available.

Swarm services
--------------
*To be filled in*

(How to check on a swarm cluster: see membership information, view master,
agent containers)

Mesos services
--------------
*To be filled in*


Barbican issues
---------------
*To be filled in*


Docker CLI
----------
*To be filled in*


Request volume size
-------------------
*To be filled in*


Heat software resource scripts
------------------------------
*To be filled in*

