.. _launch-instance:

Launch an instance
~~~~~~~~~~~~~~~~~~

In environments that include the Container Infrastructure Management service,
you can provision container clusters made up of virtual machines or baremetal
servers. The Container Infrastructure Management service uses
`Cluster Templates <ClusterTemplate>`_
to describe how a :ref:`cluster` is constructed. In each of the
following examples
you will create a Cluster Template for a specific COE and then you will
provision a Cluster using the corresponding Cluster Template. Then, you can use
the appropriate COE client or endpoint to create containers.

Create an external network (Optional)
-------------------------------------

To create a magnum cluster, you need an external network. If there are no
external networks, create one.

#. Create an external network with an appropriate provider based on your
   cloud provider support for your case:

   .. code-block:: console

      $ openstack network create public --provider-network-type vxlan \
                                        --external \
                                        --project service
      +---------------------------+--------------------------------------+
      | Field                     | Value                                |
      +---------------------------+--------------------------------------+
      | admin_state_up            | UP                                   |
      | availability_zone_hints   |                                      |
      | availability_zones        |                                      |
      | created_at                | 2017-03-27T10:09:04Z                 |
      | description               |                                      |
      | dns_domain                | None                                 |
      | id                        | 372170ca-7d2e-48a2-8449-670e4ab66c23 |
      | ipv4_address_scope        | None                                 |
      | ipv6_address_scope        | None                                 |
      | is_default                | False                                |
      | mtu                       | 1450                                 |
      | name                      | public                               |
      | port_security_enabled     | True                                 |
      | project_id                | 224c32c0dd2e49cbaadfd1cda069f149     |
      | provider:network_type     | vxlan                                |
      | provider:physical_network | None                                 |
      | provider:segmentation_id  | 3                                    |
      | qos_policy_id             | None                                 |
      | revision_number           | 4                                    |
      | router:external           | External                             |
      | segments                  | None                                 |
      | shared                    | False                                |
      | status                    | ACTIVE                               |
      | subnets                   |                                      |
      | updated_at                | 2017-03-27T10:09:04Z                 |
      +---------------------------+--------------------------------------+
      $ openstack subnet create public-subnet --network public \
                                        --subnet-range 192.168.1.0/24 \
                                        --gateway 192.168.1.1 \
                                        --ip-version 4
      +-------------------+--------------------------------------+
      | Field             | Value                                |
      +-------------------+--------------------------------------+
      | allocation_pools  | 192.168.1.2-192.168.1.254            |
      | cidr              | 192.168.1.0/24                       |
      | created_at        | 2017-03-27T10:46:15Z                 |
      | description       |                                      |
      | dns_nameservers   |                                      |
      | enable_dhcp       | True                                 |
      | gateway_ip        | 192.168.1.1                          |
      | host_routes       |                                      |
      | id                | 04185f6c-ea31-4109-b20b-fd7f935b3828 |
      | ip_version        | 4                                    |
      | ipv6_address_mode | None                                 |
      | ipv6_ra_mode      | None                                 |
      | name              | public-subnet                        |
      | network_id        | 372170ca-7d2e-48a2-8449-670e4ab66c23 |
      | project_id        | d9e40a0aff30441083d9f279a0ff50de     |
      | revision_number   | 2                                    |
      | segment_id        | None                                 |
      | service_types     |                                      |
      | subnetpool_id     | None                                 |
      | updated_at        | 2017-03-27T10:46:15Z                 |
      +-------------------+--------------------------------------+

Create a keypair (Optional)
---------------------------

To create a magnum cluster, you need a keypair which will be passed
in all compute instances of the cluster. If you don't have a keypair
in your project, create one.

#. Create a keypair on the Compute service:

   .. code-block:: console

      $ openstack keypair create --public-key ~/.ssh/id_rsa.pub mykey
      +-------------+-------------------------------------------------+
      | Field       | Value                                           |
      +-------------+-------------------------------------------------+
      | fingerprint | 05:be:32:07:58:a7:e8:0b:05:9b:81:6d:80:9a:4e:b1 |
      | name        | mykey                                           |
      | user_id     | 2d4398dbd5274707bf100a9dbbe85819                |
      +-------------+-------------------------------------------------+

Upload the images required for your clusters to the Image service
-----------------------------------------------------------------

The Kubernetes driver require a Fedora CoreOS image. Plese refer to 'Supported
versions' for each Magnum release.

#. Download the image:

   .. code-block:: console

      $ export FCOS_VERSION="35.20220116.3.0"
      $ wget https://builds.coreos.fedoraproject.org/prod/streams/stable/builds/${FCOS_VERSION}/x86_64/fedora-coreos-${FCOS_VERSION}-openstack.x86_64.qcow2.xz
      $ unxz fedora-coreos-${FCOS_VERSION}-openstack.x86_64.qcow2.xz

