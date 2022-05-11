.. _magnum_troubleshooting_guide:

============================
Magnum Troubleshooting Guide
============================

This guide is intended for users who use Magnum to deploy and manage
clusters of hosts for a Container Orchestration Engine.  It describes
common failure conditions and techniques for troubleshooting.  To help
the users quickly identify the relevant information, the guide is
organized as a list of failure symptoms: each has some suggestions
with pointers to the details for troubleshooting.

A separate section `for developers`_ describes useful techniques such as
debugging unit tests and gate tests.

Failure symptoms
================

My cluster-create takes a really long time
  If you are using devstack on a small VM, cluster-create will take a long
  time and may eventually fail because of insufficient resources.
  Another possible reason is that a process on one of the nodes is hung
  and heat is still waiting on the signal.  In this case, it will eventually
  fail with a timeout, but since heat has a long default timeout, you can
  look at the `heat stacks`_ and check the WaitConditionHandle resources.

My cluster-create fails with error: "Failed to create trustee XXX in domain XXX"
  Check the `trustee for cluster`_

Kubernetes cluster-create fails
  Check the `heat stacks`_, log into the master nodes and check the
  `Kubernetes services`_ and `etcd service`_.

Swarm cluster-create fails
  Check the `heat stacks`_, log into the master nodes and check the `Swarm
  services`_ and `etcd service`_.

I get the error "Timed out waiting for a reply" when deploying a pod
  Verify the `Kubernetes services`_ and `etcd service`_ are running on the
  master nodes.

I deploy pods on Kubernetes cluster but the status stays "Pending"
  The pod status is "Pending" while the Docker image is being downloaded,
  so if the status does not change for a long time, log into the minion
  node and check for `Cluster internet access`_.

I deploy pods and services on Kubernetes cluster but the app is not working
  The pods and services are running and the status looks correct, but
  if the app is performing communication between pods through services,
  verify `Kubernetes networking`_.

Swarm cluster is created successfully but I cannot deploy containers
  Check the `Swarm services`_ and `etcd service`_ on the master nodes.

I get a "Protocol violation" error when deploying a container
  For Kubernetes, check the `Kubernetes services`_ to verify that
  kube-apiserver is running to accept the request.
  Check `TLS`_ and `Barbican service`_.

My cluster-create fails with a resource error on docker_volume
  Check for available volume space on Cinder and the `request volume
  size`_ in the heat template.
  Run "nova volume-list" to check the volume status.


Troubleshooting details
=======================

Heat stacks
-----------
*To be filled in*

A cluster is deployed by a set of heat stacks:  one top level stack and several
nested stack.  The stack names are prefixed with the cluster name and the
nested stack names contain descriptive internal names like *kube_masters*,
*kube_minions*.

To list the status of all the stacks for a cluster:

    heat stack-list -n | grep *cluster-name*

If the cluster has failed, then one or more of the heat stacks would have
failed. From the stack list above, look for the stacks that failed, then
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
services`_ or `Swarm services`_.  If the failure is in
other scripts, look for them as `Heat software resource scripts`_.


Trustee for cluster
-------------------
When a user creates a cluster, Magnum will dynamically create a service account
for the cluster. The service account will be used by the cluster to
access the OpenStack services (i.e. Neutron, Swift, etc.). A trust relationship
will be created between the user who created the cluster (the "trustor") and
the service account created for the cluster (the "trustee"). For details,
please refer to
`Create a trustee user for each bay <https://opendev.org/openstack/magnum/src/branch/master/specs/create-trustee-user-for-each-bay.rst>`_.

If Magnum fails to create the trustee, check the magnum config file (usually
in /etc/magnum/magnum.conf). Make sure 'trustee_*' and 'www_authenticate_uri'
are set and their values are correct:

    [keystone_authtoken]
    www_authenticate_uri = http://controller:5000/v3
    ...

    [trust]
    trustee_domain_admin_password = XXX
    trustee_domain_admin_id = XXX
    trustee_domain_id = XXX

