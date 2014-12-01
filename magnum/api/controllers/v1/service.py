#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import uuid

import pecan
from pecan import rest
import wsme
from wsme import types as wtypes

from magnum.api.controllers.v1.base import Base
from magnum.common import exception
from magnum.common import yamlutils


# NOTE(dims): We don't depend on oslo*i18n yet
_ = _LI = _LW = _LE = _LC = lambda x: x


class ServiceController(rest.RestController):
    @exception.wrap_pecan_controller_exception
    @pecan.expose(content_type='application/x-yaml')
    def get(self):
        """Retrieve a service by UUID."""
        res_yaml = yamlutils.dump({'dummy_data'})
        pecan.response.status = 200
        return res_yaml

    @exception.wrap_pecan_controller_exception
    @pecan.expose(content_type='application/x-yaml')
    def put(self):
        """Create a new service."""
        res_yaml = yamlutils.dump({'dummy_data'})
        pecan.response.status = 200
        return res_yaml

    @exception.wrap_pecan_controller_exception
    @pecan.expose(content_type='application/x-yaml')
    def delete(self):
        """Delete an existing service."""
        res_yaml = yamlutils.dump({'dummy_data'})
        pecan.response.status = 200
        return res_yaml


class Service(Base):
    id = wtypes.text
    """ The ID of the services."""

    name = wsme.wsattr(wtypes.text, mandatory=True)
    """ The name of the service."""

    desc = wsme.wsattr(wtypes.text, mandatory=True)

    def __init__(self, **kwargs):
        super(Service, self).__init__(**kwargs)

    @classmethod
    def sample(cls):
        return cls(id=str(uuid.uuid1(),
                          name="Docker",
                          desc='Docker Services'))
