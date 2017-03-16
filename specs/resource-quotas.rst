..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================
Quota for Magnum Resources
==========================

Launchpad blueprint:

https://blueprints.launchpad.net/magnum/+spec/resource-quota

There are multiple ways to slice an OpenStack cloud. Imposing quota on these
various slices puts a limitation on the amount of resources that can be
consumed which helps to guarantee "fairness" or fair distribution of resource
at the creation time. If a particular project needs more resources, the
concept of quota, gives the ability to increase the resource count on-demand,
given that the system constraints are not exceeded.


Problem description
===================
At present in Magnum we don't have the concept of Quota on Magnum resources as
a result of which, as long as the underlying Infrastructure as a Service(IaaS)
layer has resources, any user can consume as many resources as they want, with
the hardlimit associated with the tenant/project being the upper bound for the
resources to be consumed. Quotas are tied closely to physical resources and are
billable entity and hence from Magnum's perspective it makes sense to limit the
creation and consumption of a particular kind of resource to a certain value.

Use cases
---------
Alice is the admin. She would like to have the feature which will give her
details of Magnum resource consumption so that she can manage her resource
appropriately.

a. Ability to know current resource consumption.
b. Ability to prohibit overuse by a project.
c. Prevent situation where users in the project get starved because users in
   other project consume all the resources. Alice feels something like
   "Quota Management" would help to guarantee "fairness".
d. Prevent DOS kind of attack, abuse or error by users where an excessive
   amount of resources are created.

Proposed change
===============
Proposed change is to introduce a Quota Table which will primarily store the
quota assigned to each resource in a project. For Mitaka, we will restrict
the scope to a Bay, which are Magnum resources. Primarily, as a first step we
will start of by imposing quota on number of bays to be created in a project.
The change also plans to introduce REST API's to GET/PUT/POST/DELETE. CLIs to
get information of Quota for a particular project will also be provided.

For Mitaka, we will restrict the scope of the resources explicit created and
managed by Magnum. Specifically for Mitaka we will focus on number of
Bays only. Going ahead we might add Quota for containers, etc. The resources
of which a Bay is constructed out of is inherently not only Magnum resource
but involve resource from Nova, Cinder, Neutron etc. Limiting those resource
consumption is out of the scope of this spec and needs a close collaboration
with the quota management framework of the orchestration layer, since the
orchestration layer can invoke the respective IaaS projects API's and get the
consumption details before provisioning. As of now the orchestration layer
used by Magnum, Heat, does not have the concept of Quota, so we will start with
imposing Quota on resources which Magnum manages, Bay, more specifically for
Mitaka.

When a project is created and if the Magnum service is running, the default
quota for Magnum resources will be set by the values configured in magnum.conf.
Other Openstack projects like Nova [2]_, Cinder [3]_ follow a similar pattern
and we will also do so and hence won't have a separate CLI for quota-create.
Later if the user wants to change the Quota of the resource option will be
provided to do so using magnum quota-update. In situation where all of the
quota for a specific Magnum resource (Bay) has been consumed and is
under use, admin will be allowed to set the quota to a any value lower than
the usage or hardlimit to prohibit users from the project to create new
Bays. This gives more flexibility to the admin to have a better control
on resource consumption. Till the time the resource is not explicitly deleted
the quota associated with the project, for a particular resource, won't be
decreased. In short quota-update support will take into consideration the
new hardlimit for a resource, specified by the admin, and will set the new
value for this resource.

Before the resource is created, Magnum will check for current count of the
resource(Bays) created for a project. If the resource(Bay) count is less
than the hardlimit set for the Bay, new Bay creation will be allowed. Since
Bay creation is a long running operation, special care will be taken while
computing the available quota. For example, 'in-progress' field in the Quota
usages table will be updated when the resource(Bay) creation is initiated and
is in progress. Lets say the quota hardlimit is 5 and 3 Bay's have already been
created and two new requests come in to create new Bays. Since we have 3 Bays
already created the 'used' field will be set to 3. Now the 'in-progress'
field will be set to 2 till the time the Bay creation is successful. Once
the Bay creation is done this field will be reset to 0, and the 'used'
count will be updated from 3 to 5. So at this moment, hardlimit is 5, used
is 5 and in-progress is 0. So lets say one more request comes in to create
new Bay this request will be prohibited since there is not enough quota
available.

