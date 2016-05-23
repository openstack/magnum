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
#. `Choosing a COE`_
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
#. `Notification`_

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

========
Overview
========
*To be filled in*

Magnum rationale, concept, compelling features

BayModel
---------
*To be filled in*

Bay
---
*To be filled in*

=============
Python Client
=============

Installation
------------

Follow the instructions in the OpenStack Installation Guide to enable the
repositories for your distribution:

* `RHEL/CentOS/Fedora
  <http://docs.openstack.org/liberty/install-guide-rdo/>`_
* `Ubuntu/Debian
  <http://docs.openstack.org/liberty/install-guide-ubuntu/>`_
* `openSUSE/SUSE Linux Enterprise
  <http://docs.openstack.org/liberty/install-guide-obs/>`_

Install using distribution packages for RHEL/CentOS/Fedora::

    $ sudo yum install python-magnumclient

Install using distribution packages for Ubuntu/Debian::

    $ sudo apt-get install python-magnumclient

Install using distribution packages for OpenSuSE and SuSE Enterprise Linux::

    $ sudo zypper install python-magnumclient

Verifying installation
----------------------

Execute the `magnum` command with the `--version` argument to confirm that the
client is installed and in the system path::

    $ magnum --version
    1.1.0

Note that the version returned may differ from the above, 1.1.0 was the latest
available version at the time of writing.

Using the command-line client
-----------------------------

Refer to the `OpenStack Command-Line Interface Reference
<http://docs.openstack.org/cli-reference/magnum.html>`_ for a full list of the
commands supported by the `magnum` command-line client.

=================
Horizon Interface
=================
*To be filled in with screenshots*

==============
Choosing a COE
==============
Magnum supports a variety of COE options, and allows more to be added over time
as they gain popularity. As an operator, you may choose to support the full
variety of options, or you may want to offer a subset of the available choices.
Given multiple choices, your users can run one or more bays, and each may use
a different COE. For example, I might have multiple bays that use Kubernetes,
and just one bay that uses Swarm. All of these bays can run concurrently, even
though they use different COE software.

Choosing which COE to use depends on what tools you want to use to manage your
containers once you start your app. If you want to use the Docker tools, you
may want to use the Swarm bay type. Swarm will spread your containers across
the various nodes in your bay automatically. It does not monitor the health of
your containers, so it can't restart them for you if they stop. It will not
automatically scale your app for you (as of Swarm version 1.2.2). You may view
this as a plus. If you prefer to manage your application yourself, you might
prefer swarm over the other COE options.

Kubernetes (as of v1.2) is more sophisticated than Swarm (as of v1.2.2). It
offers an attractive YAML file description of a pod, which is a grouping of
containers that run together as part of a distributed application. This file
format allows you to model your application deployment using a declarative
style. It has support for autoscaling and fault recovery, as well as features
that allow for sophisticated software deployments, including canary deploys
and blue/green deploys. Kubernetes is very popular, especially for web
applications.

Apache Mesos is a COE that has been around longer than Kubernetes or Swarm. It
allows for a variety of different frameworks to be used along with it,
including Marathon, Aurora, Chronos, Hadoop, and `a number of others.
<http://mesos.apache.org/documentation/latest/frameworks/>`_

The Apache Mesos framework design can be used to run alternate COE software
directly on Mesos. Although this approach is not widely used yet, it may soon
be possible to run Mesos with Kubernetes and Swarm as frameworks, allowing
you to share the resources of a bay between multiple different COEs. Until
this option matures, we encourage Magnum users to create multiple bays, and
use the COE in each bay that best fits the anticipated workload.

Finding the right COE for your workload is up to you, but Magnum offers you a
choice to select among the prevailing leading options. Once you decide, see
the next sections for examples of how to create a bay with your desired COE.

==============
Native clients
==============
*To be filled in*

==========
Kubernetes
==========
Kubernetes uses a range of terminology that we refer to in this guide. We
define these common terms for your reference:

