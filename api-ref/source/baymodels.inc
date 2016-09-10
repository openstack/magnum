.. -*- rst -*-

===================
 Manage Baymodels
===================

Lists, creates, shows details for, updates, and deletes baymodels.

Create new baymodel
====================

.. rest_method:: POST /v1/baymodels/

Create new baymodel.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404

Request
-------

.. rest_parameters:: parameters.yaml

  - labels: labels
  - fixed_subnet: fixed_subnet
  - master_flavor_id: master_flavor_id
  - no_proxy: no_proxy
  - https_proxy: https_proxy
  - http_proxy: http_proxy
  - tls_disabled: tls_disabled
  - keypair_id: keypair_id
  - public: public_type
  - docker_volume_size: docker_volume_size
  - server_type: server_type
  - external_network_id: external_network_id
  - image_id: image_id
  - volume_driver: volume_driver
  - registry_enabled: registry_enabled
  - docker_storage_driver: docker_storage_driver
  - name: name
  - network_driver: network_driver
  - fixed_network: fixed_network
  - coe: coe
  - flavor_id: flavor_id
  - master_lb_enabled: master_lb_enabled
  - dns_nameserver: dns_nameserver

Request Example
----------------

.. literalinclude:: samples/baymodel-create-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id
  - insecure_registry: insecure_registry
  - links: links
  - http_proxy: http_proxy
  - updated_at: updated_at
  - floating_ip_enabled: floating_ip_enabled
  - fixed_subnet: fixed_subnet
  - master_flavor_id: master_flavor_id
  - uuid: baymodel_id
  - no_proxy: no_proxy
  - https_proxy: https_proxy
  - tls_disabled: tls_disabled
  - keypair_id: keypair_id
  - public: public_type
  - labels: labels
  - docker_volume_size: docker_volume_size
  - server_type: server_type
  - external_network_id: external_network_id
  - cluster_distro: cluster_distro
  - image_id: image_id
  - volume_driver: volume_driver
  - registry_enabled: registry_enabled
  - docker_storage_driver: docker_storage_driver
  - apiserver_port: apiserver_port
  - name: name
  - created_at: created_at
  - network_driver: network_driver
  - fixed_network: fixed_network
  - coe: coe
  - flavor_id: flavor_id
  - master_lb_enabled: master_lb_enabled
  - dns_nameserver: dns_nameserver

Response Example
----------------

.. literalinclude:: samples/baymodel-create-resp.json
   :language: javascript

List all baymodels
==================

.. rest_method:: GET /v1/baymodels/

List all available baymodels in Magnum.

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
  - baymodels: baymodel_list
  - insecure_registry: insecure_registry
  - links: links
  - http_proxy: http_proxy
  - updated_at: updated_at
  - floating_ip_enabled: floating_ip_enabled
  - fixed_subnet: fixed_subnet
  - master_flavor_id: master_flavor_id
  - uuid: baymodel_id
  - no_proxy: no_proxy
  - https_proxy: https_proxy
  - tls_disabled: tls_disabled
  - keypair_id: keypair_id
  - public: public_type
  - labels: labels
  - docker_volume_size: docker_volume_size
  - server_type: server_type
  - external_network_id: external_network_id
  - cluster_distro: cluster_distro
  - image_id: image_id
  - volume_driver: volume_driver
  - registry_enabled: registry_enabled
  - docker_storage_driver: docker_storage_driver
  - apiserver_port: apiserver_port
  - name: name
  - created_at: created_at
  - network_driver: network_driver
  - fixed_network: fixed_network
  - coe: coe
  - flavor_id: flavor_id
  - master_lb_enabled: master_lb_enabled
  - dns_nameserver: dns_nameserver

Response Example
----------------

.. literalinclude:: samples/baymodel-get-all-resp.json
   :language: javascript

Show details of a baymodel
==========================

.. rest_method:: GET /v1/baymodels/{baymodel_ident}

Get all information of a baymodel in Magnum.

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

  - baymodel_ident: baymodel_ident

Response
--------

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id
  - baymodels: baymodel_list
  - insecure_registry: insecure_registry
  - links: links
  - http_proxy: http_proxy
  - updated_at: updated_at
  - floating_ip_enabled: floating_ip_enabled
  - fixed_subnet: fixed_subnet
  - master_flavor_id: master_flavor_id
  - uuid: baymodel_id
  - no_proxy: no_proxy
  - https_proxy: https_proxy
  - tls_disabled: tls_disabled
  - keypair_id: keypair_id
  - public: public_type
  - labels: labels
  - docker_volume_size: docker_volume_size
  - server_type: server_type
  - external_network_id: external_network_id
  - cluster_distro: cluster_distro
  - image_id: image_id
  - volume_driver: volume_driver
  - registry_enabled: registry_enabled
  - docker_storage_driver: docker_storage_driver
  - apiserver_port: apiserver_port
  - name: name
  - created_at: created_at
  - network_driver: network_driver
  - fixed_network: fixed_network
  - coe: coe
  - flavor_id: flavor_id
  - master_lb_enabled: master_lb_enabled
  - dns_nameserver: dns_nameserver

Response Example
----------------

.. literalinclude:: samples/baymodel-create-resp.json
   :language: javascript

Delete a baymodel
==================

.. rest_method:: DELETE /v1/baymodels/{baymodel_ident}

Delete a baymodel.

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

  - baymodel_ident: baymodel_ident

Response
--------

This request does not return anything in the response body.

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id

Update information of baymodel
===============================

.. rest_method:: PATCH /v1/baymodels/{baymodel_ident}

Update information of one baymodel attributes using operations including:
``add``, ``replace`` or ``remove``. The attributes to ``add`` and ``replace``
in the form of ``key=value`` while ``remove`` only needs the keys.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404

Request
-------

.. rest_parameters:: parameters.yaml

  - baymodel_ident: baymodel_ident
  - path: path
  - value: value
  - op: op

Request Example
----------------

.. literalinclude:: samples/baymodel-update-req.json
   :language: javascript

Response
--------

Return new baymodel with updated attributes.

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id
  - baymodels: baymodel_list
  - insecure_registry: insecure_registry
  - links: links
  - http_proxy: http_proxy
  - updated_at: updated_at
  - floating_ip_enabled: floating_ip_enabled
  - fixed_subnet: fixed_subnet
  - master_flavor_id: master_flavor_id
  - uuid: baymodel_id
  - no_proxy: no_proxy
  - https_proxy: https_proxy
  - tls_disabled: tls_disabled
  - keypair_id: keypair_id
  - public: public_type
  - labels: labels
  - docker_volume_size: docker_volume_size
  - server_type: server_type
  - external_network_id: external_network_id
  - cluster_distro: cluster_distro
  - image_id: image_id
  - volume_driver: volume_driver
  - registry_enabled: registry_enabled
  - docker_storage_driver: docker_storage_driver
  - apiserver_port: apiserver_port
  - name: name
  - created_at: created_at
  - network_driver: network_driver
  - fixed_network: fixed_network
  - coe: coe
  - flavor_id: flavor_id
  - master_lb_enabled: master_lb_enabled
  - dns_nameserver: dns_nameserver

Response Example
----------------

.. literalinclude:: samples/baymodel-create-resp.json
   :language: javascript