If the 'trust' group is missing, you might need to create the trustee domain
and the domain admin:

.. code-block:: bash

    . /opt/stack/devstack/accrc/admin/admin
    export OS_IDENTITY_API_VERSION=3
    unset OS_AUTH_TYPE
    openstack domain create magnum
    openstack user create trustee_domain_admin --password secret \
        --domain magnum
    openstack role add --user=trustee_domain_admin --user-domain magnum \
        --domain magnum admin

    . /opt/stack/devstack/functions
    export MAGNUM_CONF=/etc/magnum/magnum.conf
    iniset $MAGNUM_CONF trust trustee_domain_id \
        $(openstack domain show magnum | awk '/ id /{print $4}')
    iniset $MAGNUM_CONF trust trustee_domain_admin_id \
        $(openstack user show trustee_domain_admin | awk '/ id /{print $4}')
    iniset $MAGNUM_CONF trust trustee_domain_admin_password secret

Then, restart magnum-api and magnum-cond to pick up the new configuration.
If the problem still exists, you might want to manually verify your domain
admin credential to ensure it has the right privilege. To do that, run the
script below with the credentials replaced (you must use the IDs where
specified). If it fails, that means the credential you provided is invalid.

.. code-block:: python

    from keystoneauth1.identity import v3 as ka_v3
    from keystoneauth1 import session as ka_session
    from keystoneclient.v3 import client as kc_v3

    auth = ka_v3.Password(
        auth_url=YOUR_AUTH_URI,
        user_id=YOUR_TRUSTEE_DOMAIN_ADMIN_ID,
        domain_id=YOUR_TRUSTEE_DOMAIN_ID,
        password=YOUR_TRUSTEE_DOMAIN_ADMIN_PASSWORD)

    session = ka_session.Session(auth=auth)
    domain_admin_client = kc_v3.Client(session=session)
    user = domain_admin_client.users.create(
        name='anyname',
        password='anypass')


TLS
---
In production deployments, operators run the OpenStack APIs using
ssl certificates and in private clouds it is common to use self-signed
or certificates signed from CAs that they are usually not included
in the systems' default CA-bundles. Magnum clusters with TLS enabled
have their own CA but they need to make requests to the OpenStack
APIs for several reasons. Eg Get the cluster CA and sign node
certificates (Keystone, Magnum), signal the Heat API for stack
completion, create resources (volumes, load balancers) or get
information for each node (Cinder, Neutron, Nova). In these cases,
the cluster nodes need the CA used for to run the APIs.

To pass the OpenStack CA bundle to the nodes you can set the CA
using the `openstack_ca_file` option in the `drivers` section of
Magnum's configuration file (usually `/etc/magnum/magnum.conf`).
The default drivers in magnum install this CA in the system and
set it in all the places it might be needed (eg when configuring
the kubernetes cloud provider or for the heat-agents.)

The cluster nodes will validate the Certificate Authority by default
when making requests to the OpenStack APIs (Keystone, Magnum, Heat).
If you need to disable CA validation, the configuration parameter
verify_ca can be set to False.  More information on `CA Validation
<https://bugs.launchpad.net/magnum/+bug/1663757>`_.


Barbican service
----------------
*To be filled in*


Cluster internet access
-----------------------
The nodes for Kubernetes and Swarm are connected to a private
Neutron network, so to provide access to the external internet, a router
connects the private network to a public network.  With devstack, the
default public network is "public", but this can be replaced by the
parameter "external-network" in the ClusterTemplate.  The "public" network
with devstack is actually not a real external network, so it is in turn
routed to the network interface of the host for devstack.  This is
configured in the file local.conf with the variable PUBLIC_INTERFACE,
for example::

    PUBLIC_INTERFACE=eth1

If the route to the external internet is not set up properly, the ectd
discovery would fail (if using public discovery) and container images
cannot be downloaded, among other failures.

