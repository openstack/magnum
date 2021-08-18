..
      Copyright 2016 Hewlett Packard Enterprise Development Company LP
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

Configuration
=============

Magnum has a number of configuration options which will be detailed here.

Magnum Config
-------------

The magnum configuration file is called ``magnum.conf``.

Magnum Pipeline
---------------

The pipeline details are contained in ``api-paste.ini``.

Healthcheck Middleware
~~~~~~~~~~~~~~~~~~~~~~

This piece of middleware creates an endpoint that allows a load balancer
to probe if the API endpoint should be available at the node or not.

The healthcheck middleware should be deployed as a paste application
application. Which is located in your ``api-paste.ini`` under a section called
``[app:healthcheck]``. It should look like this::

    [app:healthcheck]
    paste.app_factory = oslo_middleware:Healthcheck.app_factory
    backends = disable_by_file
    disable_by_file_path = /etc/magnum/healthcheck_disable

The main pipeline using this application should look something like this also
defined in the ``api-paste.ini``::

    [composite:main]
    paste.composite_factory = magnum.api:root_app_factory
    /: api
    /healthcheck: healthcheck

If you wish to disable a middleware without taking it out of the
pipeline, you can create a file under the file path defined by
``disable_by_file_path`` ie. ``/etc/magnum/healthcheck_disable``.

For more information see
`oslo.middleware <https://docs.openstack.org/oslo.middleware/latest/reference/api.html#oslo_middleware.Healthcheck>`_.
