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

I deploy pods and services on Kubernetes bay but the app is not working
  The pods and services are running and the status looks correct, but
  if the app is performing communication between pods through services,
  verify `Kubernetes networking`_.

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
The nodes for Kubernetes, Swarm and Mesos are connected to a private
Neutron network, so to provide access to the external internet, a router
connects the private network to a public network.  With devstack, the
default public network is "public", but this can be replaced by the
parameter "external-network-id" in the bay model.  The "public" network
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

**Note:** On the fedora-21-atomic-5 image, ping does not work because
of a known atomic bug.  You can work around this problem by::

    cp /usr/bin/ping .
    sudo ./ping 8.8.8.8

If the ping fails, there is no route to the external internet.
Check the following:

- Is PUBLIC_INTERFACE in devstack/local.conf the correct network
  interface?  Does this interface have a route to the external internet?
- If "external-network-id" is specified in the bay model, does this network
  have a route to the external internet?
- Is your devstack environment behind a firewall?  This can be the case for some
  enterprises or countries.  In this case, consider using a `proxy server
  <https://github.com/openstack/magnum/blob/master/doc/source/magnum-proxy.rst>`_.
- Is the traffic blocked by the security group? Check the
  `rules of security group
  <http://docs.openstack.org/openstack-ops/content/security_groups.html>`_.
- Is your host NAT'ing your internal network correctly? Check your host
  `iptables <http://docs.openstack.org/openstack-ops/content/network_troubleshooting.html#iptables>`_.
- Use *tcpdump* for `networking troubleshooting
  <http://docs.openstack.org/openstack-ops/content/network_troubleshooting.html#tcpdump>`_.
  You can run *tcpdump* on the interface *docker0, flannel0* and *eth0* on the
  node and then run *ping* to see the path of the message from the container.

If ping is successful, check that DNS is working::

    wget google.com

If DNS works, you should get back a few lines of HTML text.

If the name lookup fails, check the following:

- Is the DNS entry correct in the subnet?  Try "neutron subnet-show
  <subnet-id>" for the private subnet and check dns_nameservers.
  The IP should be either the default public DNS 8.8.8.8 or the value
  specified by "dns-nameserver" in the bay model.
- If you are using your own DNS server by specifying "dns-nameserver"
  in the bay model, is it reachable and working?
- More help on `DNS troubleshooting <http://docs.openstack.org/openstack-ops/content/network_troubleshooting.html#debugging_dns_issues>`_.


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
particular driver being used for the bay.

Using Flannel as network driver
...............................

Flannel is the default network driver for Kubernetes bays.  Flannel is
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

- Is Flannel running properly?  check the `flannel service`_.

- Ping and try `tcpdump
  <http://docs.openstack.org/openstack-ops/content/network_troubleshooting.html#tcpdump>`_
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


==============
For Developers
==============

This section is intended to help with issues that developers may
run into in the course of their development adventures in Magnum.

Troubleshooting in Gate
-----------------------

Simulating gate tests
  *Note*: This is adapted from Devstack Gate's `README`_ which
  is worth a quick read to better understand the following)

  #. Boot a VM like described in the Devstack Gate's `README`_ .
  #. Provision this VM like so::

      apt-get update \
      && apt-get upgrade -y \ # Kernel upgrade, as recommended by README, select to keep existing grub config
      && apt-get install -y git tmux vim \
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
          git://git.openstack.org \
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
      export DEVSTACK_LOCAL_CONFIG="enable_plugin magnum git://git.openstack.org/openstack/magnum"
      export DEVSTACK_LOCAL_CONFIG+=$'\n'"enable_plugin ceilometer git://git.openstack.org/openstack/ceilometer"
      # Keep localrc to be able to set some vars in post_test_hook
      export KEEP_LOCALRC=1
      function gate_hook {
           cd /opt/stack/new/magnum/
          ./magnum/tests/contrib/gate_hook.sh api # change this to swarm to run swarm functional tests or k8s to run kubernetes functional tests
      }
      export -f gate_hook
      function post_test_hook {
          source $BASE/new/devstack/accrc/admin/admin
          cd /opt/stack/new/magnum/
          ./magnum/tests/contrib/post_test_hook.sh api # change this to swarm to run swarm functional tests or k8s to run kubernetes functional tests
      }
      export -f post_test_hook
      cp devstack-gate/devstack-vm-gate-wrap.sh ./safe-devstack-vm-gate-wrap.sh
      ./safe-devstack-vm-gate-wrap.sh

Helpful nuances about the Devstack Gate
  * Main job is in ``project-config``'s `magnum.yaml <https://github.com/openstack-infra/project-config/blob/master/jenkins/jobs/magnum.yaml>`_.

    * Must modify parameters passed in since those are escaped:

      * Anything with ``{}`` should be set as an environment variable

      * Anything with ``{{ }}`` should have those brackets changed to
        single brackets - ``{}``.

      * As with the documentation for Devstack Gate, you can just create
        a new file for the job you want, paste in what you want, then
        ``chmod u+x <filename>`` and run it.

    * Parameters can be found in `projects.yaml <https://github.com/openstack-infra/project-config/blob/master/jenkins/jobs/projects.yaml>`_.
      This file changes a lot, so it's more reliable to say that you can
      search for the magnum jobs where you'll see examples of what
      gets passed in.

  * Three jobs are usually run as a part of Magnum gate, all of with are found in ``project-config``'s `macros.yml <https://github.com/openstack-infra/project-config/blob/master/jenkins/jobs/macros.yaml>`_:

    * link-logs

    * net-info

    * devstack-checkout

  * After you run a job, it's ideal to clean up and start over with a
    fresh VM to best simulate the Devstack Gate environment.

.. _README: https://github.com/openstack-infra/devstack-gate/blob/master/README.rst#simulating-devstack-gate-tests P