Pod
  When using the Kubernetes container orchestration engine, a pod is the
  smallest deployable unit that can be created and managed. A pod is a
  co-located group of application containers that run with a shared context.
  When using Magnum, pods are created and managed within bays. Refer to the
  `pods section
  <http://kubernetes.io/v1.0/docs/user-guide/pods.html>`_ in the `Kubernetes
  User Guide`_ for more information.

Replication controller
  A replication controller is used to ensure that at any given time a certain
  number of replicas of a pod are running. Pods are automatically created and
  deleted by the replication controller as necessary based on a template to
  ensure that the defined number of replicas exist. Refer to the `replication
  controller section
  <http://kubernetes.io/v1.0/docs/user-guide/replication-controller.html>`_ in
  the `Kubernetes User Guide`_ for more information.

Service
  A service is an additional layer of abstraction provided by the Kubernetes
  container orchestration engine which defines a logical set of pods and a
  policy for accessing them. This is useful because pods are created and
  deleted by a replication controller, for example, other pods needing to
  discover them can do so via the service abstraction. Refer to the
  `services section
  <http://kubernetes.io/v1.0/docs/user-guide/services.html>`_ in the
  `Kubernetes User Guide`_ for more information.

.. _Kubernetes User Guide: http://kubernetes.io/v1.0/docs/user-guide/

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

There are two components that make up the networking in a cluster.

1. The Neutron infrastructure for the cluster: this includes the
   private network, subnet, ports, routers, load balancers, etc.

2. The networking model presented to the containers: this is what the
   containers see in communicating with each other and to the external
   world. Typically this consists of a driver deployed on each node.

The two components are deployed and managed separately.  The Neutron
infrastructure is the integration with OpenStack; therefore, it
is stable and more or less similar across different COE
types.  The networking model, on the other hand, is specific to the
COE type and is still under active development in the various
COE communities, for example,
`Docker libnetwork <https://github.com/docker/libnetwork>`_ and
`Kubernetes Container Networking
<https://github.com/kubernetes/kubernetes/blob/release-1.1/docs/design/networking.md>`_.
As a result, the implementation for the networking models is evolving and
new models are likely to be introduced in the future.

For the Neutron infrastructure, the following configuration can
be set in the baymodel:

external-network-id
  The external Neutron network ID to connect to this bay. This
  is used to connect the cluster to the external internet, allowing
  the nodes in the bay to access external URL for discovery, image
  download, etc.  If not specified, the default value is "public" and this
  is valid for a typical devstack.

fixed-network
  The Neutron network to use as the private network for the bay nodes.
  If not specified, a new Neutron private network will be created.

dns-nameserver
  The DNS nameserver to use for this bay.  This is an IP address for
  the server and it is used to configure the Neutron subnet of the
  cluster (dns_nameservers).  If not specified, the default DNS is
  8.8.8.8, the publicly available DNS.

http-proxy, https-proxy, no-proxy
  The proxy for the nodes in the bay, to be used when the cluster is
  behind a firewall and containers cannot access URL's on the external
  internet directly.  For the parameter http-proxy and https-proxy, the
  value to provide is a URL and it will be set in the environment
  variable HTTP_PROXY and HTTPS_PROXY respectively in the nodes.  For
  the parameter no-proxy, the value to provide is an IP or list of IP's
  separated by comma.  Likewise, the value will be set in the
  environment variable NO_PROXY in the nodes.

For the networking model to the container, the following configuration
can be set in the baymodel:

network-driver
  The network driver name for instantiating container networks.
  Currently, the following network drivers are supported:

  +--------+-------------+-----------+-------------+
  | Driver | Kubernetes  |   Swarm   |    Mesos    |
  +========+=============+===========+=============+
  | Flannel| supported   | supported | unsupported |
  +--------+-------------+-----------+-------------+
  | Docker | unsupported | supported | supported   |
  +--------+-------------+-----------+-------------+

  If not specified, the default driver is Flannel for Kubernetes, and
  Docker for Swarm and Mesos.

Particular network driver may require its own set of parameters for
configuration, and these parameters are specified through the labels
in the baymodel.  Labels are arbitrary key=value pairs.

