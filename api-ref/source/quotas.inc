.. -*- rst -*-

=================
 Magnum Quota API
=================

Lists, creates, shows details, and updates Quotas.

Set new quota
==================

.. rest_method:: POST /v1/quotas

Create new quota for a project.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404

Request Example
----------------

.. literalinclude:: samples/quota-create-req.json
   :language: javascript

Response Example
----------------

.. literalinclude:: samples/quota-create-resp.json
   :language: javascript

List all quotas
================

.. rest_method:: GET /v1/quotas

List all quotas in Magnum.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403

Response Example
----------------

.. literalinclude:: samples/quota-get-all-resp.json
   :language: javascript

Show details of a quota
=========================

.. rest_method:: GET /v1/quotas/{project_id}/{resource}

Get quota information for the given project_id and resource.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404

Response Example
----------------

.. literalinclude:: samples/quota-get-one-resp.json
   :language: javascript

Update a resource quota
=============================

.. rest_method:: PATCH /v1/quotas/{project_id}/{resource}

Update resource quota for the given project id.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404

Request Example
----------------

.. literalinclude:: samples/quota-update-req.json
   :language: javascript

Response Example
----------------

.. literalinclude:: samples/quota-update-resp.json
   :language: javascript

Delete a resource quota
============================

.. rest_method:: DELETE /v1/quotas/{project_id}/{resource}

Delete a resource quota for the given project id.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 204

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404

Request Example
----------------

.. literalinclude:: samples/quota-delete-req.json
   :language: javascript