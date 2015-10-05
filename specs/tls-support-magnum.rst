=====================
TLS support in Magnum
=====================

Launchpad blueprint:

https://blueprints.launchpad.net/magnum/+spec/secure-kubernetes

Currently there is no authentication in Magnum to provide access control to
limit communication between the Magnum service and the Kubernetes service so
that Kubernetes can not be controlled by a third party. This implementation
closes this security loophole by using TLS as an access control mechanism.
Only the Magnum server will have the key to communicate with any given
Kubernetes API service under its control. An additional benefit of this
approach is that communication over the network will be encrypted, reducing
the chance of eavesdropping on the communication stream.

Problem Description
-------------------

Magnum currently controls Kubernetes API services using unauthenticated HTTP.
If an attacker knows the api_address of a Kubernetes Bay, (s)he can control
the cluster without any access control.

Use Cases
---------

1. Operators expect system level control to be protected by access control that
is consistent with industry best practices. Lack of this feature may result in
rejection of Magnum as an option for hosting containerized workloads.

Proposed Changes
----------------

The complete implementation of TLS support in Magnum can be further decomposed
into below smaller implementations.

1. TLS support in Kubernetes Client Code.
-----------------------------------------

The current implementation of Kubernetes Client code doesn't have any
authentication. So this implementation will change the client code to
provide authentication using TLS.

Launchpad blueprint:

https://blueprints.launchpad.net/magnum/+spec/tls-pythonk8sclient

2. Generating certificates
----------------------------

This task is mainly on how certificates for both client(magnum-conductor)
and server(kube-apiserver) will be generated and who will be the certificate
authority(CA).

These files can be generated in two ways:

2.1. Magnum script
-------------------

This implementation will use standard tool to generate certificates and
keys. This script will be registered on Kubernetes master node while creating
bay. This script will generate certificates, start the secure kube-apiserver
and then register the client certificates at Magnum.

2.2. Using Barbican
-------------------

Barbican can also be used as a CA using Dogtag. This implementation will use
Barbican to generate certificates.

3. TLS Support in Magnum code
------------------------------

This work mainly involves deploying a secure bay and supporting the use of
certificates in Magnum to call Kubernetes API. This implementation can be
decomposed into smaller tasks.

3.1. Create secure bay
----------------------

This implementation will deploy a secure kube-apiserver running on Kubernetes
master node. To do so following things needs to be done:

* Generate certificates
* Copy certificates
* Start a secure kube-apiserver

3.1.1. Generate certificates
----------------------------

The certificates will be generated using any of the above implementation in
section 2.

3.1.2. Copy certificates
------------------------

This depends on how cert and key is generated,  the implementation will differ
with each case.

3.1.2.1. Using Magnum script
----------------------------

This script will generate both server and client certificates on Kubernetes
master node. Hence only client certificates needs to be copied to magnum host
node. To copy these files, the script will make a call to magnum-api to store
files.

3.1.2.2. Using Barbican
-----------------------

When using Barbican, the cert and key will be generated and stored in Barbican
itself. Either magnum-conductor can fetch the certificates from Barbican and
copy on Kubernetes master node or it can be fetched from Kubernetes master node
also.

3.1.3. Start a secure kube-apiserver
------------------------------------

Above generated certificates will be used to start a secure kube-apiserver
running on Kubernetes master node.

Now that we have a secure Kubernetes cluster running, any API call to
Kubernetes will be secure.


3.2. Support https
------------------

While running any Kubernetes resource related APIs, magnum-conductor will
fetch certificate from magnum database or Barbican and use it to make secure
API call.

4. Barbican support to store certificates securely
----------------------------------------------------

Barbican is a REST API designed for the secure storage, provisioning and
management of secrets. The client cert and key must be stored securely. This
implementation will support Barbican in Magnum to store the sensitive data.

Data model impact
-----------------

New table 'cert' will be introduced to store the certificates.

REST API impact
---------------

New API /certs will be introduced to store the certificates.

Security impact
---------------

After this support, Magnum will be secure to be used in actual production
environment. Now all the communication to Kubernetes master node will be
secure.
The certificates will be generated by Barbican or standard tool signed by
trusted CAs.
The certificates will be stored safely in Barbican when the Barbican cert
storage option is selected by the administrator.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance impact
------------------

None

Other deployer impact
---------------------

Deployer will need to install Barbican to store certificates.

Developer impact
----------------

None

Implementation
--------------

Assignee(s)
-----------

Primary assignee
  madhuri(Madhuri Kumari)
  yuanying(Motohiro Otsuka)

Work Items
----------

1. TLS Support in Kubernetes Client code
2. Support for generating keys in Magnum
3. Support creating secure Kubernetes cluster
4. Support Barbican in Magnum to store certificates

Dependencies
------------

Barbican(optional)

Testing
-------

Each commit will be accompanied with unit tests. There will also be functional
test to test both good and bad certificates.

Documentation Impact
--------------------

Add a document explaining how TLS cert and keys can be generated and guide
updated with how to use the secure model of bays.


References
----------

None
