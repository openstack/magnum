.. -*- rst -*-

=====================================
 Manage certificates for bay/cluster
=====================================

Generates and show CA certificates for bay/cluster.

Show details about the CA certificate for a bay/cluster
=======================================================

.. rest_method:: GET /v1/certificates/{cluster_ident}?ca_cert_type={ca_cert_type}

Show CA certificate details that are associated with the created bay/cluster based on the
given CA certificate type.

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

  - cluster_ident: cluster_ident
  - ca_cert_type: ca_cert_type

.. note::

   After Newton, all terms related bay/baymodel will be renamed to cluster
   and cluster template.

Response
--------

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id
  - cluster_uuid: cluster_id
  - pem: pem
  - bay_uuid: bay_id
  - links: links

.. note::

   After Newton, all terms related bay/baymodel will be renamed to cluster
   and cluster template.

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

  - bay_uuid: bay_id
  - csr: csr

.. note::

   After Newton, all terms related bay/baymodel will be renamed to cluster
   and cluster template.

Request Example
----------------

.. literalinclude:: samples/certificates-ca-sign-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id
  - pem: pem
  - bay_uuid: bay_id
  - links: links
  - csr: csr

.. note::

   After Newton, all terms related bay/baymodel will be renamed to cluster
   and cluster template.

Response Example
----------------

.. literalinclude:: samples/certificates-ca-sign-resp.json
   :language: javascript

Rotate the CA certificate for a bay/cluster
===========================================

.. rest_method:: PATCH /v1/certificates/{bay_uuid/cluster_uuid}

Rotate the CA certificate for a bay/cluster and invalidate all user
certificates.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 400

Request
-------

.. rest_parameters:: parameters.yaml

   - cluster: cluster_id