When Flannel is specified as the network driver, the following
optional labels can be added:

flannel_network_cidr
  IPv4 network in CIDR format to use for the entire Flannel network.
  If not specified, the default is 10.100.0.0/16.

flannel_network_subnetlen
  The size of the subnet allocated to each host. If not specified, the
  default is 24.

flannel_backend
  The type of backend for Flannel.  Possible values are *udp, vxlan,
  host-gw*.  If not specified, the default is *udp*.  Selecting the
  best backend depends on your networking.  Generally, *udp* is
  the most generally supported backend since there is little
  requirement on the network, but it typically offers the lowest
  performance.  The *vxlan* backend performs better, but requires
  vxlan support in the kernel so the image used to provision the
  nodes needs to include this support.  The *host-gw* backend offers
  the best performance since it does not actually encapsulate
  messages, but it requires all the nodes to be on the same L2
  network.  The private Neutron network that Magnum creates does
  meet this requirement;  therefore if the parameter *fixed_network*
  is not specified in the baymodel, *host-gw* is the best choice for
  the Flannel backend.


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

Currently Cinder provides the block storage to the containers, and the
storage is made available in two ways: as ephemeral storage and as
persistent storage.

Ephemeral storage
-----------------

The filesystem for the container consists of multiple layers from the
image and a top layer that holds the modification made by the
container.  This top layer requires storage space and the storage is
configured in the Docker daemon through a number of storage options.
When the container is removed, the storage allocated to the particular
container is also deleted.

To manage this space in a flexible manner independent of the Nova
instance flavor, Magnum creates a separate Cinder block volume for each
node in the bay, mounts it to the node and configures it to be used as
ephemeral storage.  Users can specify the size of the Cinder volume with
the baymodel attribute 'docker-volume-size'.  The default size is 5GB.
Currently the block size is fixed at bay creation time, but future
lifecycle operations may allow modifying the block size during the
life of the bay.

To use the Cinder block storage, there is a number of Docker
storage drivers available.  Only 'devicemapper' is supported as the
storage driver but other drivers such as 'OverlayFS' are being
considered.  There are important trade-off between the choices
for the storage drivers that should be considered.  For instance,
'OperlayFS' may offer better performance, but it may not support
the filesystem metadata needed to use SELinux, which is required
to support strong isolation between containers running in the same
bay. Using the 'devicemapper' driver does allow the use of SELinux.


Persistent storage
------------------

In some use cases, data read/written by a container needs to persist
so that it can be accessed later.  To persist the data, a Cinder
volume with a filesystem on it can be mounted on a host and be made
available to the container, then be unmounted when the container exits.

Docker provides the 'volume' feature for this purpose: the user
invokes the 'volume create' command, specifying a particular volume
driver to perform the actual work.  Then this volume can be mounted
when a container is created.  A number of third-party volume drivers
support OpenStack Cinder as the backend, for example Rexray and
Flocker.  Magnum currently supports Rexray as the volume driver for
Swarm and Mesos.  Other drivers are being considered.

Kubernetes allows a previously created Cinder block to be mounted to
a pod and this is done by specifying the block ID in the pod yaml file.
When the pod is scheduled on a node, Kubernetes will interface with
Cinder to request the volume to be mounted on this node, then
Kubernetes will launch the Docker container with the proper options to
make the filesystem on the Cinder volume accessible to the container
in the pod.  When the pod exits, Kubernetes will again send a request
to Cinder to unmount the volume's filesystem, making it avaiable to be
mounted on other nodes.

Magnum supports these features to use Cinder as persistent storage
using the baymodel attribute 'volume-driver' and the support matrix
for the COE types is summarized as follows:

+--------+-------------+-------------+-------------+
| Driver | Kubernetes  |    Swarm    |    Mesos    |
+========+=============+=============+=============+
| cinder | supported   | unsupported | unsupported |
+--------+-------------+-------------+-------------+
| rexray | unsupported | supported   | supported   |
+--------+-------------+-------------+-------------+

Following are some examples for using Cinder as persistent storage.

