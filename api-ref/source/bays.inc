.. -*- rst -*-

============
 Manage Bay
============

Lists, creates, shows details for, updates, and deletes Bay.

Create new bay
==============

.. rest_method:: POST /v1/bays

Create new bay based on bay model.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404

Request
-------

.. rest_parameters:: parameters.yaml

  - name: name
  - discovery_url: discovery_url
  - master_count: master_count
  - baymodel_id: baymodel_id
  - node_count: node_count
  - bay_create_timeout: bay_create_timeout

.. note::

   Request for creating bay is asynchronous from Newton.

Request Example
----------------

.. literalinclude:: samples/bay-create-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id
  - uuid: bay_id

Response Example
----------------

.. literalinclude:: samples/bay-create-resp.json
   :language: javascript

List all bays
====================

.. rest_method:: GET /v1/bays/

List all bays in Magnum.

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

  - X-Openstack-Request-Id: request_id
  - bays: bay_list
  - status: status
  - uuid: bay_id
  - links: links
  - stack_id: stack_id
  - master_count: master_count
  - baymodel_id: baymodel_id
  - node_count: node_count
  - bay_create_timeout: bay_create_timeout
  - name: name

Response Example
----------------

.. literalinclude:: samples/bay-get-all-resp.json
   :language: javascript

Show details of a bay
=============================

.. rest_method:: GET /v1/bays/{bay_ident}

Get all information of a bay in Magnum.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404

Request
-------

.. rest_parameters:: parameters.yaml

  - bay_ident: bay_ident

Response
--------

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id
  - status: status
  - uuid: bay_id
  - links: links
  - stack_id: stack_id
  - created_at: created_at
  - api_address: api_address
  - discovery_url: discovery_url
  - updated_at: updated_at
  - master_count: master_count
  - coe_version: coe_version
  - baymodel_id: baymodel_id
  - master_addresses: master_addresses
  - node_count: node_count
  - node_addresses: node_addresses
  - status_reason: status_reason
  - bay_create_timeout: bay_create_timeout
  - name: name

Response Example
----------------

.. literalinclude:: samples/bay-get-one-resp.json
   :language: javascript

Delete a bay
====================

.. rest_method:: DELETE /v1/bays/{bay_ident}

Delete a bay.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 204

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404
   - 409

Request
-------

.. rest_parameters:: parameters.yaml

  - bay_ident: bay_ident

Response
--------

This request does not return anything in the response body.

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id

Update information of bay
=================================

.. rest_method:: PATCH /v1/bays/{bay_ident}

Update information of one bay  attributes using operations
including: ``add``, ``replace`` or ``remove``. The attributes to ``add`` and
``replace`` in the form of ``key=value`` while ``remove`` only needs the keys.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404

Request
-------

.. rest_parameters:: parameters.yaml

  - bay_ident: bay_ident
  - path: path
  - value: value
  - op: op

.. note::

   Request for updating bay is asynchronous from Newton.
   Currently only attribute ``node_count`` are supported for operation
   ``replace`` and ``remove``.

Request Example
----------------

.. literalinclude:: samples/bay-update-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id
  - uuid: bay_id

Response Example
----------------

.. literalinclude:: samples/bay-create-resp.json
   :language: javascript
