API Microversions
=================

Background
----------

Magnum uses a framework we call 'API Microversions' for allowing changes
to the API while preserving backward compatibility. The basic idea is
that a user has to explicitly ask for their request to be treated with
a particular version of the API. So breaking changes can be added to
the API without breaking users who don't specifically ask for it. This
is done with an HTTP header ``OpenStack-API-Version`` which has as its
value a string containing the name of the service, ``container-infra``,
and a monotonically increasing semantic version number starting
from ``1.1``.
The full form of the header takes the form::

    OpenStack-API-Version: container-infra 1.1

If a user makes a request without specifying a version, they will get
the ``BASE_VER`` as defined in
``magnum/api/controllers/versions.py``.  This value is currently ``1.1`` and
is expected to remain so for quite a long time.


When do I need a new Microversion?
----------------------------------

A microversion is needed when the contract to the user is
changed. The user contract covers many kinds of information such as:

- the Request

  - the list of resource urls which exist on the server

    Example: adding a new clusters/{ID}/foo which didn't exist in a
    previous version of the code

  - the list of query parameters that are valid on urls

    Example: adding a new parameter ``is_yellow`` clusters/{ID}?is_yellow=True

  - the list of query parameter values for non free form fields

    Example: parameter filter_by takes a small set of constants/enums "A",
    "B", "C". Adding support for new enum "D".

  - new headers accepted on a request

  - the list of attributes and data structures accepted.

    Example: adding a new attribute 'locked': True/False to the request body