#. Register the image to the Image service setting the ``os_distro`` property
   to ``fedora-coreos``:

   .. code-block:: console

      $ openstack image create \
                            --disk-format=qcow2 \
                            --container-format=bare \
                            --file=fedora-coreos-${FCOS_VERSION}-openstack.x86_64.qcow2 \
                            --property os_distro='fedora-coreos' \
                            fedora-coreos-latest


Provision a Kubernetes cluster and create a deployment
------------------------------------------------------

Following this example, you will provision a Kubernetes cluster with one
master and one node. Then, using Kubernetes's native client ``kubectl``, you
will create a deployment.

#. Create a cluster template for a Kubernetes cluster using the
   ``fedora-coreos-latest`` image, ``m1.small`` as the flavor for the master
   and the node, ``public`` as the external network and ``8.8.8.8`` for the
   DNS nameserver, using the following command:

   .. code-block:: console

      $ openstack coe cluster template create kubernetes-cluster-template \
                           --image fedora-coreos-latest \
                           --external-network public \
                           --dns-nameserver 8.8.8.8 \
                           --master-flavor m1.small \
                           --flavor m1.small \
                           --coe kubernetes

#. Create a cluster with one node and one master using ``mykey`` as the
   keypair, using the following command:

   .. code-block:: console

      $ openstack coe cluster create kubernetes-cluster \
                              --cluster-template kubernetes-cluster-template \
                              --master-count 1 \
                              --node-count 1 \
                              --keypair mykey
      Request to create cluster b1ef3528-ac03-4459-bbf7-22649bfbc84f has been accepted.

   Your cluster is now being created. Creation time depends on your
   infrastructure's performance. You can check the status of your cluster
   using the commands: ``openstack coe cluster list`` or
   ``openstack coe cluster show kubernetes-cluster``.

   .. code-block:: console

      $ openstack coe cluster list
      +--------------------------------------+--------------------+---------+------------+--------------+-----------------+
      | uuid                                 | name               | keypair | node_count | master_count | status          |
      +--------------------------------------+--------------------+---------+------------+--------------+-----------------+
      | b1ef3528-ac03-4459-bbf7-22649bfbc84f | kubernetes-cluster | mykey   | 1          | 1            | CREATE_COMPLETE |
      +--------------------------------------+--------------------+---------+------------+--------------+-----------------+

#. Add the credentials of the above cluster to your environment:

   .. code-block:: console

      $ mkdir -p ~/clusters/kubernetes-cluster
      $ cd ~/clusters/kubernetes-cluster
      $ openstack coe cluster config kubernetes-cluster


   The above command will save the authentication artifacts in the directory
   ``~/clusters/kubernetes-cluster``. It will output a command to set the ``KUBECONFIG``
   environment variable:

   .. code-block:: console

      export KUBECONFIG=/home/user/clusters/kubernetes-cluster/config

#. You can list the controller components of your Kubernetes cluster and
   check if they are ``Running``:

   .. code-block:: console

      $ kubectl -n kube-system get po
      NAME                                                                            READY     STATUS    RESTARTS   AGE
      kube-controller-manager-ku-hesuip7l3i-0-5mqijvszepxw-kube-master-rqwmwne7rjh2   1/1       Running   0          1h
      kube-proxy-ku-hesuip7l3i-0-5mqijvszepxw-kube-master-rqwmwne7rjh2                1/1       Running   0          1h
      kube-proxy-ku-wmmticfvdr-0-k53p22xmlxvx-kube-minion-x4ly6zfhrrui                1/1       Running   0          1h
      kube-scheduler-ku-hesuip7l3i-0-5mqijvszepxw-kube-master-rqwmwne7rjh2            1/1       Running   0          1h
      kubernetes-dashboard-3203831700-zvj2d                                           1/1       Running   0          1h

#. Now, you can create a nginx deployment and verify it is running:

   .. code-block:: console

      $ kubectl run nginx --image=nginx --replicas=5
      deployment "nginx" created
      $ kubectl get po
      NAME                    READY     STATUS    RESTARTS   AGE
      nginx-701339712-2ngt8   1/1       Running   0          15s
      nginx-701339712-j8r3d   1/1       Running   0          15s
      nginx-701339712-mb6jb   1/1       Running   0          15s
      nginx-701339712-q115k   1/1       Running   0          15s
      nginx-701339712-tb5lp   1/1       Running   0          15s

#. Delete the cluster:

   .. code-block:: console

      $ openstack coe cluster delete kubernetes-cluster
      Request to delete cluster kubernetes-cluster has been accepted.