Using Cinder in Kubernetes
++++++++++++++++++++++++++

**NOTE:** This feature requires Kubernetes version 1.1.1 or above and
Docker version 1.8.3 or above.  The public Fedora image from Atomic
currently meets this requirement.

**NOTE:** The following steps are a temporary workaround, and Magnum's
development team is working on a long term solution to automate these steps.

1. Create the baymodel.

   Specify 'cinder' as the volume-driver for Kubernetes::

    magnum baymodel-create --name k8sbaymodel \
                           --image-id fedora-23-atomic-7 \
                           --keypair-id testkey \
                           --external-network-id public \
                           --dns-nameserver 8.8.8.8 \
                           --flavor-id m1.small \
                           --docker-volume-size 5 \
                           --network-driver flannel \
                           --coe kubernetes \
                           --volume-driver cinder

2. Create the bay::

    magnum bay-create --name k8sbay --baymodel k8sbaymodel --node-count 1


3. Configure kubelet.

   To allow Kubernetes to interface with Cinder, log into each minion
   node of your bay and perform step 4 through 6::

    sudo vi /etc/kubernetes/kubelet

   Comment out the line::

    #KUBELET_ARGS=--config=/etc/kubernetes/manifests --cadvisor-port=4194

   Uncomment the line::

    #KUBELET_ARGS="--config=/etc/kubernetes/manifests --cadvisor-port=4194 --cloud-provider=openstack --cloud-config=/etc/kubernetes/kube_openstack_config"


4. Enter OpenStack user credential::

    sudo vi /etc/kubernetes/kube_openstack_config

  The username, tenant-name and region entries have been filled in with the
  Keystone values of the user who created the bay.  Enter the password
  of this user on the entry for password::

    password=ChangeMe

5. Restart Kubernetes services::

    sudo systemctl restart kubelet

   On restart, the new configuration enables the Kubernetes cloud provider
   plugin for OpenStack, along with the necessary credential for kubelet
   to authenticate with Keystone and to make request to OpenStack services.

6. Install nsenter::

    sudo docker run -v /usr/local/bin:/target jpetazzo/nsenter

   The nsenter utility is used by Kubernetes to run new processes within
   existing kernel namespaces. This allows the kubelet agent to manage storage
   for pods.

Kubernetes is now ready to use Cinder for persistent storage.
Following is an example illustrating how Cinder is used in a pod.

1. Create the cinder volume::

    cinder create --display-name=test-repo 1

    ID=$(cinder create --display-name=test-repo 1 | awk -F'|' '$2~/^[[:space:]]*id/ {print $3}')

   The command will generate the volume with a ID. The volume ID will be specified in
   Step 2.

2. Create a pod in this bay and mount this cinder volume to the pod.
   Create a file (e.g nginx-cinder.yaml) describing the pod::

    cat > nginx-cinder.yaml << END
    apiVersion: v1
    kind: Pod
    metadata:
      name: aws-web
    spec:
      containers:
        - name: web
          image: nginx
          ports:
            - name: web
              containerPort: 80
              hostPort: 8081
              protocol: TCP
          volumeMounts:
            - name: html-volume
              mountPath: "/usr/share/nginx/html"
      volumes:
        - name: html-volume
          cinder:
            # Enter the volume ID below
            volumeID: $ID
            fsType: ext4
    END

**NOTE:** The Cinder volume ID needs to be configured in the yaml file
so the existing Cinder volume can be mounted in a pod by specifying
the volume ID in the pod manifest as follows::

    volumes:
    - name: html-volume
      cinder:
        volumeID: $ID
        fsType: ext4

3. Create the pod by the normal Kubernetes interface::

    kubectl create -f nginx-cinder.yaml

You can start a shell in the container to check that the mountPath exists,
and on an OpenStack client you can run the command 'cinder list' to verify
that the cinder volume status is 'in-use'.


Using Cinder in Swarm
+++++++++++++++++++++
*To be filled in*


Using Cinder in Mesos
+++++++++++++++++++++

