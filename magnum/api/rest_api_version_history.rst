REST API Version History
========================

This documents the changes made to the REST API with every
microversion change. The description for each version should be a
verbose one which has enough information to be suitable for use in
user documentation.

1.1
---

  This is the initial version of the v1.1 API which supports
  microversions. The v1.1 API is from the REST API users's point of
  view exactly the same as v1.0 except with strong input validation.

  A user can specify a header in the API request::

    OpenStack-API-Version: <version>

  where ``<version>`` is any valid api version for this API.

  If no version is specified then the API will behave as if a version
  request of v1.1 was requested.

1.2
---

  Support for async cluster (previously known as bay) operations

  Before v1.2 all magnum bay operations were synchronous and as a result API
  requests were blocked until response from HEAT service is received.
  With this change cluster-create/bay-create, cluster-update/bay-update and
  cluster-delete/bay-delete calls will be asynchronous.


1.3
---

  Rollback cluster (previously known as bay) on update failure

  User can enable rollback on bay update failure by specifying microversion
  1.3 in header({'OpenStack-API-Version': 'container-infra 1.3'}) and passing
  'rollback=True' when issuing cluster/bay update request.
  For example:-
  - http://XXX/v1/clusters/XXX/?rollback=True or
  - http://XXX/v1/bays/XXX/?rollback=True


1.4
---

  Add stats API

  An admin user can get total number of clusters and nodes for a specified
  tenant or for all the tenants and also a non-admin user can get self stats.
  For example:-
  - http://XXX/v1/stats or
  - http://XXX/v1/stats?project_id=<project-id> or
  - http://XXX/v1/stats?project_id=<project-id>&type=<stats-type>


1.5
---

  Support for cluster CA certificate rotation

  This gives admins a way to revoke access to an existing cluster once
  a user has been granted access.


1.6
---

  Add quotas API

  An admin user can set/update/delete/list quotas for the given tenant.
  A non-admin user can get self quota information.


1.7
---

  Add resize API


1.8
---

  Add upgrade API


1.9
---

  Add nodegroup API

  Allow create/update/delete/list of default-worker and additional nodegroups.


1.10
---

  Allow nodegroups with 0 nodes

  Allow the cluster to be created with node_count = 0 as well as to update
  existing nodegroups to have 0 nodes.

1.11
---

  Drop bay and baymodels objects from magnum source code
