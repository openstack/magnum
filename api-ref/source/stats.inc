.. -*- rst -*-

=================
 Magnum Stats API
=================

An admin user can get stats for the given tenant and also overall system stats.
A non-admin user can get self stats.

Show stats for a tenant
=======================

.. rest_method:: GET /v1/stats?project_id=<project_id>

Get stats based on project id.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403

Request
-------

.. rest_parameters:: parameters.yaml

  - project_id: project_id

Response
--------

.. rest_parameters:: parameters.yaml

  - clusters: clusters
  - nodes: nodes

Response Example
----------------

.. literalinclude:: samples/stats-get-resp.json
   :language: javascript

Show overall stats
==================

.. rest_method:: GET /v1/stats

Show overall Magnum system stats.
If the requester is non-admin user show self stats.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403

Response
--------

.. rest_parameters:: parameters.yaml

  - clusters: clusters
  - nodes: nodes

Response Example
----------------

.. literalinclude:: samples/stats-get-resp.json
   :language: javascript
