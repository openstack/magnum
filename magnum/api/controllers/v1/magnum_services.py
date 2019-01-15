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

import pecan
import wsme
from wsme import types as wtypes

from magnum.api.controllers import base
from magnum.api.controllers.v1 import collection
from magnum.api.controllers.v1 import types
from magnum.api import expose
from magnum.api import servicegroup as svcgrp_api
from magnum.common import policy
from magnum import objects
from magnum.objects import fields


class MagnumService(base.APIBase):

    host = wtypes.StringType(min_length=1, max_length=255)
    """Name of the host """

    binary = wtypes.Enum(wtypes.text, *fields.MagnumServiceBinary.ALL)
    """Name of the binary"""

    state = wtypes.Enum(wtypes.text, *fields.MagnumServiceState.ALL)
    """State of the binary"""

    id = wsme.wsattr(wtypes.IntegerType(minimum=1))
    """The id for the healthcheck record """

    report_count = wsme.wsattr(wtypes.IntegerType(minimum=0))
    """The number of times the heartbeat was reported """

    disabled = wsme.wsattr(types.boolean, default=False)
    """If the service is 'disabled' administratively """

    disabled_reason = wtypes.StringType(min_length=0, max_length=255)
    """Reason for disabling """

    def __init__(self, state, **kwargs):
        super(MagnumService, self).__init__()

        self.fields = ['state']
        setattr(self, 'state', state)
        for field in objects.MagnumService.fields:
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))


class MagnumServiceCollection(collection.Collection):

    mservices = [MagnumService]
    """A list containing service objects"""

    def __init__(self, **kwargs):
        super(MagnumServiceCollection, self).__init__()
        self._type = 'mservices'

    @staticmethod
    def convert_db_rec_list_to_collection(servicegroup_api,
                                          rpc_msvcs, **kwargs):
        collection = MagnumServiceCollection()
        collection.mservices = []
        for p in rpc_msvcs:
            alive = servicegroup_api.service_is_up(p)
            state = 'up' if alive else 'down'
            msvc = MagnumService(state, **p.as_dict())
            collection.mservices.append(msvc)
        collection.next = collection.get_next(limit=None, url=None, **kwargs)
        return collection


class MagnumServiceController(base.Controller):
    """REST controller for magnum-services."""

    def __init__(self, **kwargs):
        super(MagnumServiceController, self).__init__()
        self.servicegroup_api = svcgrp_api.ServiceGroup()

    @expose.expose(MagnumServiceCollection)
    @policy.enforce_wsgi("magnum-service")
    def get_all(self):
        """Retrieve a list of magnum-services.

        """
        msvcs = objects.MagnumService.list(pecan.request.context,
                                           limit=None,
                                           marker=None,
                                           sort_key='id',
                                           sort_dir='asc')

        return MagnumServiceCollection.convert_db_rec_list_to_collection(
            self.servicegroup_api, msvcs)
