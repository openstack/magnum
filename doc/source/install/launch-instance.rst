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

The VM versions of Kubernetes and Docker Swarm drivers require a Fedora Atomic
image. The following is stock Fedora Atomic image, built by the Atomic team
and tested by the Magnum team.

#. Download the image:

   .. code-block:: console

      $ wget https://download.fedoraproject.org/pub/alt/atomic/stable/Fedora-Atomic-27-20180419.0/CloudImages/x86_64/images/Fedora-Atomic-27-20180419.0.x86_64.qcow2

#. Register the image to the Image service setting the ``os_distro`` property
   to ``fedora-atomic``:

   .. code-block:: console

      $ openstack image create \
                            --disk-format=qcow2 \
                            --container-format=bare \
                            --file=Fedora-Atomic-27-20180419.0.x86_64.qcow2\
                            --property os_distro='fedora-atomic' \
                            fedora-atomic-latest
      +------------------+------------------------------------------------------+
      | Field            | Value                                                |
      +------------------+------------------------------------------------------+
      | checksum         | a987b691e23dce54c03d7a57c104b195                     |
      | container_format | bare                                                 |
      | created_at       | 2016-09-14T12:58:01Z                                 |
      | disk_format      | qcow2                                                |
      | file             | /v2/images/81b25935-3400-441a-9f2e-f984a46c89dd/file |
      | id               | 81b25935-3400-441a-9f2e-f984a46c89dd                 |
      | min_disk         | 0                                                    |
      | min_ram          | 0                                                    |
      | name             | fedora-atomic-latest                                 |
      | owner            | c4b42942156741dfbc4775dbcb032841                     |
      | properties       | os_distro='fedora-atomic'                            |
      | protected        | False                                                |
      | schema           | /v2/schemas/image                                    |
      | size             | 507928064                                            |
      | status           | active                                               |
      | tags             |                                                      |
      | updated_at       | 2016-09-14T12:58:03Z                                 |
      | virtual_size     | None                                                 |
      | visibility       | private                                              |
      +------------------+------------------------------------------------------+

Provision a Docker Swarm cluster and create a container
-------------------------------------------------------

Following this example, you will provision a Docker Swarm cluster with one
master and one node. Then, using docker's native API you will create a
container.


#. Create a cluster template for a Docker Swarm cluster using the
   ``fedora-atomic-latest`` image, ``m1.small`` as the flavor for the master
   and the node, ``public`` as the external network and ``8.8.8.8`` for the
   DNS nameserver, using the following command:

   .. code-block:: console

      $ openstack coe cluster template create swarm-cluster-template \
                           --image fedora-atomic-latest \
                           --external-network public \
                           --dns-nameserver 8.8.8.8 \
                           --master-flavor m1.small \
                           --flavor m1.small \
                           --coe swarm
      +-----------------------+--------------------------------------+
      | Property              | Value                                |
      +-----------------------+--------------------------------------+
      | insecure_registry     | -                                    |
      | labels                | {}                                   |
      | updated_at            | -                                    |
      | floating_ip_enabled   | True                                 |
      | fixed_subnet          | -                                    |
      | master_flavor_id      | m1.small                             |
      | uuid                  | 47c6ce77-50ae-43bd-8e2a-06980392693d |
      | no_proxy              | -                                    |
      | https_proxy           | -                                    |
      | tls_disabled          | False                                |
      | keypair_id            | mykey                                |
      | public                | False                                |
      | http_proxy            | -                                    |
      | docker_volume_size    | -                                    |
      | server_type           | vm                                   |
      | external_network_id   | public                               |
      | cluster_distro        | fedora-atomic                        |
      | image_id              | fedora-atomic-latest                 |
      | volume_driver         | -                                    |
      | registry_enabled      | False                                |
      | docker_storage_driver | devicemapper                         |
      | apiserver_port        | -                                    |
      | name                  | swarm-cluster-template               |
      | created_at            | 2016-09-14T13:05:11+00:00            |
      | network_driver        | docker                               |
      | fixed_network         | -                                    |
      | coe                   | swarm                                |
      | flavor_id             | m1.small                             |
      | master_lb_enabled     | False                                |
      | dns_nameserver        | 8.8.8.8                              |
      +-----------------------+--------------------------------------+

