========================
Magnum Cluster Stats API
========================

Launchpad blueprint:

https://blueprints.launchpad.net/magnum/+spec/magnum-stats-api

This proposal is to add a new Magnum statistics API to provide useful metrics
to OpenStack administrators/service providers as well as users.

Problem Description
-------------------

Currently there is no magnum API to get usage metrics. This specification
document proposes to add a new stats endpoint to Magnum API. The proposed
stats endpoint will provide useful metrics such as overall current usage info
to OpenStack service providers and also non-admin tenants will be able to
fetch tenant scoped statistics.


Use Cases
---------

Below given are some of the use cases that can be addressed by implementing
stats API for Magnum:

1. A Magnum tenant with admin role would like to get the total number of
   active clusters, nodes, floating IPs and Cinder volumes for all active
   tenants.

2. A Magnum tenant with admin role would like to get the total number of
   active clusters, nodes, floating IPs and Cinder volumes for a specific
   tenant.

3. A Magnum tenant without admin role can get the total number of active
   clusters, nodes, floating IPs and Cinder volumes scoped to that tenant.

4. A Magnum tenant would like to discover the sum of allocated server capacity
   for a given cluster (in terms of aggregate vcpu, memory, local storage, and
   cinder volume storage).

5. A Magnum tenant with admin role would like to discover the aggregate server
   capacity (in terms of aggregate vcpu, memory, local storage, and cinder
   volume storage) allocated by all clusters belonging to a specific tenant or
   all the tenants.

Please note that this is not an exhaustive list of use cases and additional
specs will be proposed based on the community needs.


Proposed Changes
----------------

The proposed change is to add a new '/stats' REST API endpoint to Magnum
service that will provide total number of clusters, nodes, floating IPs,
Cinder volumes and also a summary view of server capacity (in terms of
aggregate vcpu, memory, local storage, and cinder volume storage) allocated
to a cluster, or to all the clusters owned by the given tenant or all the
tenants.

1. Add an API that returns total number of clusters, nodes, floating IPs, and
   Cinder volumes of all tenants.

2. Add an API that returns total number of clusters, nodes, floating IPs, and
   Cinder volumes of a specific tenant.

3. Add an API that returns aggregate vcpu, memory, local storage, and cinder
   volume storage for the given cluster.

4. Add an API that returns aggregate vcpu, memory, local storage, and cinder
   volume storage allocated by all clusters belonging to a specific tenant.

5. Update policy.json file to enable access to '/stats' endpoint to owner and
   admin (using a policy rule admin_or_owner).

In the initial implementation stats data will be aggregated from Magnum DB
and/or from other OpenStack services on demand. There will be some interaction
between the conductor and the drivers through an interface. If needed, this
on-demand stats aggregation implementation can be updated in future without
affecting the REST API behavior. For example, if the proposed on-demand data
aggregation is not responsive, Magnum conductor may need to collect the stats
periodically and save in the Magnum DB.

Initial work in progress review [2].


Alternatives
------------

Without proposed stats endpoint, an administrator could use OpenStack clients
to get some basic statistics such as server count, volume count etc. by
relying on the Magnum naming convention. For example, to get nova instance
count:
nova list | grep -e "kube-" -e "swarm-" -e "mesos-" | wc

For the number of cinder volumes:
cinder list | grep "docker_volume" | wc -l

For float IPs count:
openstack ip floating list -f value|wc -l

For clusters count:
magnum cluster-list | grep "CREATE_COMPLETE" | wc -l


Data model impact
-----------------

None, because data will be aggregated and summarized at the time of each stats
API request, so no stats need to be persisted in the data store.

REST API impact
---------------

Add a new REST endpoint '/stats' as shown below:

A GET request with admin role to '/stats?type=cluster' will return the total
clusters, nodes, floating IPs and Cinder volumes for all active tenants.

A GET request without admin role to '/stats?type=cluster' will return the
total clusters, nodes, floating IPs and Cinder volumes for the current tenant.

A GET request with admin role to '/stats?type=cluster&tenant=<tenant-id>' will
return the total clusters, nodes, floating IPs and Cinder volumes for the
given tenant.

A GET request to '/stats?type=cluster&tenant=<tenant-id>' without admin role
will result in HTTP status code 403 (Permission denied) if the requester
tenant-id does not match the tenant-id provided in the URI. If it matches,
stats will be scoped to the requested tenant.


Other Implementation Option
---------------------------

Existing /cluster API can be updated to include stats info as shown below:

A 'GET' request with admin role to '/cluster/stats' will return total active
clusters and nodes across all the tenants.

A 'GET' request to '/cluster/stats/<tenant-id>' will return total clusters and
nodes for the given tenant.

A 'GET' request without admin role to '/cluster/stats/<tenant-id>' will result
in HTTP status code 403 (Permission denied).

This option was discussed and rejected due to the fact that /cluster/stats
collide with /cluster/<cluster-name/id>.


Security impact
---------------

There will be changes to policy.json file that enable access to '/stats'
endpoint to owner and admin (using a policy rule admin_or_owner).

Notifications impact
--------------------

None

Other end user impact
---------------------

New /stats endpoint will be available to users.

Performance impact
------------------

None

Other deployer impact
---------------------

None.

Developer impact
----------------

None

Implementation
--------------

Assignee(s)
-----------

Primary assignee
  vijendar-komalla

Work Items
----------

1. Implement /stats API in Magnum service.

2. Document new API.

3. Update Magnum CLI to expose stats functionality.

Dependencies
------------

None

Testing
-------

1. Since a new stats endpoint will be introduced with this proposal, need to
   update some unit tests.

2. Add unit tests and functional tests for new functionality introduced.

Documentation Impact
--------------------

Update API documentation to include stats API information.

References
----------

[1] - Magnum cluster statistics API blueprint:

https://blueprints.launchpad.net/magnum/+spec/magnum-stats-api

[2] - Proposed change under review:

https://review.openstack.org/391301
