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
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from magnum.api.controllers import common_types
from magnum.api.controllers.v1 import root as v1_root

STATUS_KIND = wtypes.Enum(str, 'SUPPORTED', 'CURRENT', 'DEPRECATED')


class Version(wtypes.Base):
    """Version representation."""

    id = wtypes.text
    "The version identifier."

    status = STATUS_KIND
    "The status of the API (SUPPORTED, CURRENT or DEPRECATED)."

    link = common_types.Link
    "The link to the versioned API."

    @classmethod
    def sample(cls):
        return cls(id='v1.0',
                   status='CURRENT',
                   link=common_types.Link(target_name='v1',
                                          href='http://example.com:9511/v1'))


class RootController(object):

    v1 = v1_root.Controller()

    @wsme_pecan.wsexpose([Version])
    def index(self):
        host_url = '%s/%s' % (pecan.request.host_url, 'v1')
        Version(id='v1.0',
                status='CURRENT',
                link=common_types.Link(target_name='v1',
                                       href=host_url))
