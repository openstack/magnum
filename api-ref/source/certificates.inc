.. -*- rst -*-

=====================================
 Manage certificates for bay/cluster
=====================================

Generates and show CA certificates for bay/cluster.

Show details about the CA certificate for a bay/cluster
=======================================================

.. rest_method:: GET /v1/certificates/{bay_uuid/cluster_uuid}

Show CA certificate details that are associated with the created bay/cluster.

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

  - bay_uuid: bay_cluster_id

Response
--------

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id
  - pem: pem
  - bay_uuid: bay_cluster_id
  - links: links

Response Example
----------------

.. literalinclude:: samples/certificates-ca-show-resp.json
   :language: javascript

Generate the CA certificate for a bay/cluster
=============================================

.. rest_method:: POST /v1/certificates/

Sign client key and generate the CA certificate for a bay/cluster

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403

Request
-------

.. rest_parameters:: parameters.yaml

  - bay_uuid: bay_cluster_id
  - csr: csr

Request Example
----------------

.. literalinclude:: samples/certificates-ca-sign-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id
  - pem: pem
  - bay_uuid: bay_cluster_id
  - links: links
  - csr: csr

Response Example
----------------

.. literalinclude:: samples/certificates-ca-sign-resp.json
   :language: javascript