- the Response

  - the list of attributes and data structures returned

    Example: adding a new attribute 'locked': True/False to the output
    of clusters/{ID}

  - the allowed values of non free form fields

    Example: adding a new allowed ``status`` to clusters/{ID}

  - the list of status codes allowed for a particular request

    Example: an API previously could return 200, 400, 403, 404 and the
    change would make the API now also be allowed to return 409.

    See [#f2]_ for the 400, 403, 404 and 415 cases.

  - changing a status code on a particular response

    Example: changing the return code of an API from 501 to 400.

    .. note:: Fixing a bug so that a 400+ code is returned rather than a 500 or
      503 does not require a microversion change. It's assumed that clients are
      not expected to handle a 500 or 503 response and therefore should not
      need to opt-in to microversion changes that fixes a 500 or 503 response
      from happening.
      According to the OpenStack API Working Group, a
      **500 Internal Server Error** should **not** be returned to the user for
      failures due to user error that can be fixed by changing the request on
      the client side. See [#f1]_.

  - new headers returned on a response

The following flow chart attempts to walk through the process of "do
we need a microversion".


.. graphviz::

   digraph states {

    label="Do I need a microversion?"

    silent_fail[shape="diamond", style="", group=g1, label="Did we silently
   fail to do what is asked?"];
    ret_500[shape="diamond", style="", group=g1, label="Did we return a 500
   before?"];
    new_error[shape="diamond", style="", group=g1, label="Are we changing what
    status code is returned?"];
    new_attr[shape="diamond", style="", group=g1, label="Did we add or remove an
    attribute to a payload?"];
    new_param[shape="diamond", style="", group=g1, label="Did we add or remove
    an accepted query string parameter or value?"];
    new_resource[shape="diamond", style="", group=g1, label="Did we add or remove a
   resource url?"];


   no[shape="box", style=rounded, label="No microversion needed"];
   yes[shape="box", style=rounded, label="Yes, you need a microversion"];
   no2[shape="box", style=rounded, label="No microversion needed, it's
   a bug"];

   silent_fail -> ret_500[label=" no"];
   silent_fail -> no2[label="yes"];

    ret_500 -> no2[label="yes [1]"];
    ret_500 -> new_error[label=" no"];

    new_error -> new_attr[label=" no"];
    new_error -> yes[label="yes"];

    new_attr -> new_param[label=" no"];
    new_attr -> yes[label="yes"];

    new_param -> new_resource[label=" no"];
    new_param -> yes[label="yes"];

    new_resource -> no[label=" no"];
    new_resource -> yes[label="yes"];

   {rank=same; yes new_attr}
   {rank=same; no2 ret_500}
   {rank=min; silent_fail}
   }


**Footnotes**

.. [#f1] When fixing 500 errors that previously caused stack traces, try
  to map the new error into the existing set of errors that API call
  could previously return (400 if nothing else is appropriate). Changing
  the set of allowed status codes from a request is changing the
  contract, and should be part of a microversion (except in [#f2]_).

  The reason why we are so strict on contract is that we'd like
  application writers to be able to know, for sure, what the contract is
  at every microversion in Magnum. If they do not, they will need to write
  conditional code in their application to handle ambiguities.

  When in doubt, consider application authors. If it would work with no
  client side changes on both Magnum versions, you probably don't need a
  microversion. If, on the other hand, there is any ambiguity, a
  microversion is probably needed.

.. [#f2] The exception to not needing a microversion when returning a
  previously unspecified error code is the 400, 403, 404 and 415 cases. This is
  considered OK to return even if previously unspecified in the code since
  it's implied given keystone authentication can fail with a 403 and API
  validation can fail with a 400 for invalid JSON request body. Request to
  url/resource that does not exist always fails with 404. Invalid content types
  are handled before API methods are called which results in a 415.

  .. note:: When in doubt about whether or not a microversion is required
      for changing an error response code, consult the `Containers Team`_.

.. _Containers Team: https://wiki.openstack.org/wiki/Meetings/Containers


When a microversion is not needed
---------------------------------

A microversion is not needed in the following situation:

- the response

  - Changing the error message without changing the response code
    does not require a new microversion.

  - Removing an inapplicable HTTP header, for example, suppose the Retry-After
    HTTP header is being returned with a 4xx code. This header should only be
    returned with a 503 or 3xx response, so it may be removed without bumping
    the microversion.

In Code
-------

In ``magnum/api/controllers/base.py`` we define an ``@api_version`` decorator
which is intended to be used on top-level Controller methods. It is
not appropriate for lower-level methods. Some examples:

Adding a new API method
~~~~~~~~~~~~~~~~~~~~~~~

In the controller class::

    @base.Controller.api_version("1.2")
    def my_api_method(self, req, id):
        ....

This method would only be available if the caller had specified an
``OpenStack-API-Version`` of >= ``1.2``. If they had specified a
lower version (or not specified it and received the default of ``1.1``)
the server would respond with ``HTTP/406``.

Removing an API method
~~~~~~~~~~~~~~~~~~~~~~

In the controller class::

    @base.Controller.api_version("1.2", "1.3")
    def my_api_method(self, req, id):
        ....

This method would only be available if the caller had specified an
``OpenStack-API-Version`` of >= ``1.2`` and
``OpenStack-API-Version`` of <= ``1.3``. If ``1.4`` or later
is specified the server will respond with ``HTTP/406``.

Changing a method's behavior
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the controller class::

    @base.Controller.api_version("1.2", "1.3")
    def my_api_method(self, req, id):
        .... method_1 ...

    @base.Controller.api_version("1.4") #noqa
    def my_api_method(self, req, id):
        .... method_2 ...

If a caller specified ``1.2``, ``1.3`` (or received the default
of ``1.1``) they would see the result from ``method_1``,
and for ``1.4`` or later they would see the result from ``method_2``.

It is vital that the two methods have the same name, so the second of
them will need ``# noqa`` to avoid failing flake8's ``F811`` rule. The
two methods may be different in any kind of semantics (schema
validation, return values, response codes, etc)

When not using decorators
~~~~~~~~~~~~~~~~~~~~~~~~~

When you don't want to use the ``@api_version`` decorator on a method
or you want to change behavior within a method (say it leads to
simpler or simply a lot less code) you can directly test for the
requested version with a method as long as you have access to the api
request object (commonly accessed with ``pecan.request``). Every API
method has an versions object attached to the request object and that
can be used to modify behavior based on its value::

    def index(self):
        <common code>

        req_version = pecan.request.headers.get(Version.string)
        req1_min = versions.Version("1.1")
        req1_max = versions.Version("1.5")
        req2_min = versions.Version("1.6")
        req2_max = versions.Version("1.10")

        if req_version.matches(req1_min, req1_max):
            ....stuff....
        elif req_version.matches(req2min, req2_max):
            ....other stuff....
        elif req_version > versions.Version("1.10"):
            ....more stuff.....

        <common code>

The first argument to the matches method is the minimum acceptable version
and the second is maximum acceptable version. If the specified minimum
version and maximum version are null then ``ValueError`` is returned.

Other necessary changes
-----------------------

If you are adding a patch which adds a new microversion, it is
necessary to add changes to other places which describe your change:

* Update ``REST_API_VERSION_HISTORY`` in
  ``magnum/api/controllers/versions.py``

* Update ``CURRENT_MAX_VER`` in
  ``magnum/api/controllers/versions.py``

* Add a verbose description to
  ``magnum/api/rest_api_version_history.rst``.  There should
  be enough information that it could be used by the docs team for
  release notes.

* Update the expected versions in affected tests, for example in
  ``magnum/tests/unit/api/controllers/test_base.py``.

* Make a new commit to python-magnumclient and update corresponding
  files to enable the newly added microversion API.

* If the microversion changes the response schema, a new schema and test for
  the microversion must be added to Tempest.

Allocating a microversion
-------------------------

If you are adding a patch which adds a new microversion, it is
necessary to allocate the next microversion number. Except under
extremely unusual circumstances and this would have been mentioned in
the magnum spec for the change, the minor number of ``CURRENT_MAX_VER``
will be incremented. This will also be the new microversion number for
the API change.

It is possible that multiple microversion patches would be proposed in
parallel and the microversions would conflict between patches.  This
will cause a merge conflict. We don't reserve a microversion for each
patch in advance as we don't know the final merge order. Developers
may need over time to rebase their patch calculating a new version
number as above based on the updated value of ``CURRENT_MAX_VER``.