First, check for connectivity to the external internet by pinging
an external IP (the IP shown here is an example; use an IP that
works in your case)::

    ping 8.8.8.8

If the ping fails, there is no route to the external internet.
Check the following:

- Is PUBLIC_INTERFACE in devstack/local.conf the correct network
  interface?  Does this interface have a route to the external internet?
- If "external-network" is specified in the ClusterTemplate, does this
  network have a route to the external internet?
- Is your devstack environment behind a firewall?  This can be the
  case for some
  enterprises or countries.  In this case, consider using a
  :doc:`proxy server </admin/magnum-proxy>`.
- Is the traffic blocked by the security group? Check the
  `rules of security group
  <https://docs.openstack.org/operations-guide/ops-user-facing-operations.html#security-groups>`_.
- Is your host NAT'ing your internal network correctly? Check your host
  `iptables <https://docs.openstack.org/operations-guide/ops-network-troubleshooting.html#iptables>`_.
- Use *tcpdump* for `networking troubleshooting
  <https://docs.openstack.org/operations-guide/ops-network-troubleshooting.html#tcpdump>`_.
  You can run *tcpdump* on the interface *docker0, flannel0* and *eth0* on the
  node and then run *ping* to see the path of the message from the container.

If ping is successful, check that DNS is working::

    wget google.com

If DNS works, you should get back a few lines of HTML text.

If the name lookup fails, check the following:

- Is the DNS entry correct in the subnet?  Try "neutron subnet-show
  <subnet-id>" for the private subnet and check dns_nameservers.
  The IP should be either the default public DNS 8.8.8.8 or the value
  specified by "dns-nameserver" in the ClusterTemplate.
- If you are using your own DNS server by specifying "dns-nameserver"
  in the ClusterTemplate, is it reachable and working?
- More help on `DNS troubleshooting <https://docs.openstack.org/operations-guide/ops-network-troubleshooting.html#debugging-dns-issues>`_.


Kubernetes networking
---------------------

The networking between pods is different and separate from the neutron
network set up for the cluster.
Kubernetes presents a flat network space for the pods and services
and uses different network drivers to provide this network model.

It is possible for the pods to come up correctly and be able to connect
to the external internet, but they cannot reach each other.
In this case, the app in the pods may not be working as expected.
For example, if you are trying the `redis example
<https://github.com/kubernetes/kubernetes/blob/release-1.1/examples/redis/README.md>`_,
the key:value may not be replicated correctly.  In this case, use the
following steps to verify the inter-pods networking and pinpoint problems.

Since the steps are specific to the network drivers, refer to the
particular driver being used for the cluster.

Using Flannel as network driver
...............................

Flannel is the default network driver for Kubernetes clusters.  Flannel is
an overlay network that runs on top of the neutron network.  It works by
encapsulating the messages between pods and forwarding them to the
correct node that hosts the target pod.

First check the connectivity at the node level.  Log into two
different minion nodes, e.g. node A and node B, run a docker container
on each node, attach to the container and find the IP.

For example, on node A::

    sudo docker run -it alpine
    # ip -f inet -o a | grep eth0 | awk '{print $4}'
    10.100.54.2/24

Similarly, on node B::

    sudo docker run -it alpine
    # ip -f inet -o a | grep eth0 | awk '{print $4}'
    10.100.49.3/24

Check that the containers can see each other by pinging from one to another.

On node A::

    # ping 10.100.49.3
    PING 10.100.49.3 (10.100.49.3): 56 data bytes
    64 bytes from 10.100.49.3: seq=0 ttl=60 time=1.868 ms
    64 bytes from 10.100.49.3: seq=1 ttl=60 time=1.108 ms

Similarly, on node B::

    # ping 10.100.54.2
    PING 10.100.54.2 (10.100.54.2): 56 data bytes
    64 bytes from 10.100.54.2: seq=0 ttl=60 time=2.678 ms
    64 bytes from 10.100.54.2: seq=1 ttl=60 time=1.240 ms

If the ping is not successful, check the following:

