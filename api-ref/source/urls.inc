.. -*- rst -*-

=================
 Magnum Base URLs
=================

All API calls through the rest of this document require authentication
with the OpenStack Identity service. The Identity service includes a so-called
Service Catalog in responses to valid requests for a new token. This service
catalog defines a list of services, identified by both a name and a service
type, along with a list of endpoints. In deployments where Magnum is installed,
Magnum should appear in this list using the service type,
``container-infrastructure-management``, or one of the aliases,
``container-infrastructure`` or ``container-infra``. The endpoint URL provided
will form the root url that every call below will be added to build a full
path.

.. note::

    If using OpenStack Identity service API v2, ``url`` can be represented via
    ``adminURL``, ``internalURL`` or ``publicURL`` in endpoint catalog. In
    Identity service API v3, ``url`` is represented with field ``interface``
    including ``admin``, ``internal`` and ``public``.

For instance, if the ``url`` is
``http://my-container-infra.org/magnum/v1`` then the full API call for
``/clusters`` is ``http://my-container-infra.org/magnum/v1/clusters``.

Depending on the deployment the container infrastructure management service
url might be http or https, a custom port, a custom path, and include your
project id. The only way to know the urls for your deployment is by using the
service catalog. The container infrastructure management URL should never be
hard coded in applications, even if they are only expected to work at a
single site. It should always be discovered from the Identity token.

As such, for the rest of this document we will be using short hand
where ``GET /clusters`` really means
``GET {your_container_infra_url}/clusters``.