For Bays,

available = hard_limit - [in_progress + used]

In general,

Resource quota available = Resource hard_limit - [
(Resource creation in progress + Resources already created for project)]

Alternatives
------------
At present there is not quota infrastructure in Magnum.

Adding Quota Management layer at the Orchestration layer, Heat, could be an
alternative. Doing so will give a finer view of resource consumption at the
IaaS layer which can be used while provisioning Magnum resources which
depend on the IaaS layer [1]_.

Data model impact
-----------------
New Quota and Quota usages table will be introduced to Magnum database to
store quota consumption for each resource in a project.

Quota Table :

+------------+--------------+------+-----+---------+----------------+
| Field      | Type         | Null | Key | Default | Extra          |
+------------+--------------+------+-----+---------+----------------+
| id         | int(11)      | NO   | PRI | NULL    | auto_increment |
| created_at | datetime     | YES  |     | NULL    |                |
| updated_at | datetime     | YES  |     | NULL    |                |
| project_id | varchar(255) | YES  | MUL | NULL    |                |
| resource   | varchar(255) | NO   |     | NULL    |                |
| hard_limit | int(11)      | YES  |     | NULL    |                |
+------------+--------------+------+-----+---------+----------------+

Quota usages table :

+---------------+--------------+------+-----+---------+----------------+
| Field         | Type         | Null | Key | Default | Extra          |
+---------------+--------------+------+-----+---------+----------------+
| created_at    | datetime     | YES  |     | NULL    |                |
| updated_at    | datetime     | YES  |     | NULL    |                |
| id            | int(11)      | NO   | PRI | NULL    | auto_increment |
| project_id    | varchar(255) | YES  | MUL | NULL    |                |
| resource      | varchar(255) | NO   |     | NULL    |                |
| in_progress   | int(11)      | NO   |     | NULL    |                |
| used          | int(11)      | NO   |     | NULL    |                |
+---------------+--------------+------+-----+---------+----------------+


REST API impact
---------------
REST API will be added for :

1. quota-defaults      List all default quotas for all tenants.
2. quota-show          List the currently set quota values for a tenant.
3. quota-update        Updates quotas for a tenant.
4. quota-usage         Lists quota usage for a tenant.
5. quota-list          List quota for all the tenants.

A user with "admin" role will be able to do all the above operations but a user
with "non-admin" role will be restricted to only get/list quota associated to
his/her tenant. User with "non-admin" role can be a Member of the tenant less
"admin" role.

REST API for resources which will have quota imposed will be enhanced :

1. Bay create
Will check if there is quota available for Bay creation, if so proceed
ahead with the request otherwise throw exception that not enough quota is
available.

Security impact
---------------
None

Notifications impact
--------------------
None

Other end user impact
---------------------
End user will have the option to look at the quota set on the resources, quota
usage by a particular project.

Performance Impact
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
vilobhmm

Other contributors:
None

Work Items
----------

1. Introduce Quota and Quota usages table in Magnum database.
2. Introduce API to set/update Quota for a resource, specifically
   bay, for Mitaka release.
3. Introduce API to create Quota entry, by default, for a resource.
4. Provide config options that will allow users/admins to set Quota.
5. Make sure that if the resource is deleted the used count from the
   quota_usages table will be decremented by the number of resources
   deleted. For example, if resource, bay, is deleted then the entries
   for it in the Quota usages table should be decremented by the
   number of Bays deleted.
6. Provide CLI options to view the quota details :
    a. magnum quota-show <project-id>
    b. magnum quota-update <project-id> <resource> <hard-limit>
    c. magnum quota-defaults <project-id>
    d. magnum quota-usage <project-id>
    e. magnum quota-list
7. Add conf setting for bays default quota since we will focus
   on Bays for Mitaka.

Dependencies
============
None

Testing
=======

1. Each commit will be accompanied with unit tests.
2. Gate functional tests will also be covered.

Documentation Impact
====================
None

References
==========

.. [1] http://lists.openstack.org/pipermail/openstack-dev/2015-December/082266.html
.. [2] https://github.com/openstack/nova/blob/master/nova/quota.py
.. [3] https://github.com/openstack/nova/blob/master/cinder/quota.py