- Is neutron working properly?  Try pinging between the VMs.

- Are the docker0 and flannel0 interfaces configured correctly on the
  nodes? Log into each node and find the Flannel CIDR by::

    cat /run/flannel/subnet.env | grep FLANNEL_SUBNET
    FLANNEL_SUBNET=10.100.54.1/24

  Then check the interfaces by::

    ifconfig flannel0
    ifconfig docker0

  The correct configuration should assign flannel0 with the "0" address
  in the subnet, like *10.100.54.0*, and docker0 with the "1" address, like
  *10.100.54.1*.

- Verify the IP's assigned to the nodes as found above are in the correct
  Flannel subnet.  If this is not correct, the docker daemon is not configured
  correctly with the parameter *--bip*.  Check the systemd service for docker.

- Is Flannel running properly?  check the `Running Flannel`_.

- Ping and try `tcpdump
  <https://docs.openstack.org/operations-guide/ops-network-troubleshooting.html#tcpdump>`_
  on each network interface along the path between two nodes
  to see how far the message is able to travel.
  The message path should be as follows:

  1. Source node: docker0
  2. Source node: flannel0
  3. Source node: eth0
  4. Target node: eth0
  5. Target node: flannel0
  6. Target node: docker0

If ping works, this means the flannel overlay network is functioning
correctly.

The containers created by Kubernetes for pods will be on the same IP
subnet as the containers created directly in Docker as above, so they
will have the same connectivity.  However, the pods still may not be
able to reach each other because normally they connect through some
Kubernetes services rather than directly.  The services are supported
by the kube-proxy and rules inserted into the iptables, therefore
their networking paths have some extra hops and there may be problems
here.

