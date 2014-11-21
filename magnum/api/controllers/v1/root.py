# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import pecan
import wsmeext.pecan as wsme_pecan


from magnum.api.controllers import common_types
from magnum.api.controllers.v1 import bay
from magnum.api.controllers.v1 import container
from magnum.api.controllers.v1.datamodel import types as api_types
from magnum.api.controllers.v1 import pod
from magnum.api.controllers.v1 import service
from magnum.common import exception
from magnum import version


class Platform(api_types.Base):
    bays_uri = common_types.Uri
    "URI to Bays"

    pods_uri = common_types.Uri
    "URI to Pods"

    services_uri = common_types.Uri
    "URI to Services"

    containers_uri = common_types.Uri
    "URI to Services"

    @classmethod
    def sample(cls):
        return cls(uri='http://example.com/v1',
                   name='magnum',
                   type='platform',
                   description='magnum native implementation',
                   bays_uri='http://example.com:9511/v1/bays',
                   pods_uri='http://example.com:9511/v1/pods',
                   services_uri='http://example.com:9511/v1/services',
                   containers_uri='http://example.com:9511/v1/containers')


class Controller(object):
    """Version 1 API Controller Root."""

    bays = bay.BayController()
    pods = pod.PodController()
    services = service.ServiceController()
    containers = container.ContainerController()

    @exception.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(Platform)
    def index(self):
        host_url = '%s/%s' % (pecan.request.host_url, 'v1')
        return Platform(uri=host_url,
                        name='magnum',
                        type='platform',
                        description='magnum native implementation',
                        implementation_version=version.version_string(),
                        bays_uri='%s/bays' % host_url,
                        pods_uri='%s/pods' % host_url,
                        services_uri='%s/services' % host_url,
                        containers_uri='%s/containers' % host_url)
