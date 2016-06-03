# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Version 1 of the Magnum API

NOTE: IN PROGRESS AND NOT FULLY IMPLEMENTED.
"""

from oslo_log import log as logging
import pecan
from pecan import rest
from webob import exc
from wsme import types as wtypes

from magnum.api.controllers import base as controllers_base
from magnum.api.controllers import link
from magnum.api.controllers.v1 import bay
from magnum.api.controllers.v1 import baymodel
from magnum.api.controllers.v1 import certificate
from magnum.api.controllers.v1 import magnum_services
from magnum.api import expose
from magnum.i18n import _


LOG = logging.getLogger(__name__)

BASE_VERSION = 1

# NOTE(yuntong): v1.0 is reserved to indicate Kilo's API, but is not presently
#             supported by the API service. All changes between Kilo and the
#             point where we added microversioning are considered backwards-
#             compatible, but are not specifically discoverable at this time.
#
#             The v1.1 version indicates this "initial" version as being
#             different from Kilo (v1.0), and includes the following changes:
#

# v1.1: API at the point in time when microversioning support was added
MIN_VER_STR = 'magnum 1.1'

# v1.1: Add API changelog here
MAX_VER_STR = 'magnum 1.1'


MIN_VER = controllers_base.Version(
    {controllers_base.Version.string: MIN_VER_STR},
    MIN_VER_STR, MAX_VER_STR)
MAX_VER = controllers_base.Version(
    {controllers_base.Version.string: MAX_VER_STR},
    MIN_VER_STR, MAX_VER_STR)


class MediaType(controllers_base.APIBase):
    """A media type representation."""

    base = wtypes.text
    type = wtypes.text

    def __init__(self, base, type):
        self.base = base
        self.type = type


class V1(controllers_base.APIBase):
    """The representation of the version 1 of the API."""

    id = wtypes.text
    """The ID of the version, also acts as the release number"""

    media_types = [MediaType]
    """An array of supcontainersed media types for this version"""

    links = [link.Link]
    """Links that point to a specific URL for this version and documentation"""

    baymodels = [link.Link]
    """Links to the baymodels resource"""

    bays = [link.Link]
    """Links to the bays resource"""

    certificates = [link.Link]
    """Links to the certificates resource"""

    mservices = [link.Link]
    """Links to the magnum-services resource"""

    @staticmethod
    def convert():
        v1 = V1()
        v1.id = "v1"
        v1.links = [link.Link.make_link('self', pecan.request.host_url,
                                        'v1', '', bookmark=True),
                    link.Link.make_link('describedby',
                                        'http://docs.openstack.org',
                                        'developer/magnum/dev',
                                        'api-spec-v1.html',
                                        bookmark=True, type='text/html')]
        v1.media_types = [MediaType('application/json',
                          'application/vnd.openstack.magnum.v1+json')]
        v1.baymodels = [link.Link.make_link('self', pecan.request.host_url,
                                            'baymodels', ''),
                        link.Link.make_link('bookmark',
                                            pecan.request.host_url,
                                            'baymodels', '',
                                            bookmark=True)]
        v1.bays = [link.Link.make_link('self', pecan.request.host_url,
                                       'bays', ''),
                   link.Link.make_link('bookmark',
                                       pecan.request.host_url,
                                       'bays', '',
                                       bookmark=True)]
        v1.certificates = [link.Link.make_link('self', pecan.request.host_url,
                                               'certificates', ''),
                           link.Link.make_link('bookmark',
                                               pecan.request.host_url,
                                               'certificates', '',
                                               bookmark=True)]
        v1.mservices = [link.Link.make_link('self', pecan.request.host_url,
                                            'mservices', ''),
                        link.Link.make_link('bookmark',
                                            pecan.request.host_url,
                                            'mservices', '',
                                            bookmark=True)]
        return v1


class Controller(rest.RestController):
    """Version 1 API controller root."""

    bays = bay.BaysController()
    baymodels = baymodel.BayModelsController()
    certificates = certificate.CertificateController()
    mservices = magnum_services.MagnumServiceController()

    @expose.expose(V1)
    def get(self):
        # NOTE: The reason why convert() it's being called for every
        #       request is because we need to get the host url from
        #       the request object to make the links.
        return V1.convert()

    def _check_version(self, version, headers=None):
        if headers is None:
            headers = {}
        # ensure that major version in the URL matches the header
        if version.major != BASE_VERSION:
            raise exc.HTTPNotAcceptable(_(
                "Mutually exclusive versions requested. Version %(ver)s "
                "requested but not supported by this service."
                "The supported version range is: "
                "[%(min)s, %(max)s].") % {'ver': version,
                                          'min': MIN_VER_STR,
                                          'max': MAX_VER_STR},
                headers=headers)
        # ensure the minor version is within the supported range
        if version < MIN_VER or version > MAX_VER:
            raise exc.HTTPNotAcceptable(_(
                "Version %(ver)s was requested but the minor version is not "
                "supported by this service. The supported version range is: "
                "[%(min)s, %(max)s].") % {'ver': version, 'min': MIN_VER_STR,
                                          'max': MAX_VER_STR}, headers=headers)

    @pecan.expose()
    def _route(self, args):
        version = controllers_base.Version(
            pecan.request.headers, MIN_VER_STR, MAX_VER_STR)

        # Always set the min and max headers
        pecan.response.headers[
            controllers_base.Version.min_string] = MIN_VER_STR
        pecan.response.headers[
            controllers_base.Version.max_string] = MAX_VER_STR

        # assert that requested version is supported
        self._check_version(version, pecan.response.headers)
        pecan.response.headers[controllers_base.Version.string] = str(version)
        pecan.request.version = version
        if pecan.request.body:
            msg = ("Processing request: url: %(url)s, %(method)s, "
                   "body: %(body)s" %
                   {'url': pecan.request.url,
                    'method': pecan.request.method,
                    'body': pecan.request.body})
            LOG.debug(msg)

        return super(Controller, self)._route(args)

__all__ = (Controller)
