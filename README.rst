======
Magnum
======

new Openstack project for containers.

* Free software: Apache license
* Documentation: http://docs.openstack.org/developer/magnum
* Source: http://git.openstack.org/cgit/stackforge/magnum
* Bugs: http://bugs.launchpad.net/magnum
* ReST Client: http://github.com/stackforge/python-magnumclient

Architecture
------------

There are four different types of objects in the Magnum system:

* Bay: A physical machine or virtual machine where work is scheduled
* Pod: A collection of containers running on one physical or virtual machine
* Service: A port to Pod mapping
* Container: A docker container

Three binaries work together to compose the Magnum system.  The first binary
accessed by the python-magnumclient code is the magnum-api ReST server.  The
ReST server may run as one process or multiple processes.  When a ReST request
is sent to the client API, the request is sent via AMQP to the magnum-backend
process.

The magnum-backend process runs on each machine where a docker server is
running or where a k8s minion is located.  The backend processor contacts the
appropriate backend (for the container object, docker, for the server & pod
objects, k8s).  The backend then executes the operation requested and sends the
results to the third binary.

The third binary, magnum-conductor, reads and writes the database with
information related to the object operated upon.  The conductor then returns
the new object back up the call stack, where it may be used to provide
information to the client or used for processing the operation.  There is only
one magnum-conductor process running.

Features
--------
* Abstractions for bays, pods, services, and containers.
* Integration with Kubernetes and Docker for backend container technology.
* Integration with Keystone for multi-tenant security.
* Integraiton with Neutron for k8s multi-tenancy network security.

Installation
------------
* Configure Keystone

$ source openrc admin admin

$ keystone user-create --name=magnum --pass=<secure-magnum-password> --email=magnum@example.com
$ keystone 1
 keystone service-create --name=container --type=container --description="Magnum Container Service"
$keystone endpoint-create --service=container --publicurl=http://127.0.0.1:9511/v1 --internalurl=http://127.0.0.1:9511/v1 --adminurl=http://127.0.0.1:9511/v1

* Install Magnum

$ git clone http://github.com/stackforge/magnum
$ cd magnum
$ sudo python ./setup.py install
$ cd ..

* Install Magnum's Python Client

$ git clone http://github.com/stackforge/python-magnumclient
$ cd python-magnumclient
$ sudo python ./setup.py install
$ cd ..

Run
---
* Start magnum-api

$ magnum-api &

* Start magnum-conductor

$ magnum-conductor &

* Start magnum-backend (should be started where a docker server or kubernetes
* api server is running

$ magnum-backend &

* Install magnum pythonclient
$ git clone http://github.com/stackforge/python-magnumclient
$ cd python-magnumclient
$ sudo python ./setup.py install

Access Magnum via ReST API
--------------------------

* Note the magnum ReST API is not yet plumbed *

* select a subcommand:
    bay-create
    bay-delete
    bay-list
    bay-show
    container-create
    container-delete
    container-execute
    container-list
    container-logs
    container-pause
    container-reboot
    container-show
    container-start
    container-stop
    container-unpause
    pod-create
    pod-delete
    pod-list
    pod-show
    service-create
    service-delete
    service-list
    service-show

* Run the operation:
$ magnum bay-list
