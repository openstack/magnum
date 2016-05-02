===============================================
Using Kubernetes external load balancer feature
===============================================

In a Kubernetes cluster, all masters and minions are connected to a private
Neutron subnet, which in turn is connected by a router to the public network.
This allows the nodes to access each other and the external internet.

All Kubernetes pods and services created in the cluster are connected to a
private container network which by default is Flannel, an overlay network that
runs on top of the Neutron private subnet.  The pods and services are assigned
IP addresses from this container network and they can access each other and
the external internet.  However, these IP addresses are not accessible from an
external network.

To publish a service endpoint externally so that the service can be accessed
from the external network, Kubernetes provides the external load balancer
feature.  This is done by simply specifying the attribute "type: LoadBalancer"
in the service manifest.  When the service is created, Kubernetes will add an
external load balancer in front of the service so that the service will have
an external IP address in addition to the internal IP address on the container
network.  The service endpoint can then be accessed with this external IP
address.  Refer to the Kubernetes guide for more details::

    http://kubernetes.io/v1.0/docs/user-guide/services.html#external-services

A Kubernetes cluster deployed by Magnum will have all the necessary
configuration required for the external load balancer.  This document describes
how to use this feature.

Steps for the cluster administrator
===================================

Because the Kubernetes master needs to interface with OpenStack to create and
manage the Neutron load balancer, we need to provide a credential for
Kubernetes to use.

In the current implementation, the cluster administrator needs to manually
perform this step.  We are looking into several ways to let Magnum automate
this step in a secure manner.  This means that after the Kubernetes cluster is
initially deployed, the load balancer support is disabled.  If the
administrator does not want to enable this feature, no further action is
required.  All the services will be created normally; services that specify the
load balancer will also be created successfully, but a load balancer will not
be created.

To enable the load balancer, log into each master node of your bay and
perform the following steps:

1. Configure kube-apiserver::

    sudo vi /etc/kubernetes/apiserver

   Comment out the line::

    #KUBE_API_ARGS="--runtime_config=api/all=true"

   Uncomment the line::

    KUBE_API_ARGS="--runtime_config=api/all=true --cloud_config=/etc/sysconfig/kube_openstack_config --cloud_provider=openstack"""

2. Configure kube-controller-manager::

    sudo vi /etc/kubernetes/controller-manager

   Uncomment the line::

    KUBE_CONTROLLER_MANAGER_ARGS="--cloud_config=/etc/sysconfig/kube_openstack_config --cloud_provider=openstack"

3. Enter OpenStack user credential::

    sudo vi /etc/sysconfig/kube_openstack_config

   The username and tenant-name entries have been filled in with the
   Keystone values of the user who created the bay.  Enter the password
   of this user on the entry for password::

    password=ChangeMe

4. Restart Kubernetes services::

    sudo service kube-apiserver restart
    sudo service kube-controller-manager restart
    service kube-apiserver status
    service kube-controller-manager status

This only needs to be done once.  The steps can be reversed to disable the
load balancer feature. Before deleting the Kubernetes cluster, make sure to
delete all the services that created load balancers. Because the Neutron
objects created by Kubernetes are not managed by Heat, they will not be
deleted by Heat and this will cause the bay-delete operation to fail. If this
occurs, delete the neutron objects manually (lb-pool, lb-vip, lb-member,
lb-healthmonitor) and then run bay-delete again.

Steps for the users
===================

For the user, publishing the service endpoint externally involves the following
2 steps:

1. Specify "type: LoadBalancer" in the service manifest
2. After the service is created, associate a floating IP with the VIP of the
   load balancer pool.

The following example illustrates how to create an external endpoint for
a pod running nginx.

Create a file (e.g nginx.yaml) describing a pod running nginx::

    apiVersion: v1
    kind: Pod
    metadata:
      name: nginx
      labels:
       app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx
        ports:
        - containerPort: 80

