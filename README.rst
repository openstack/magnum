======
Magnum
======

new Openstack project for containers.

* Free software: Apache license
* Documentation: http://docs.openstack.org/developer/magnum
* Source: http://git.openstack.org/cgit/stackforge/magnum
* Bugs: http://bugs.launchpad.net/magnum
* ReST Client: http://git.openstack.org/cgit/stackforge/python-magnumclient

Architecture
------------

There are five different types of objects in the Magnum system:

* Bay: A collection of node objects where work is scheduled
* Node: A baremetal or virtual machine where work executes
* Pod: A collection of containers running on one physical or virtual machine
* Service: A port to Pod mapping
* Container: A docker container

Two binaries work together to compose the Magnum system.  The first binary
accessed by the python-magnumclient code is the magnum-api ReST server.  The
ReST server may run as one process or multiple processes.  When a ReST request
is sent to the client API, the request is sent via AMQP to the magnum-backend
process.  The ReST server is horizontally scalable.  AT this time, the backend
is limited to one process, but we intend to add horizontal scalability to the
backend as well.

The magnum-backend process runs on a controller machine and connects to a
kubernetes or docker ReST API endpoint.  The kubernetes and docker ReST API
endpoints are managed by the bay object.

When service or pod objects are created, Kubernetes is directly contacted via
the k8s ReST API.  When container objects are acted upon, the docker ReST API
is directly contacted.

Features
--------
* Abstractions for bays, containers, nodes, pods, and services
* Integration with Kubernetes and Docker for backend container technology.
* Integration with Keystone for multi-tenant security.
* Integraiton with Neutron for k8s multi-tenancy network security.

Installation and Usage
----------------------
* Getting Started Guides: [doc/source/dev/dev-quickstart.rst](doc/source/dev/dev-quickstart.rst)
