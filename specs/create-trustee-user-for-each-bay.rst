==================================
Create a trustee user for each bay
==================================

https://blueprints.launchpad.net/magnum/+spec/create-trustee-user-for-each-bay

Some services which are running in a bay need to access OpenStack services.
For example, Kubernetes load balancer [1]_ needs to access Neutron. Docker
registry [2]_ needs to access Swift. In order to access OpenStack services,
we can create a trustee for each bay and delegate a limited set of rights to
the trustee. [3]_ and [4]_ give a brief introduction to Keystone's trusts
mechanism.

Problem description
===================

Some services which are running in a bay need to access OpenStack services,
so we need to pass user credentials into the vms.

Use Cases
---------

1. Kubernetes load balancer needs to access Neutron [1]_.
2. For persistent storage, Cloud Provider needs to access Cinder to
   mount/unmount block storage to the node as volume [5]_.
3. TLS cert is generated in the vms and need to be uploaded to Magnum [6]_ and
   [7]_.
4. Docker registry needs to access Swift [2]_.

Project Priority
----------------

High

Proposed change
===============
When a user (the "trustor") wants to create a bay, steps for trust are as
follows.

1. Create a new service account (the "trustee") without any role in a domain
   which is dedicated for trust. Without any role, the service account can do
   nothing in Openstack.

2. Define a trust relationship between the trustor and the trustee. The trustor
   can delegate a limited set of roles to the trustee. We can add an option
   named trust_roles in baymodel. Users can add roles which they want to
   delegate into trust_roles. If trust_roles is not provided, we delegate all
   the roles to the trustee.

3. Services in the bay can access OpenStack services with the trustee
   credentials and the trust.

The roles which are delegated to the trustee should be limited. If the services
in the bay only need access to Neutron, we should not allow the services to
access to other OpenStack services. But there is a limitation that a trustor
must have the role which is delegated to a trustee [4]_.

Magnum now only allows the user who create the bay to get the certificate to
avoid the security risk introduced by Docker [8]_. For example, if other users
in the same tenant can get the certificate, then they can use Docker API to
access the host file system of a bay node and get anything they want::

    docker run --rm -v /:/hostroot ubuntu /bin/bash \
               -c "cat /hostroot/etc/passwd"

If Keystone doesn't allow to create new service accounts when LDAP is used as
the backend for Keystone, we can use a pre-create service account for all
bays. In this situation, all the bays use the same service account and
different trust. We should add an config option to choose this method.

Alternatives
------------

Magnum can create a user for each bay with roles to access OpenStack Services
in a dedicated domain. The method has one disadvantage. The user which is
created by magnum may get the access to OpenStack services which this user can
not access before. For example, a user can not access Swift service and create
a bay. Then Magnum create a service account for this bay with roles to access
Swift. If the user logins into the vms and get the credentials, the user can
use these credentials to access Swift.

Or Magnum doesn't prepare credentials and the user who create a bay needs to
login into the nodes to manully add credentials in config files for services.

Data model impact
-----------------

Trustee id, trustee password and trust id are added to Bay table in Magnum
database.

REST API impact
---------------

Only the user who create a bay can get the certificate of this bay. Other
users in the same tenant can not get the certificate now.

Security impact
---------------

Trustee id and trustee password are encrypted in magnum database. When Magnum
passes these parameters to heat to create a stack, the transmission is
encrypted by tls, so we don't need to encrypt these credentials. These
credentials are hidden in heat, users can not query them in stack parameters.

Trustee id, trustee password and trust id can be obtained in the vms. Anyone
who can login into the vms can get them and use these credentials to access
OpenStack services. In a production environment, these vms must be secured
properly to prevent unauthorized access.

Only the user who create the bay can get the certificate to access the COE
api, so it is not a security risk even if the COE api is not safe.

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

None

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    humble00 (wanghua.humble@gmail.com)
Other contributors:
    None

Work Items
----------

1. Create an trustee for each bay.
2. Change the policy so that only the user who create a bay can get the
   certificate of the bay.

Dependencies
============

None

Testing
=======

Unit test and functional test for service accounts and the policy change.

Documentation Impact
====================

The user guide and troubleshooting guide will be updated with details
regarding the service accounts.

References
==========
.. [1] http://docs.openstack.org/developer/magnum/dev/kubernetes-load-balancer.html
.. [2] https://blueprints.launchpad.net/magnum/+spec/registryv2-in-master
.. [3] http://blogs.rdoproject.org/5858/role-delegation-in-keystone-trusts
.. [4] https://wiki.openstack.org/wiki/Keystone/Trusts
.. [5] https://github.com/kubernetes/kubernetes/blob/release-1.1/examples/mysql-cinder-pd/README.md
.. [6] https://bugs.launchpad.net/magnum/+bug/1503863
.. [7] https://review.openstack.org/#/c/232152/
.. [8] https://docs.docker.com/engine/articles/security/#docker-daemon-attack-surface

History
=======

None