Create a file (e.g nginx-service.yaml) describing a service for the nginx pod::

    apiVersion: v1
    kind: Service
    metadata:
      name: nginxservice
      labels:
        app: nginx
    spec:
      ports:
      - port: 80
        targetPort: 80
        protocol: TCP
      selector:
        app: nginx
      type: LoadBalancer

Assuming that a Kubernetes bay named k8sbayv1 has been created, deploy the pod
and service by the commands. Please refer to the quickstart guide on how to
connect to Kubernetes running on the launched bay.::

    kubectl create -f nginx.yaml

    kubectl create -f nginx-service.yaml

For more details on verifying the load balancer in OpenStack, refer to the
following section on how it works.

Next, associate a floating IP to the load balancer.  This can be done easily
on Horizon by navigating to::

    Compute -> Access & Security -> Floating IPs

Click on "Allocate IP To Project" and then on "Associate" for the new floating
IP.

Alternatively, associating a floating IP can be done on the command line by
allocating a floating IP, finding the port of the VIP, and associating the
floating IP to the port.
The commands shown below are for illustration purpose and assume
that there is only one service with load balancer running in the bay and
no other load balancers exist except for those created for the cluster.

First create a floating IP on the public network::

    neutron floatingip-create public

    Created a new floatingip:

    +---------------------+--------------------------------------+
    | Field               | Value                                |
    +---------------------+--------------------------------------+
    | fixed_ip_address    |                                      |
    | floating_ip_address | 172.24.4.78                          |
    | floating_network_id | 4808eacb-e1a0-40aa-97b6-ecb745af2a4d |
    | id                  | b170eb7a-41d0-4c00-9207-18ad1c30fecf |
    | port_id             |                                      |
    | router_id           |                                      |
    | status              | DOWN                                 |
    | tenant_id           | 012722667dc64de6bf161556f49b8a62     |
    +---------------------+--------------------------------------+

Note the floating IP 172.24.4.78 that has been allocated.  The ID for this
floating IP is shown above, but it can also be queried by::

    FLOATING_ID=$(neutron floatingip-list | grep "172.24.4.78" | awk '{print $2}')

Next find the VIP for the load balancer::

    VIP_ID=$(neutron lb-vip-list | grep TCP | grep -v pool | awk '{print $2}')

Find the port for this VIP::

    PORT_ID=$(neutron lb-vip-show $VIP_ID | grep port_id | awk '{print $4}')

Finally associate the floating IP with the port of the VIP::

    neutron floatingip-associate $FLOATING_ID $PORT_ID

The endpoint for nginx can now be accessed at this floating IP::

    http://172.24.4.78:80

NOTE: it is not necessary to indicate port :80 here but it is shown to
correlate with the port that was specified in the service manifest.

How it works
============

Kubernetes is designed to work with different Clouds such as Google Compute
Engine (GCE), Amazon Web Services (AWS), and OpenStack;  therefore, different
load balancers need to be created on the particular Cloud for the services.
This is done through a plugin for each Cloud and the OpenStack plugin was
developed by Angus Lees::

    https://github.com/kubernetes/kubernetes/blob/release-1.0/pkg/cloudprovider/openstack/openstack.go

When the Kubernetes components kube-apiserver and kube-controller-manager start
up, they will use the credential provided to authenticate a client
to interface with OpenStack.

When a service with load balancer is created, the plugin code will interface
with Neutron in this sequence:

1. Create lb-pool for the Kubernetes service
2. Create lb-member for the minions
3. Create lb-healthmonitor
4. Create lb-vip on the private network of the Kubernetes cluster

