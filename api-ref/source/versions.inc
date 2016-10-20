.. -*- rst -*-

==============
 API Versions
==============

In order to bring new features to users over time, the Magnum API
supports versioning. There are two kinds of versions in Magnum.

- ''major versions'', which have dedicated urls
- ''microversions'', which can be requested through the use of the
  ``OpenStack-API-Version``.

Beginning with the Newton release, all API requests support the
``OpenStack-API-Version`` header. This header SHOULD be supplied
with every request; in the absence of this header, each request is treated
as though coming from an older pre-Newton client. This was done to preserve
backwards compatibility as we introduced new features.

The Version APIs work differently from other APIs as they *do not*
require authentication.

List API Versions
=======================

.. rest_method:: GET /

This fetches all the information about all known major API versions in
the deployment. Links to more specific information will be provided
for each API version, as well as information about supported min and
max microversions.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 503

Response
--------

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id
  - versions: version
  - status: version_status
  - min_version: version_min
  - max_version: version_max
  - id: version_id
  - links: links
  - name: name
  - description: description

Response Example
----------------

.. literalinclude:: samples/versions-get-resp.json
   :language: javascript


Show v1 API Version
====================================

.. rest_method:: GET /v1/

Show all the resources within the Magnum v1 API.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 503

Response
--------

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id
  - id: version_id
  - links: links

.. note::

   The ``media-types`` parameters in the response are
   vestigial and provide no useful information. They will probably be
   deprecated and removed in the future.


Response Example
----------------

.. literalinclude:: samples/versions-01-get-resp.json
   :language: javascript