1. Create the baymodel.

   Specify 'rexray' as the volume-driver for Mesos.  As an option, you
   can specify in a label the attributes 'rexray_preempt' to enable
   any host to take control of a volume regardless if other
   hosts are using the volume. If this is set to false, the driver
   will ensure data safety by locking the volume::

    magnum baymodel-create --name mesosbaymodel \
                           --image-id ubuntu-mesos \
                           --keypair-id testkey \
                           --external-network-id public \
                           --dns-nameserver 8.8.8.8 \
                           --master-flavor-id m1.magnum \
                           --docker-volume-size 4 \
                           --tls-disabled \
                           --flavor-id m1.magnum \
                           --coe mesos \
                           --volume-driver rexray \
                           --labels rexray-preempt=true

2. Create the Mesos bay::

    magnum bay-create --name mesosbay --baymodel mesosbaymodel --node-count 1

3. Create the cinder volume and configure this bay::

    cinder create --display-name=redisdata 1

   Create the following file ::

    cat > mesos.json << END
    {
      "id": "redis",
      "container": {
        "docker": {
        "image": "redis",
        "network": "BRIDGE",
        "portMappings": [
          { "containerPort": 80, "hostPort": 0, "protocol": "tcp"}
        ],
        "parameters": [
           { "key": "volume-driver", "value": "rexray" },
           { "key": "volume", "value": "redisdata:/data" }
        ]
        }
     },
     "cpus": 0.2,
     "mem": 32.0,
     "instances": 1
    }
    END

**NOTE:** When the Mesos bay is created using this baymodel, the Mesos bay
will be configured so that a filesystem on an existing cinder volume can
be mounted in a container by configuring the parameters to mount the cinder
volume in the json file ::

    "parameters": [
       { "key": "volume-driver", "value": "rexray" },
       { "key": "volume", "value": "redisdata:/data" }
    ]

4. Create the container using Marathon REST API ::

    MASTER_IP=$(magnum bay-show mesosbay | awk '/ api_address /{print $4}')
    curl -X POST -H "Content-Type: application/json" \
    http://${MASTER_IP}:8080/v2/apps -d@mesos.json

You can log into the container to check that the mountPath exists, and
you can run the command 'cinder list' to verify that your cinder
volume status is 'in-use'.


================
Image Management
================

When a COE is deployed, an image from Glance is used to boot the nodes
in the cluster and then the software will be configured and started on
the nodes to bring up the full cluster.  An image is based on a
particular distro such as Fedora, Ubuntu, etc, and is prebuilt with
the software specific to the COE such as Kubernetes, Swarm, Mesos.
The image is tightly coupled with the following in Magnum:

1. Heat templates to orchestrate the configuration.

2. Template definition to map baymodel parameters to Heat
   template parameters.

3. Set of scripts to configure software.

Collectively, they constitute the driver for a particular COE and a
particular distro; therefore, developing a new image needs to be done
in conjunction with developing these other components.  Image can be
built by various methods such as diskimagebuilder, or in some case, a
distro image can be used directly.  A number of drivers and the
associated images is supported in Magnum as reference implementation.
In this section, we focus mainly on the supported images.

All images must include support for cloud-init and the heat software
configuration utility:

- os-collect-config
- os-refresh-config
- os-apply-config
- heat-config
- heat-config-script

Additional software are described as follows.

Kubernetes on Fedora Atomic
---------------------------

This image can be downloaded from the `public Atomic site
<https://alt.fedoraproject.org/pub/alt/atomic/stable/Cloud-Images/x86_64/Images/>`_
or can be built locally using diskimagebuilder.  Details can be found in the
`fedora-atomic element
<https://github.com/openstack/magnum/tree/master/magnum/elements/fedora-atomic>`_
The image currently has the following OS/software:

+-------------+-----------+
| OS/software | version   |
+=============+===========+
| Fedora      | 23        |
+-------------+-----------+
| Docker      | 1.9.1     |
+-------------+-----------+
| Kubernetes  | 1.2.0     |
+-------------+-----------+
| etcd        | 2.2.1     |
+-------------+-----------+
| Flannel     | 0.5.4     |
+-------------+-----------+

