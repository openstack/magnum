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
from wsme import types as wtypes

from magnum.api.controllers import base as controllers_base
from magnum.api.controllers import link
from magnum.api.controllers.v1 import bay
from magnum.api.controllers.v1 import baymodel
from magnum.api.controllers.v1 import certificate
from magnum.api.controllers.v1 import cluster
from magnum.api.controllers.v1 import cluster_template
from magnum.api.controllers.v1 import federation
from magnum.api.controllers.v1 import magnum_services
from magnum.api.controllers.v1 import quota
from magnum.api.controllers.v1 import stats
from magnum.api.controllers import versions as ver
from magnum.api import expose
from magnum.api import http_error
from magnum.i18n import _


LOG = logging.getLogger(__name__)

BASE_VERSION = 1

MIN_VER_STR = '%s %s' % (ver.Version.service_string, ver.BASE_VER)

MAX_VER_STR = '%s %s' % (ver.Version.service_string, ver.CURRENT_MAX_VER)

MIN_VER = ver.Version({ver.Version.string: MIN_VER_STR},
                      MIN_VER_STR, MAX_VER_STR)
MAX_VER = ver.Version({ver.Version.string: MAX_VER_STR},
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

    clustertemplates = [link.Link]
    """Links to the clustertemplates resource"""

    clusters = [link.Link]
    """Links to the clusters resource"""

    quotas = [link.Link]
    """Links to the quotas resource"""

    certificates = [link.Link]
    """Links to the certificates resource"""

    mservices = [link.Link]
    """Links to the magnum-services resource"""

    stats = [link.Link]
    """Links to the stats resource"""

    # Links to the federations resources
    federations = [link.Link]

    nodegroups = [link.Link]
    """Links to the nodegroups resource"""

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
        v1.clustertemplates = [link.Link.make_link('self',
                                                   pecan.request.host_url,
                                                   'clustertemplates', ''),
                               link.Link.make_link('bookmark',
                                                   pecan.request.host_url,
                                                   'clustertemplates', '',
                                                   bookmark=True)]
        v1.clusters = [link.Link.make_link('self', pecan.request.host_url,
                                           'clusters', ''),
                       link.Link.make_link('bookmark',
                                           pecan.request.host_url,
                                           'clusters', '',
                                           bookmark=True)]
        v1.quotas = [link.Link.make_link('self', pecan.request.host_url,
                                         'quotas', ''),
                     link.Link.make_link('bookmark',
                                         pecan.request.host_url,
                                         'quotas', '',
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
        v1.stats = [link.Link.make_link('self', pecan.request.host_url,
                                        'stats', ''),
                    link.Link.make_link('bookmark',
                                        pecan.request.host_url,
                                        'stats', '',
                                        bookmark=True)]
        v1.federations = [link.Link.make_link('self', pecan.request.host_url,
                                              'federations', ''),
                          link.Link.make_link('bookmark',
                                              pecan.request.host_url,
                                              'federations', '',
                                              bookmark=True)]
        v1.nodegroups = [link.Link.make_link('self', pecan.request.host_url,
                                             'clusters/{cluster_id}',
                                             'nodegroups'),
                         link.Link.make_link('bookmark',
                                             pecan.request.host_url,
                                             'clusters/{cluster_id}',
                                             'nodegroups',
                                             bookmark=True)]

        return v1


class Controller(controllers_base.Controller):
    """Version 1 API controller root."""

    bays = bay.BaysController()
    baymodels = baymodel.BayModelsController()
    clusters = cluster.ClustersController()
    clustertemplates = cluster_template.ClusterTemplatesController()
    quotas = quota.QuotaController()
    certificates = certificate.CertificateController()
    mservices = magnum_services.MagnumServiceController()
    stats = stats.StatsController()
    federations = federation.FederationsController()

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
            raise http_error.HTTPNotAcceptableAPIVersion(_(
                "Mutually exclusive versions requested. Version %(ver)s "
                "requested but not supported by this service."
                "The supported version range is: "
                "[%(min)s, %(max)s].") % {'ver': version,
                                          'min': MIN_VER_STR,
                                          'max': MAX_VER_STR},
                headers=headers,
                max_version=str(MAX_VER),
                min_version=str(MIN_VER))
        # ensure the minor version is within the supported range
        if version < MIN_VER or version > MAX_VER:
            raise http_error.HTTPNotAcceptableAPIVersion(_(
                "Version %(ver)s was requested but the minor version is not "
                "supported by this service. The supported version range is: "
                "[%(min)s, %(max)s].") % {'ver': version, 'min': MIN_VER_STR,
                                          'max': MAX_VER_STR},
                headers=headers,
                max_version=str(MAX_VER),
                min_version=str(MIN_VER))

    @pecan.expose()
    def _route(self, args):
        version = ver.Version(
            pecan.request.headers, MIN_VER_STR, MAX_VER_STR)

        # Always set the basic version headers
        pecan.response.headers[ver.Version.min_string] = MIN_VER_STR
        pecan.response.headers[ver.Version.max_string] = MAX_VER_STR
        pecan.response.headers[ver.Version.string] = " ".join(
            [ver.Version.service_string, str(version)])
        pecan.response.headers["vary"] = ver.Version.string

        # assert that requested version is supported
        self._check_version(version, pecan.response.headers)
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