#. Create a cluster with one node and one master using ``mykey`` as the
   keypair, using the following command:

   .. code-block:: console

      $ openstack coe cluster create swarm-cluster \
                              --cluster-template swarm-cluster-template \
                              --master-count 1 \
                              --node-count 1 \
                              --keypair mykey
      Request to create cluster 2582f192-480e-4329-ac05-32a8e5b1166b has been accepted.

   Your cluster is now being created. Creation time depends on your
   infrastructure's performance. You can check the status of your cluster
   using the commands: ``openstack coe cluster list`` or
   ``openstack coe cluster show swarm-cluster``.

   .. code-block:: console

      $ openstack coe cluster list
      +--------------------------------------+---------------+---------+------------+--------------+-----------------+
      | uuid                                 | name          | keypair | node_count | master_count | status          |
      +--------------------------------------+---------------+---------+------------+--------------+-----------------+
      | 2582f192-480e-4329-ac05-32a8e5b1166b | swarm-cluster | mykey   | 1          | 1            | CREATE_COMPLETE |
      +--------------------------------------+---------------+---------+------------+--------------+-----------------+

   .. code-block:: console

      $ openstack coe cluster show swarm-cluster
      +---------------------+------------------------------------------------------------+
      | Property            | Value                                                      |
      +---------------------+------------------------------------------------------------+
      | status              | CREATE_COMPLETE                                            |
      | cluster_template_id | 47c6ce77-50ae-43bd-8e2a-06980392693d                       |
      | uuid                | 2582f192-480e-4329-ac05-32a8e5b1166b                       |
      | stack_id            | 3d7bbf1c-49bd-4930-84e0-ab71ba200687                       |
      | status_reason       | Stack CREATE completed successfully                        |
      | created_at          | 2016-09-14T13:36:54+00:00                                  |
      | name                | swarm-cluster                                              |
      | updated_at          | 2016-09-14T13:38:08+00:00                                  |
      | discovery_url       | https://discovery.etcd.io/a5ece414689287eca62e35555512bfd5 |
      | api_address         | tcp://172.24.4.10:2376                                     |
      | coe_version         | 1.2.5                                                      |
      | master_addresses    | ['172.24.4.10']                                            |
      | create_timeout      | 60                                                         |
      | node_addresses      | ['172.24.4.8']                                             |
      | master_count        | 1                                                          |
      | container_version   | 1.12.6                                                     |
      | node_count          | 1                                                          |
      +---------------------+------------------------------------------------------------+

#. Add the credentials of the above cluster to your environment:

   .. code-block:: console

      $ mkdir myclusterconfig
      $ $(openstack coe cluster config swarm-cluster --dir myclusterconfig)


   The above command will save the authentication artifacts in the
   `myclusterconfig` directory and it will export the environment
   variables: DOCKER_HOST, DOCKER_CERT_PATH and DOCKER_TLS_VERIFY.
   Sample output:

   .. code-block:: console

      export DOCKER_HOST=tcp://172.24.4.10:2376
      export DOCKER_CERT_PATH=myclusterconfig
      export DOCKER_TLS_VERIFY=True

#. Create a container:

   .. code-block:: console

      $ docker run busybox echo "Hello from Docker!"
      Hello from Docker!

#. Delete the cluster:

   .. code-block:: console

      $ openstack coe cluster delete swarm-cluster
      Request to delete cluster swarm-cluster has been accepted.

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
      +-----------------------+--------------------------------------+
      | Property              | Value                                |
      +-----------------------+--------------------------------------+
      | insecure_registry     | -                                    |
      | labels                | {}                                   |
      | updated_at            | -                                    |
      | floating_ip_enabled   | True                                 |
      | fixed_subnet          | -                                    |
      | master_flavor_id      | m1.small                             |
      | uuid                  | 0a601cc4-8fef-41aa-8036-d113e719ed7a |
      | no_proxy              | -                                    |
      | https_proxy           | -                                    |
      | tls_disabled          | False                                |
      | keypair_id            | -                                    |
      | public                | False                                |
      | http_proxy            | -                                    |
      | docker_volume_size    | -                                    |
      | server_type           | vm                                   |
      | external_network_id   | public                               |
      | cluster_distro        | fedora-atomic                        |
      | image_id              | fedora-atomic-latest                 |
      | volume_driver         | -                                    |
      | registry_enabled      | False                                |
      | docker_storage_driver | devicemapper                         |
      | apiserver_port        | -                                    |
      | name                  | kubernetes-cluster-template          |
      | created_at            | 2017-05-16T09:53:00+00:00            |
      | network_driver        | flannel                              |
      | fixed_network         | -                                    |
      | coe                   | kubernetes                           |
      | flavor_id             | m1.small                             |
      | master_lb_enabled     | False                                |
      | dns_nameserver        | 8.8.8.8                              |
      +-----------------------+--------------------------------------+

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

   .. code-block:: console

      $ openstack coe cluster show kubernetes-cluster
      +---------------------+------------------------------------------------------------+
      | Property            | Value                                                      |
      +---------------------+------------------------------------------------------------+
      | status              | CREATE_COMPLETE                                            |
      | cluster_template_id | 0a601cc4-8fef-41aa-8036-d113e719ed7a                       |
      | node_addresses      | ['172.24.4.5']                                             |
      | uuid                | b1ef3528-ac03-4459-bbf7-22649bfbc84f                       |
      | stack_id            | 8296624c-3c0e-45e1-967e-b6ff05105a3b                       |
      | status_reason       | Stack CREATE completed successfully                        |
      | created_at          | 2017-05-16T09:58:02+00:00                                  |
      | updated_at          | 2017-05-16T10:00:02+00:00                                  |
      | coe_version         | v1.6.7                                                     |
      | keypair             | default                                                    |
      | api_address         | https://172.24.4.13:6443                                   |
      | master_addresses    | ['172.24.4.13']                                            |
      | create_timeout      | 60                                                         |
      | node_count          | 1                                                          |
      | discovery_url       | https://discovery.etcd.io/69c7cd3b3b06c98b4771410bd166a7c6 |
      | master_count        | 1                                                          |
      | container_version   | 1.12.6                                                     |
      | name                | kubernetes-cluster                                         |
      +---------------------+------------------------------------------------------------+

#. Add the credentials of the above cluster to your environment:

   .. code-block:: console

      $ mkdir -p ~/clusters/kubernetes-cluster
      $ $(openstack coe cluster config kubernetes-cluster --dir ~/clusters/kubernetes-cluster)


   The above command will save the authentication artifacts in the directory
   ``~/clusters/kubernetes-cluster`` and it will export the ``KUBECONFIG``
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