The following software are managed as systemd services:

- kube-apiserver
- kubelet
- etcd
- flannel (if specified as network driver)
- docker

The following software are managed as Docker containers:

- kube-controller-manager
- kube-scheduler
- kube-proxy

The login for this image is *minion*.

Kubernetes on CoreOS
--------------------

CoreOS publishes a `stock image
<http://beta.release.core-os.net/amd64-usr/current/coreos_production_openstack_image.img.bz2>`_
that is being used to deploy Kubernetes.
This image has the following OS/software:

+-------------+-----------+
| OS/software | version   |
+=============+===========+
| CoreOS      | 4.3.6     |
+-------------+-----------+
| Docker      | 1.9.1     |
+-------------+-----------+
| Kubernetes  | 1.0.6     |
+-------------+-----------+
| etcd        | 2.2.3     |
+-------------+-----------+
| Flannel     | 0.5.5     |
+-------------+-----------+

The following software are managed as systemd services:

- kubelet
- flannel (if specified as network driver)
- docker
- etcd

The following software are managed as Docker containers:

- kube-apiserver
- kube-controller-manager
- kube-scheduler
- kube-proxy

The login for this image is *core*.

Kubernetes on Ironic
--------------------

This image is built manually using diskimagebuilder.  The scripts and instructions
are included in `Magnum code repo
<https://github.com/openstack/magnum/tree/master/magnum/templates/kubernetes/elements>`_.
Currently Ironic is not fully supported yet, therefore more details will be
provided when this driver has been fully tested.


Swarm on Fedora Atomic
----------------------

This image is the same as the image for `Kubernetes on Fedora Atomic`_
described above.  The login for this image is *fedora*.

Mesos on Ubuntu
---------------

This image is built manually using diskimagebuilder.  The instructions are
provided in this `Mesos guide
<https://github.com/openstack/magnum/blob/master/doc/source/dev/mesos.rst>`_.
The Fedora site hosts the current image `ubuntu-14.04.3-mesos-0.25.0.qcow2
<https://fedorapeople.org/groups/magnum/ubuntu-14.04.3-mesos-0.25.0.qcow2>`_.

+-------------+-----------+
| OS/software | version   |
+=============+===========+
| Ubuntu      | 14.04     |
+-------------+-----------+
| Docker      | 1.8.1     |
+-------------+-----------+
| Mesos       | 0.25.0    |
+-------------+-----------+
| Marathon    | 0.11.1    |
+-------------+-----------+

============
Notification
============

Magnum provides notifications about usage data so that 3rd party applications
can use the data for auditing, billing, monitoring, or quota purposes. This
document describes the current inclusions and exclusions for Magnum
notifications.

Magnum uses Cloud Auditing Data Federation (`CADF`_) Notification as its
notification format for better support of auditing, details about CADF are
documented below.

Auditing with CADF
------------------

Magnum uses the `PyCADF`_ library to emit CADF notifications, these events
adhere to the DMTF `CADF`_ specification. This standard provides auditing
capabilities for compliance with security, operational, and business processes
and supports normalized and categorized event data for federation and
aggregation.

.. _PyCADF: http://docs.openstack.org/developer/pycadf
.. _CADF: http://www.dmtf.org/standards/cadf

Below table describes the event model components and semantics for
each component:

+-----------------+----------------------------------------------------------+
| model component |  CADF Definition                                         |
+=================+==========================================================+
| OBSERVER        |  The RESOURCE that generates the CADF Event Record based |
|                 |  on its observation (directly or indirectly) of the      |
|                 |  Actual Event.                                           |
+-----------------+----------------------------------------------------------+
| INITIATOR       |  The RESOURCE that initiated, originated, or instigated  |
|                 |  the event's ACTION, according to the OBSERVER.          |
+-----------------+----------------------------------------------------------+
| ACTION          |  The operation or activity the INITIATOR has performed,  |
|                 |  has attempted to perform or has pending against the     |
|                 |  event's TARGET, according to the OBSERVER.              |
+-----------------+----------------------------------------------------------+
| TARGET          |  The RESOURCE against which the ACTION of a CADF Event   |
|                 |  Record was performed, attempted, or is pending,         |
|                 |  according to the OBSERVER.                              |
+-----------------+----------------------------------------------------------+
| OUTCOME         |  The result or status of the ACTION against the TARGET,  |
|                 |  according to the OBSERVER.                              |
+-----------------+----------------------------------------------------------+