These Neutron objects can be verified as follows.  For the load balancer pool::

    neutron lb-pool-list
    +--------------------------------------+----------------------------------------------+----------+-------------+----------+----------------+--------+
    | id                                   | name                                         | provider | lb_method   | protocol | admin_state_up | status |
    +--------------------------------------+----------------------------------------------+----------+-------------+----------+----------------+--------+
    | 241357b3-2a8f-442e-b534-bde7cd6ba7e4 | a1f03e40f634011e59c9efa163eae8ab             | haproxy  | ROUND_ROBIN | TCP      | True           | ACTIVE |
    | 82b39251-1455-4eb6-a81e-802b54c2df29 | k8sbayv1-iypacicrskib-api_pool-fydshw7uvr7h  | haproxy  | ROUND_ROBIN | HTTP     | True           | ACTIVE |
    | e59ea983-c6e8-4cec-975d-89ade6b59e50 | k8sbayv1-iypacicrskib-etcd_pool-qbpo43ew2m3x | haproxy  | ROUND_ROBIN | HTTP     | True           | ACTIVE |
    +--------------------------------------+----------------------------------------------+----------+-------------+----------+----------------+--------+

Note that 2 load balancers already exist to implement high availability for the
cluster (api and ectd). The new load balancer for the Kubernetes service uses
the TCP protocol and has a name assigned by Kubernetes.

For the members of the pool::

    neutron lb-member-list
    +--------------------------------------+----------+---------------+--------+----------------+--------+
    | id                                   | address  | protocol_port | weight | admin_state_up | status |
    +--------------------------------------+----------+---------------+--------+----------------+--------+
    | 9ab7dcd7-6e10-4d9f-ba66-861f4d4d627c | 10.0.0.5 |          8080 |      1 | True           | ACTIVE |
    | b179c1ad-456d-44b2-bf83-9cdc127c2b27 | 10.0.0.5 |          2379 |      1 | True           | ACTIVE |
    | f222b60e-e4a9-4767-bc44-ffa66ec22afe | 10.0.0.6 |         31157 |      1 | True           | ACTIVE |
    +--------------------------------------+----------+---------------+--------+----------------+--------+

Again, 2 members already exist for high availability and they serve the master
node at 10.0.0.5. The new member serves the minion at 10.0.0.6, which hosts the
Kubernetes service.

For the monitor of the pool::

    neutron lb-healthmonitor-list
    +--------------------------------------+------+----------------+
    | id                                   | type | admin_state_up |
    +--------------------------------------+------+----------------+
    | 381d3d35-7912-40da-9dc9-b2322d5dda47 | TCP  | True           |
    | 67f2ae8f-ffc6-4f86-ba5f-1a135f4af85c | TCP  | True           |
    | d55ff0f3-9149-44e7-9b52-2e055c27d1d3 | TCP  | True           |
    +--------------------------------------+------+----------------+

For the VIP of the pool::

    neutron lb-vip-list
    +--------------------------------------+----------------------------------+----------+----------+----------------+--------+
    | id                                   | name                             | address  | protocol | admin_state_up | status |
    +--------------------------------------+----------------------------------+----------+----------+----------------+--------+
    | 9ae2ebfb-b409-4167-9583-4a3588d2ff42 | api_pool.vip                     | 10.0.0.3 | HTTP     | True           | ACTIVE |
    | c318aec6-8b7b-485c-a419-1285a7561152 | a1f03e40f634011e59c9efa163eae8ab | 10.0.0.7 | TCP      | True           | ACTIVE |
    | fc62cf40-46ad-47bd-aa1e-48339b95b011 | etcd_pool.vip                    | 10.0.0.4 | HTTP     | True           | ACTIVE |
    +--------------------------------------+----------------------------------+----------+----------+----------------+--------+

Note that the VIP is created on the private network of the cluster;  therefore
it has an internal IP address of 10.0.0.7.  This address is also associated as
the "external address" of the Kubernetes service.  You can verify in Kubernetes
by running the kubectl command::

    kubectl get services
    NAME           LABELS                                    SELECTOR    IP(S)            PORT(S)
    kubernetes     component=apiserver,provider=kubernetes   <none>      10.254.0.1       443/TCP
    nginxservice   app=nginx                                 app=nginx   10.254.122.191   80/TCP
                                                                         10.0.0.7

On GCE, the networking implementation gives the load balancer an external
address automatically. On OpenStack, we need to take the additional step of
associating a floating IP to the load balancer.