To check the connectivity at the Kubernetes pod level, log into the
master node and create two pods and a service for one of the pods.
You can use the examples provided in the directory
*/etc/kubernetes/examples/* for the first pod and service.  This will
start up an nginx container and a Kubernetes service to expose the
endpoint.  Create another manifest for a second pod to test the
endpoint::

    cat > alpine.yaml << END
    apiVersion: v1
    kind: Pod
    metadata:
      name: alpine
    spec:
      containers:
      - name: alpine
        image: alpine
        args:
        - sleep
        - "1000000"
    END

    kubectl create -f /etc/kubernetes/examples/pod-nginx-with-label.yaml
    kubectl create -f /etc/kubernetes/examples/service.yaml
    kubectl create -f alpine.yaml

Get the endpoint for the nginx-service, which should route message to the pod
nginx::

    kubectl describe service nginx-service | grep -e IP: -e Port:
    IP:                     10.254.21.158
    Port:                   <unnamed>       8000/TCP

Note the IP and port to use for checking below.  Log into the node
where the *alpine* pod is running.  You can find the hosting node by
running this command on the master node::

    kubectl get pods -o wide  | grep alpine | awk '{print $6}'
    k8-gzvjwcooto-0-gsrxhmyjupbi-kube-minion-br73i6ans2b4

To get the IP of the node, query Nova on devstack::

    nova list

On this hosting node, attach to the *alpine* container::

    export DOCKER_ID=`sudo docker ps | grep k8s_alpine | awk '{print $1}'`
    sudo docker exec -it $DOCKER_ID sh

From the *alpine* pod, you can try to reach the nginx pod through the nginx
service using the IP and Port found above::

    wget 10.254.21.158:8000

If the connection is successful, you should receive the file *index.html* from
nginx.

If the connection is not successful, you will get an error message like::xs

    wget: can't connect to remote host (10.100.54.9): No route to host

In this case, check the following:

- Is kube-proxy running on the nodes? It runs as a container on each node.
  check by logging in the minion nodes and run::

    sudo docker ps | grep k8s_kube-proxy

- Check the log from kube-proxy by running on the minion nodes::

    export PROXY=`sudo docker ps | grep "hyperkube proxy" | awk '{print $1}'`
    sudo docker logs $PROXY

- Try additional `service debugging
  <https://github.com/kubernetes/kubernetes/blob/release-1.1/docs/user-guide/debugging-services.md>`_.
  To see what's going during provisioning::

    kubectl get events

  To get information on a service in question::

    kubectl describe services <service_name>



etcd service
------------

The etcd service is used by many other components for key/value pair
management, therefore if it fails to start, these other components
will not be running correctly either.
Check that etcd is running on the master nodes by::

    sudo service etcd status -l

If it is running correctly, you should see that the service is
successfully deployed::

    Active: active (running) since ....

The log message should show the service being published::

    etcdserver: published {Name:10.0.0.5 ClientURLs:[http://10.0.0.5:2379]} to cluster 3451e4c04ec92893

In some cases, the service may show as *active* but may still be stuck
in discovery mode and not fully operational.  The log message may show
something like::

    discovery: waiting for other nodes: error connecting to https://discovery.etcd.io, retrying in 8m32s

If this condition persists, check for `Cluster internet access`_.

If the daemon is not running, the status will show the service as failed,
something like::

    Active: failed (Result: timeout)

In this case, try restarting etcd by::

    sudo service etcd start

If etcd continues to fail, check the following:

- Check the log for etcd::

    sudo journalctl -u etcd

- etcd requires discovery, and the default discovery method is the
  public discovery service provided by etcd.io; therefore, a common
  cause of failure is that this public discovery service is not
  reachable.  Check by running on the master nodes::

    . /etc/sysconfig/heat-params
    curl $ETCD_DISCOVERY_URL

  You should receive something like::

    {"action":"get",
     "node":{"key":"/_etcd/registry/00a6b00064174c92411b0f09ad5466c6",
             "dir":true,
             "nodes":[
               {"key":"/_etcd/registry/00a6b00064174c92411b0f09ad5466c6/7d8a68781a20c0a5",
                "value":"10.0.0.5=http://10.0.0.5:2380",
                "modifiedIndex":978239406,
                "createdIndex":978239406}],
             "modifiedIndex":978237118,
             "createdIndex":978237118}
    }

  The list of master IP is provided by Magnum during cluster deployment,
  therefore it should match the current IP of the master nodes.
  If the public discovery service is not reachable, check the
  `Cluster internet access`_.

Running Flannel
---------------

When deploying a COE, Flannel is available as a network driver for
certain COE type.  Magnum currently supports Flannel for a Kubernetes
or Swarm cluster.

Flannel provides a flat network space for the containers in the cluster:
they are allocated IP in this network space and they will have connectivity
to each other.  Therefore, if Flannel fails, some containers will not
be able to access services from other containers in the cluster.  This can be
confirmed by running *ping* or *curl* from one container to another.

The Flannel daemon is run as a systemd service on each node of the cluster.
To check Flannel, run on each node::

    sudo service flanneld status

If the daemon is running, you should see that the service is successfully
deployed::

    Active: active (running) since ....

If the daemon is not running, the status will show the service as failed,
something like::

    Active: failed (Result: timeout) ....

or::

    Active: inactive (dead) ....

Flannel daemon may also be running but not functioning correctly.
Check the following:

- Check the log for Flannel::

    sudo journalctl -u flanneld

- Since Flannel relies on etcd, a common cause for failure is that the
  etcd service is not running on the master nodes.  Check the `etcd service`_.
  If the etcd service failed, once it has been restored successfully, the
  Flannel service can be restarted by::

    sudo service flanneld restart

- Magnum writes the configuration for Flannel in a local file on each master
  node.  Check for this file on the master nodes by::

    cat /etc/sysconfig/flannel-network.json

  The content should be something like::

    {
      "Network": "10.100.0.0/16",
      "Subnetlen": 24,
      "Backend": {
        "Type": "udp"
      }
    }

  where the values for the parameters must match the corresponding
  parameters from the ClusterTemplate.

  Magnum also loads this configuration into etcd, therefore, verify
  the configuration in etcd by running *etcdctl* on the master nodes::

    . /etc/sysconfig/flanneld
    etcdctl get $FLANNEL_ETCD_KEY/config

- Each node is allocated a segment of the network space.  Check
  for this segment on each node by::

    grep FLANNEL_SUBNET /run/flannel/subnet.env

  The containers on this node should be assigned an IP in this range.
  The nodes negotiate for their segment through etcd, and you can use
  *etcdctl* on the master node to query the network segment associated
  with each node::

    . /etc/sysconfig/flanneld
    for s in `etcdctl ls $FLANNEL_ETCD_KEY/subnets`
    do
    echo $s
    etcdctl get $s
    done

    /atomic.io/network/subnets/10.100.14.0-24
    {"PublicIP":"10.0.0.5"}
    /atomic.io/network/subnets/10.100.61.0-24
    {"PublicIP":"10.0.0.6"}
    /atomic.io/network/subnets/10.100.92.0-24
    {"PublicIP":"10.0.0.7"}

  Alternatively, you can read the full record in ectd by::

    curl http://<master_node_ip>:2379/v2/keys/coreos.com/network/subnets

  You should receive a JSON snippet that describes all the segments
  allocated.

- This network segment is passed to Docker via the parameter *--bip*.
  If this is not configured correctly, Docker would not assign the correct
  IP in the Flannel network segment to the container.  Check by::

    cat /run/flannel/docker
    ps -aux | grep docker

- Check the interface for Flannel::

    ifconfig flannel0

  The IP should be the first address in the Flannel subnet for this node.

- Flannel has several different backend implementations and they have
  specific requirements.  The *udp* backend is the most general and have
  no requirement on the network.  The *vxlan* backend requires vxlan
  support in the kernel, so ensure that the image used does provide
  vxlan support.  The *host-gw* backend requires that all the hosts are
  on the same L2 network.  This is currently met by the private Neutron
  subnet created by Magnum;  however, if other network topology is used
  instead, ensure that this requirement is met if *host-gw* is used.

Current known limitation:  the image fedora-21-atomic-5.qcow2 has
Flannel version 0.5.0.  This version has known bugs that prevent the
backend vxland and host-gw to work correctly.  Only the backend udp
works for this image.  Version 0.5.3 and later should work correctly.
The image fedora-21-atomic-7.qcow2 has Flannel version 0.5.5.

Kubernetes services
-------------------
*To be filled in*

(How to introspect k8s when heat works and k8s does not)

Additional `Kubernetes troubleshooting section
<https://kubernetes.io/docs/tasks/debug-application-cluster/troubleshooting/>`_
is available in the Monitoring, Logging, and Debugging section.

Swarm services
--------------
*To be filled in*

(How to check on a swarm cluster: see membership information, view master,
agent containers)


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


For Developers
==============

This section is intended to help with issues that developers may
run into in the course of their development adventures in Magnum.

Troubleshooting in Gate
-----------------------

Simulating gate tests

  #. Boot a VM
  #. Provision this VM like so::

      apt-get update \
      && apt-get upgrade \ # Kernel upgrade, as recommended by README, select to keep existing grub config
      && apt-get install git tmux vim \
      && git clone https://git.openstack.org/openstack-infra/system-config \
      && system-config/install_puppet.sh && system-config/install_modules.sh \
      && puppet apply \
      --modulepath=/root/system-config/modules:/etc/puppet/modules \
      -e "class { openstack_project::single_use_slave: install_users => false,
      ssh_key => \"$( cat .ssh/authorized_keys | awk '{print $2}' )\" }" \
      && echo "jenkins ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers \
      && cat ~/.ssh/authorized_keys >> /home/jenkins/.ssh/authorized_keys
  #. Compare ``~/.ssh/authorized_keys`` and ``/home/jenkins/.ssh/authorized_keys``.  Your original public SSH key should now be in ``/home/jenkins/.ssh/authorized_keys``.  If it's not, explicitly copy it (this can happen if you spin up a using ``--key-name <name>``, for example).
  #. Assuming all is well up to this point, now it's time to ``reboot`` into the latest kernel
  #. Once you're done booting into the new kernel, log back in as ``jenkins`` user to continue with setting up the simulation.
  #. Now it's time to set up the workspace::

      export REPO_URL=https://git.openstack.org
      export WORKSPACE=/home/jenkins/workspace/testing
      export ZUUL_URL=/home/jenkins/workspace-cache2
      export ZUUL_REF=HEAD
      export ZUUL_BRANCH=master
      export ZUUL_PROJECT=openstack/magnum
      mkdir -p $WORKSPACE
      git clone $REPO_URL/$ZUUL_PROJECT $ZUUL_URL/$ZUUL_PROJECT \
      && cd $ZUUL_URL/$ZUUL_PROJECT \
      && git checkout remotes/origin/$ZUUL_BRANCH
  #. At this point, you may be wanting to test a specific change. If so, you can pull down the changes in ``$ZUUL_URL/$ZUUL_PROJECT`` directory::

      cd $ZUUL_URL/$ZUUL_PROJECT \
      && git fetch https://review.openstack.org/openstack/magnum refs/changes/83/247083/12 && git checkout FETCH_HEAD
  #. Now you're ready to pull down the ``devstack-gate`` scripts that will let you run the gate job on your own VM::

      cd $WORKSPACE \
      && git clone --depth 1 $REPO_URL/openstack-infra/devstack-gate
  #. And now you can kick off the job using the following script (the ``devstack-gate`` documentation suggests just copying from the job which can be found in the `project-config <https://github.com/openstack-infra/project-config>`_ repository), naturally it should be executable (``chmod u+x <filename>``)::

      #!/bin/bash -xe
      cat > clonemap.yaml << EOF
      clonemap:
        - name: openstack-infra/devstack-gate
          dest: devstack-gate
      EOF
      /usr/zuul-env/bin/zuul-cloner -m clonemap.yaml --cache-dir /opt/git \
          https://git.openstack.org \
          openstack-infra/devstack-gate
      export PYTHONUNBUFFERED=true
      export DEVSTACK_GATE_TIMEOUT=240 # bump this if you see timeout issues.  Default is 120
      export DEVSTACK_GATE_TEMPEST=0
      export DEVSTACK_GATE_NEUTRON=1
      # Enable tempest for tempest plugin
      export ENABLED_SERVICES=tempest
      export BRANCH_OVERRIDE="default"
      if [ "$BRANCH_OVERRIDE" != "default" ] ; then
          export OVERRIDE_ZUUL_BRANCH=$BRANCH_OVERRIDE
      fi
      export PROJECTS="openstack/magnum $PROJECTS"
      export PROJECTS="openstack/python-magnumclient $PROJECTS"
      export PROJECTS="openstack/barbican $PROJECTS"
      export DEVSTACK_LOCAL_CONFIG="enable_plugin magnum https://git.openstack.org/openstack/magnum"
      export DEVSTACK_LOCAL_CONFIG+=$'\n'"enable_plugin ceilometer https://git.openstack.org/openstack/ceilometer"
      # Keep localrc to be able to set some vars in post_test_hook
      export KEEP_LOCALRC=1
      function gate_hook {
           cd /opt/stack/new/magnum/
          ./magnum/tests/contrib/gate_hook.sh api # change this to swarm to run swarm functional tests or k8s to run kubernetes functional tests
      }
      export -f gate_hook
      function post_test_hook {
          . $BASE/new/devstack/accrc/admin/admin
          cd /opt/stack/new/magnum/
          ./magnum/tests/contrib/post_test_hook.sh api # change this to swarm to run swarm functional tests or k8s to run kubernetes functional tests
      }
      export -f post_test_hook
      cp devstack-gate/devstack-vm-gate-wrap.sh ./safe-devstack-vm-gate-wrap.sh
      ./safe-devstack-vm-gate-wrap.sh