The ``payload`` portion of a CADF Notification is a CADF ``event``, which
is represented as a JSON dictionary. For example:

.. code-block:: javascript

    {
        "typeURI": "http://schemas.dmtf.org/cloud/audit/1.0/event",
        "initiator": {
            "typeURI": "service/security/account/user",
            "host": {
                "agent": "curl/7.22.0(x86_64-pc-linux-gnu)",
                "address": "127.0.0.1"
            },
            "id": "<initiator_id>"
        },
        "target": {
            "typeURI": "<target_uri>",
            "id": "openstack:1c2fc591-facb-4479-a327-520dade1ea15"
        },
        "observer": {
            "typeURI": "service/security",
            "id": "openstack:3d4a50a9-2b59-438b-bf19-c231f9c7625a"
        },
        "eventType": "activity",
        "eventTime": "2014-02-14T01:20:47.932842+00:00",
        "action": "<action>",
        "outcome": "success",
        "id": "openstack:f5352d7b-bee6-4c22-8213-450e7b646e9f",
    }

Where the following are defined:

* ``<initiator_id>``: ID of the user that performed the operation
* ``<target_uri>``: CADF specific target URI, (i.e.:  data/security/project)
* ``<action>``: The action being performed, typically:
  ``<operation>``. ``<resource_type>``

Additionally there may be extra keys present depending on the operation being
performed, these will be discussed below.

Note, the ``eventType`` property of the CADF payload is different from the
``event_type`` property of a notifications. The former (``eventType``) is a
CADF keyword which designates the type of event that is being measured, this
can be: `activity`, `monitor` or `control`. Whereas the latter
(``event_type``) is described in previous sections as:
`magnum.<resource_type>.<operation>`

Supported Events
----------------

The following table displays the corresponding relationship between resource
types and operations.

+---------------+----------------------------+-------------------------+
| resource type |    supported operations    |       typeURI           |
+===============+============================+=========================+
| bay           |  create, update, delete    |    service/magnum/bay   |
+---------------+----------------------------+-------------------------+

Example Notification - Bay Create
---------------------------------

The following is an example of a notification that is sent when a bay is
created. This example can be applied for any ``create``, ``update`` or
``delete`` event that is seen in the table above. The ``<action>`` and
``typeURI`` fields will be change.

.. code-block:: javascript

    {
        "event_type": "magnum.bay.created",
        "message_id": "0156ee79-b35f-4cef-ac37-d4a85f231c69",
        "payload": {
            "typeURI": "http://schemas.dmtf.org/cloud/audit/1.0/event",
            "initiator": {
                "typeURI": "service/security/account/user",
                "id": "c9f76d3c31e142af9291de2935bde98a",
                "user_id": "0156ee79-b35f-4cef-ac37-d4a85f231c69",
                "project_id": "3d4a50a9-2b59-438b-bf19-c231f9c7625a"
            },
            "target": {
                "typeURI": "service/magnum/bay",
                "id": "openstack:1c2fc591-facb-4479-a327-520dade1ea15"
            },
            "observer": {
                "typeURI": "service/magnum/bay",
                "id": "openstack:3d4a50a9-2b59-438b-bf19-c231f9c7625a"
            },
            "eventType": "activity",
            "eventTime": "2015-05-20T01:20:47.932842+00:00",
            "action": "create",
            "outcome": "success",
            "id": "openstack:f5352d7b-bee6-4c22-8213-450e7b646e9f",
            "resource_info": "671da331c47d4e29bb6ea1d270154ec3"
        }
        "priority": "INFO",
        "publisher_id": "magnum.host1234",
        "timestamp": "2016-05-20 15:03:45.960280"
    }
