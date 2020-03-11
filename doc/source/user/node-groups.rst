Node groups can be used to create heterogeneous clusters.

This functionality is only supported for Kubernetes clusters.

When a cluster is created it already has two node groups,
``default-master`` and ``default-worker``.

::

   $ openstack coe cluster list
   +--------------------------------------+------+-----------+------------+--------------+-----------------+---------------+
   | uuid                                 | name | keypair   | node_count | master_count | status          | health_status |
   +--------------------------------------+------+-----------+------------+--------------+-----------------+---------------+
   | ef7011bb-d404-4198-a145-e8808204cde3 | kube | default   |          1 |            1 | CREATE_COMPLETE | HEALTHY       |
   +--------------------------------------+------+-----------+------------+--------------+-----------------+---------------+

   $ openstack coe nodegroup list kube
   +--------------------------------------+----------------+-----------+----------------------------------------+------------+-----------------+--------+
   | uuid                                 | name           | flavor_id | image_id                               | node_count | status          | role   |
   +--------------------------------------+----------------+-----------+----------------------------------------+------------+-----------------+--------+
   | adc3ecfa-d11e-4da7-8c44-4092ea9dddd9 | default-master | m1.small  | Fedora-AtomicHost-29-20190820.0.x86_64 |          1 | CREATE_COMPLETE | master |
   | 186e131f-8103-4285-a900-eb0dcf18a670 | default-worker | m1.small  | Fedora-AtomicHost-29-20190820.0.x86_64 |          1 | CREATE_COMPLETE | worker |
   +--------------------------------------+----------------+-----------+----------------------------------------+------------+-----------------+--------+

The ``default-worker`` node group cannot be removed or reconfigured, so
the initial cluster configuration should take this into account.

Create a new node group
-----------------------

To add a new node group, use ``openstack coe nodegroup create``. The
only required parameters are the cluster ID and the name for the new
node group, but several extra options are available.

Roles
+++++

Roles can be used to show the purpose of a node group, and multiple node
groups can be given the same role if they share a common purpose.

::

   $ openstack coe nodegroup create kube test-ng --node-count 1 --role test

When listing node groups, the role may be used as a filter:

::

   $ openstack coe nodegroup list kube --role test
   +--------------------------------------+---------+-----------+----------------------------------------+------------+--------------------+------+
   | uuid                                 | name    | flavor_id | image_id                               | node_count | status             | role |
   +--------------------------------------+---------+-----------+----------------------------------------+------------+--------------------+------+
   | b4ab1fcb-f23a-4d1f-b583-d699a2f1e2d7 | test-ng | m1.small  | Fedora-AtomicHost-29-20190820.0.x86_64 |          1 | CREATE_IN_PROGRESS | test |
   +--------------------------------------+---------+-----------+----------------------------------------+------------+--------------------+------+

The node group role will default to “worker” if unset, and the only
reserved role is “master”.

Role information is available within Kubernetes as labels on the nodes.

::

   $ kubectl get nodes -L magnum.openstack.org/role
   NAME                               STATUS   AGE    VERSION   ROLE
   kube-r6cyw4bjb4lr-master-0         Ready    5d5h   v1.16.0   master
   kube-r6cyw4bjb4lr-node-0           Ready    5d5h   v1.16.0   worker
   kube-test-ng-lg7bkvjgus4y-node-0   Ready    61s    v1.16.0   test

This information can be used for scheduling, using a `node
selector <https://kubernetes.io/docs/concepts/configuration/assign-pod-node/#step-two-add-a-nodeselector-field-to-your-pod-configuration>`__.

.. code:: yaml

   nodeSelector:
     magnum.openstack.org/role: test

The label ``magnum.openstack.org/nodegroup`` is also available for
selecting a specific node group.

Flavor
++++++

The node group flavor will default to the minion flavor given when
creating the cluster, but can be changed for each new node group.

::

   $ openstack coe nodegroup create ef7011bb-d404-4198-a145-e8808204cde3 large-ng --flavor m2.large

This can be used if you require nodes of different sizes in the same
cluster, or to switch from one flavor to another by creating a new node
group and deleting the old one.

Availability zone
+++++++++++++++++

To create clusters which span more than one availability zone, multiple
node groups must be used. The availability zone is passed as a label to
the node group.

::

   $ openstack coe nodegroup create kube zone-a --labels availability_zone=zone-a --labels ...
   $ openstack coe nodegroup create kube zone-b --labels availability_zone=zone-b --labels ...
   $ openstack coe nodegroup create kube zone-c --labels availability_zone=zone-c --labels ...

Where ``--labels ...`` are the rest of the labels that the cluster was
created with, which can be obtained from the cluster with this script:

::

   $ openstack coe cluster show -f json <CLUSTER_ID> |
       jq --raw-output '.labels | to_entries |
       map("--labels \(.key)=\"\(.value)\"") | join(" ")'

Zone information is available within the cluster as the label
``topology.kubernetes.io/zone`` on each node, or as the now deprecated
label ``failure-domain.beta.kubernetes.io/zone``.

From Kubernetes 1.16 and onwards it is possible to `balance the number
of pods in a deployment across availability
zones <https://kubernetes.io/docs/concepts/workloads/pods/pod-topology-spread-constraints/>`__
(or any other label).

Resize
------

Resizing a node group is done with the same API as resizing a cluster,
but the ``--nodegroup`` parameter must be used.

::

   $ openstack coe cluster resize kube --nodegroup default-worker 2
   Request to resize cluster ef7011bb-d404-4198-a145-e8808204cde3 has been accepted.

As usual the ``--nodes-to-remove`` parameter may be used to remove
specific nodes when decreasing the size of a node group.

Delete
------

Any node group except the default master and worker node groups can be
deleted, by specifying the cluster and nodegroup name or ID.

::

   $ openstack coe nodegroup delete ef7011bb-d404-4198-a145-e8808204cde3 test-ng
