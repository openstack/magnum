A Mesos cluster with Heat
=========================

These `Heat <https://wiki.openstack.org/wiki/Heat>`__ templates will
deploy a `Mesos <http://mesos.apache.org/>`__ cluster.

Requirements
------------

OpenStack
~~~~~~~~~

These templates will work with the Kilo version of Heat.

Guest image
~~~~~~~~~~~

These templates will work with Ubuntu 14.04 base image with the
following middleware pre-installed:

-  ``docker``
-  ``zookeeper``
-  ``mesos``
-  ``marathon``

Building an image
~~~~~~~~~~~~~~~~~

If you do not have a suitable image you can build one easily using one
of two methods:

Disk Image Builder
^^^^^^^^^^^^^^^^^^

`elements <http://git.openstack.org/cgit/openstack/magnum/tree/magnum/templates/mesos/elements/>`__
directory contains `diskimage-builder <http://docs.openstack.org/developer/diskimage-builder>`__
elements to build an image which contains mesos and its frameworks
required to use the heat template mesoscluster.yaml.

Currently, only Ubuntu 14.04 is supported. An example Ubuntu based image
can be built and uploaded to glance as follows:

::

    $ sudo apt-get update
    $ sudo apt-get install git qemu-utils python-pip

    $ git clone https://git.openstack.org/openstack/magnum
    $ git clone https://git.openstack.org/openstack/diskimage-builder.git
    $ git clone https://git.openstack.org/openstack/dib-utils.git
    $ git clone https://git.openstack.org/openstack/tripleo-image-elements.git
    $ git clone https://git.openstack.org/openstack/heat-templates.git
    $ export PATH="${PWD}/dib-utils/bin:$PATH"
    $ export ELEMENTS_PATH=tripleo-image-elements/elements:heat-templates/hot/software-config/elements:magnum/magnum/templates/mesos/elements
    $ export DIB_RELEASE=trusty

    $ diskimage-builder/bin/disk-image-create ubuntu vm docker mesos \
        os-collect-config os-refresh-config os-apply-config \
        heat-config heat-config-script \
        -o ubuntu-mesos.qcow2

    $ glance image-create --name ubuntu-mesos --visibility public \
        --disk-format=qcow2 --container-format=bare \
        --os-distro=ubuntu --file=ubuntu-mesos.qcow2

Docker
^^^^^^

Install docker using ``curl -sSL http://get.docker.com | sudo bash`` or
use the appropriate system packaging.

Use the provided `Dockerfile <http://git.openstack.org/cgit/openstack/magnum/tree/magnum/templates/mesos/Dockerfile>`__ to build the image (it
uses the same DIB scripts as above). The resultant image will be saved
as ``/tmp/ubuntu-mesos.qcow2``

::

    $ sudo docker build -t magnum/mesos-builder .
    $ sudo docker run -v /tmp:/output --rm -ti --privileged magnum/mesos-builder
    ...
    Image file /output/ubuntu-mesos.qcow2 created...
    $ glance image-create --name ubuntu-mesos --visibility public \
            --disk-format=qcow2 --container-format=bare \
            --os-distro=ubuntu --file=/tmp/ubuntu-mesos.qcow2

Creating the stack
------------------

Creating an environment file ``local.yaml`` with parameters specific to
your environment:

::

    parameters:
      ssh_key_name: testkey
      external_network: public
      dns_nameserver: 8.8.8.8
      server_image: ubuntu-mesos

The parameters above will create a stack with one master node. If you want to
create a stack with multiple master nodes (HA mode), create a file like below:

::

    parameters:
      ssh_key_name: testkey
      external_network: public
      dns_nameserver: 8.8.8.8
      server_image: ubuntu-mesos
      number_of_masters: 3

And then create the stack, referencing that environment file:

::

    heat stack-create -f mesoscluster.yaml -e local.yaml my-mesos-cluster

You must provide value for:

-  ``ssh_key_name``

You can optionally provide values for:

-  ``server_image`` (ubuntu-mesos if not provided)
-  ``external_network`` (public if not provided)
-  ``dns_nameserver`` (8.8.8.8 if not provided)

Interacting with Mesos
----------------------

You can get the ip address of the Mesos master using the
``heat output-show`` command:

::

    $ heat output-show my-mesos-cluster mesos_master
    [
      "192.168.200.86"
    ]

You can ssh into that server as the ``ubuntu`` user:

::

    $ ssh ubuntu@192.168.200.86

You can log into your slaves using the ``ubuntu`` user as well. You can
get a list of slaves addresses by running:

::

    $ heat output-show my-mesos-cluster mesos_slaves
    [
      "192.168.200.182"
    ]

Testing
-------

Docker containers can be deployed via Marathon's REST API. Marathon is a
mesos framework for long running applications.

We can 'post' a JSON app description to ``http://${MASTER_IP}:8080/apps`` to deploy a
Docker container. In this example, the ``${MASTER_IP}`` is 192.168.200.86.

::

    $ cat > app.json << END
    {
      "container": {
        "type": "DOCKER",
        "docker": {
          "image": "libmesos/ubuntu"
        }
      },
      "id": "ubuntu",
      "instances": 1,
      "cpus": 0.5,
      "mem": 512,
      "uris": [],
      "cmd": "while sleep 10; do date -u +%T; done"
    }
    END
    $ MASTER_IP=$(heat output-show my-mesos-cluster api_address | tr -d '"')
    $ curl -X POST -H "Content-Type: application/json" \
        http://${MASTER_IP}:8080/v2/apps -d@app.json

Using the Marathon web console (at ``http://${MASTER_IP}:8080/``), you will see the
application you created.

License
-------

Copyright 2015 Huawei Technologies Co.,LTD.

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use these files except in compliance with the License. You may
obtain a copy of the License at

::

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
