.. -*- rst -*-

================
 Manage Cluster
================

Lists, creates, shows details for, updates, and deletes Cluster.

Create new cluster
==================

.. rest_method:: POST /v1/clusters

Create new cluster based on cluster template.

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
  - cluster_template_id: clustertemplate_id
  - node_count: node_count
  - create_timeout: create_timeout
  - keypair: keypair_id
  - master_flavor_id: master_flavor_id
  - labels: labels
  - flavor_id: flavor_id
  - fixed_subnet: fixed_subnet
  - fixed_network: fixed_network
  - floating_ip_enabled: floating_ip_enabled_cluster
  - master_lb_enabled: master_lb_enabled_cluster

.. note::

   Request for creating cluster is asynchronous from Newton.

Request Example
----------------

.. literalinclude:: samples/cluster-create-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id
  - uuid: cluster_id

Response Example
----------------

.. literalinclude:: samples/cluster-create-resp.json
   :language: javascript

List all clusters
=================

.. rest_method:: GET /v1/clusters

List all clusters in Magnum.

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
  - clusters: cluster_list
  - status: status
  - uuid: cluster_id
  - links: links
  - stack_id: stack_id
  - keypair: keypair_id
  - master_count: master_count
  - cluster_template_id: clustertemplate_id
  - node_count: node_count
  - create_timeout: create_timeout
  - name: name

Response Example
----------------

.. literalinclude:: samples/cluster-get-all-resp.json
   :language: javascript

Show details of a cluster
=========================

.. rest_method:: GET /v1/clusters/{cluster_ident}

Get all information of a cluster in Magnum.

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

  - cluster_ident: cluster_ident

Response
--------

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id
  - status: status
  - uuid: cluster_id
  - links: links
  - stack_id: stack_id
  - created_at: created_at
  - api_address: api_address
  - discovery_url: discovery_url
  - updated_at: updated_at
  - master_count: master_count
  - coe_version: coe_version
  - keypair: keypair_id
  - cluster_template_id: clustertemplate_id
  - master_addresses: master_addresses
  - node_count: node_count
  - node_addresses: node_addresses
  - status_reason: status_reason
  - create_timeout: create_timeout
  - floating_ip_enabled: floating_ip_enabled_cluster
  - master_lb_enabled: master_lb_enabled_cluster
  - name: name

Response Example
----------------

.. literalinclude:: samples/cluster-get-one-resp.json
   :language: javascript

Delete a cluster
====================

.. rest_method:: DELETE /v1/clusters/{cluster_ident}

Delete a cluster.

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

  - cluster_ident: cluster_ident

Response
--------

This request does not return anything in the response body.

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id

Update information of cluster
=============================

.. rest_method:: PATCH /v1/clusters/{cluster_ident}

Update information of one cluster attributes using operations
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

  - cluster_ident: cluster_ident
  - path: path
  - value: value
  - op: op

.. note::

   Request for updating cluster is asynchronous from Newton.
   Currently only attribute ``node_count`` are supported for operation
   ``replace`` and ``remove``.

Request Example
----------------

.. literalinclude:: samples/cluster-update-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id
  - uuid: cluster_id

Response Example
----------------

.. literalinclude:: samples/cluster-create-resp.json
   :language: javascript


Resize a cluster
================

.. rest_method:: POST /v1/clusters/{cluster_ident}/actions/resize

Resize a cluster.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404
   - 409

Request
-------

.. rest_parameters:: parameters.yaml

  - cluster_ident: cluster_ident
  - node_count: node_count
  - nodes_to_remove: nodes_to_remove
  - nodegroup: nodegroup

.. note::

   The nodegroup is just a placeholder for future. It hasn't been supported
   in Magnum now.

Request Example
----------------

.. literalinclude:: samples/cluster-resize-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id
  - uuid: cluster_id

Response Example
----------------

.. literalinclude:: samples/cluster-resize-resp.json
   :language: javascript


Upgrade a cluster
=================

.. rest_method:: POST /v1/clusters/{cluster_ident}/actions/upgrade

Resize a cluster.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404
   - 409

Request
-------

.. rest_parameters:: parameters.yaml

  - cluster_ident: cluster_ident
  - cluster_template: clustertemplate_id
  - max_batch_size: max_batch_size
  - nodegroup: nodegroup

.. note::

   The nodegroup is just a placeholder for future. It hasn't been supported
   in Magnum now.

Request Example
----------------

.. literalinclude:: samples/cluster-upgrade-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id
  - uuid: cluster_id

Response Example
----------------

.. literalinclude:: samples/cluster-upgrade-resp.json
   :language: javascript
