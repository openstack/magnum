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

import datetime

import pecan
from pecan import rest
import wsme
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from magnum.api.controllers import link
from magnum.api.controllers.v1 import bay
from magnum.api.controllers.v1 import baymodel
from magnum.api.controllers.v1 import container
from magnum.api.controllers.v1 import node
from magnum.api.controllers.v1 import pod
from magnum.api.controllers.v1 import service


class APIBase(wtypes.Base):

    created_at = wsme.wsattr(datetime.datetime, readonly=True)
    """The time in UTC at which the object is created"""

    updated_at = wsme.wsattr(datetime.datetime, readonly=True)
    """The time in UTC at which the object is updated"""

    def as_dict(self):
        """Render this object as a dict of its fields."""
        return dict((k, getattr(self, k))
                    for k in self.fields
                    if hasattr(self, k) and
                    getattr(self, k) != wsme.Unset)

    def unset_fields_except(self, except_list=None):
        """Unset fields so they don't appear in the message body.

        :param except_list: A list of fields that won't be touched.

        """
        if except_list is None:
            except_list = []

        for k in self.as_dict():
            if k not in except_list:
                setattr(self, k, wsme.Unset)


class MediaType(APIBase):
    """A media type representation."""

    base = wtypes.text
    type = wtypes.text

    def __init__(self, base, type):
        self.base = base
        self.type = type


class V1(APIBase):
    """The representation of the version 1 of the API."""

    id = wtypes.text
    """The ID of the version, also acts as the release number"""

    media_types = [MediaType]
    """An array of supcontainersed media types for this version"""

    links = [link.Link]
    """Links that point to a specific URL for this version and documentation"""

    pods = [link.Link]
    """Links to the pods resource"""

    baymodels = [link.Link]
    """Links to the baymodels resource"""

    bays = [link.Link]
    """Links to the bays resource"""

    containers = [link.Link]
    """Links to the containers resource"""

    services = [link.Link]
    """Links to the services resource"""

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
                                        bookmark=True, type='text/html')
                   ]
        v1.media_types = [MediaType('application/json',
                          'application/vnd.openstack.magnum.v1+json')]
        v1.pods = [link.Link.make_link('self', pecan.request.host_url,
                                          'pods', ''),
                      link.Link.make_link('bookmark',
                                           pecan.request.host_url,
                                           'pods', '',
                                           bookmark=True)
                     ]
        v1.baymodels = [link.Link.make_link('self', pecan.request.host_url,
                                        'baymodels', ''),
                    link.Link.make_link('bookmark',
                                        pecan.request.host_url,
                                        'bays', '',
                                        bookmark=True)
                   ]
        v1.bays = [link.Link.make_link('self', pecan.request.host_url,
                                        'bays', ''),
                    link.Link.make_link('bookmark',
                                        pecan.request.host_url,
                                        'bays', '',
                                        bookmark=True)
                   ]
        v1.containers = [link.Link.make_link('self', pecan.request.host_url,
                                        'containers', ''),
                    link.Link.make_link('bookmark',
                                        pecan.request.host_url,
                                        'containers', '',
                                        bookmark=True)
                   ]
        v1.services = [link.Link.make_link('self', pecan.request.host_url,
                                          'services', ''),
                      link.Link.make_link('bookmark',
                                          pecan.request.host_url,
                                          'services', '',
                                          bookmark=True)
                     ]
        return v1


class Controller(rest.RestController):
    """Version 1 API controller root."""

    bays = bay.BaysController()
    baymodels = baymodel.BayModelsController()
    containers = container.ContainersController()
    nodes = node.NodesController()
    pods = pod.PodsController()
    services = service.ServicesController()

    @wsme_pecan.wsexpose(V1)
    def get(self):
        # NOTE: The reason why convert() it's being called for every
        #       request is because we need to get the host url from
        #       the request object to make the links.
        return V1.convert()

__all__ = (Controller)
