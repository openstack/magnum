# Copyright 2013 UnitedStack Inc.
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

import datetime

import pecan
from pecan import rest
import wsme
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from magnum.api.controllers import base
from magnum.api.controllers import link
from magnum.api.controllers.v1 import collection
from magnum.api.controllers.v1 import types
from magnum.api.controllers.v1 import utils as api_utils
from magnum.common import exception
from magnum import objects


class BayPatchType(types.JsonPatchType):

    @staticmethod
    def mandatory_attrs():
        return ['/baymodel_id']


class Bay(base.APIBase):
    """API representation of a bay.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a bay.
    """

    _baymodel_id = None

    def _get_baymodel_id(self):
        return self._baymodel_id

    def _set_baymodel_id(self, value):
        if value and self._baymodel_id != value:
            try:
                baymodel = api_utils.get_rpc_resource('BayModel', value)
                self._baymodel_id = baymodel.uuid
            except exception.BayModelNotFound as e:
                # Change error code because 404 (NotFound) is inappropriate
                # response for a POST request to create a Bay
                e.code = 400  # BadRequest
                raise e
        elif value == wtypes.Unset:
            self._baymodel_id = wtypes.Unset

    uuid = types.uuid
    """Unique UUID for this bay"""

    name = wtypes.text
    """Name of this bay"""

    baymodel_id = wsme.wsproperty(wtypes.text, _get_baymodel_id,
                                  _set_baymodel_id, mandatory=True)
    """The bay model UUID or id"""

    node_count = wtypes.IntegerType(minimum=1)
    """The node count for this bay"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated bay links"""

    status = wtypes.text
    """Status of the bay from the heat stack"""

    def __init__(self, **kwargs):
        super(Bay, self).__init__()

        self.fields = []
        for field in objects.Bay.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @staticmethod
    def _convert_with_links(bay, url, expand=True):
        if not expand:
            bay.unset_fields_except(['uuid', 'name', 'baymodel_id',
                                    'node_count', 'status'])

        bay.links = [link.Link.make_link('self', url,
                                          'bays', bay.uuid),
                      link.Link.make_link('bookmark', url,
                                          'bays', bay.uuid,
                                          bookmark=True)
                     ]
        return bay

    @classmethod
    def convert_with_links(cls, rpc_bay, expand=True):
        bay = Bay(**rpc_bay.as_dict())
        return cls._convert_with_links(bay, pecan.request.host_url, expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(uuid='27e3153e-d5bf-4b7e-b517-fb518e17f34c',
                     name='example',
                     baymodel_id='4a96ac4b-2447-43f1-8ca6-9fd6f36d146d',
                     node_count=1,
                     status="CREATED",
                     created_at=datetime.datetime.utcnow(),
                     updated_at=datetime.datetime.utcnow())
        return cls._convert_with_links(sample, 'http://localhost:9511', expand)


class BayCollection(collection.Collection):
    """API representation of a collection of bays."""

    bays = [Bay]
    """A list containing bays objects"""

    def __init__(self, **kwargs):
        self._type = 'bays'

    @staticmethod
    def convert_with_links(rpc_bays, limit, url=None, expand=False, **kwargs):
        collection = BayCollection()
        collection.bays = [Bay.convert_with_links(p, expand)
                            for p in rpc_bays]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.bays = [Bay.sample(expand=False)]
        return sample


class BaysController(rest.RestController):
    """REST controller for Bays."""
    def __init__(self):
        super(BaysController, self).__init__()

    from_bays = False
    """A flag to indicate if the requests to this controller are coming
    from the top-level resource Bays."""

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_bays_collection(self, marker, limit,
                              sort_key, sort_dir, expand=False,
                              resource_url=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Bay.get_by_uuid(pecan.request.context,
                                                  marker)

        bays = pecan.request.rpcapi.bay_list(pecan.request.context, limit,
                                         marker_obj, sort_key=sort_key,
                                         sort_dir=sort_dir)

        return BayCollection.convert_with_links(bays, limit,
                                                url=resource_url,
                                                expand=expand,
                                                sort_key=sort_key,
                                                sort_dir=sort_dir)

    @wsme_pecan.wsexpose(BayCollection, types.uuid,
                         types.uuid, int, wtypes.text, wtypes.text)
    def get_all(self, bay_uuid=None, marker=None, limit=None,
                sort_key='id', sort_dir='asc'):
        """Retrieve a list of bays.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        return self._get_bays_collection(marker, limit, sort_key,
                                         sort_dir)

    @wsme_pecan.wsexpose(BayCollection, types.uuid,
                         types.uuid, int, wtypes.text, wtypes.text)
    def detail(self, bay_uuid=None, marker=None, limit=None,
                sort_key='id', sort_dir='asc'):
        """Retrieve a list of bays with detail.

        :param bay_uuid: UUID of a bay, to get only bays for that bay.
        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        # NOTE(lucasagomes): /detail should only work agaist collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "bays":
            raise exception.HTTPNotFound

        expand = True
        resource_url = '/'.join(['bays', 'detail'])
        return self._get_bays_collection(marker, limit,
                                         sort_key, sort_dir, expand,
                                         resource_url)

    @wsme_pecan.wsexpose(Bay, types.uuid_or_name)
    def get_one(self, bay_ident):
        """Retrieve information about the given bay.

        :param bay_ident: UUID of a bay or logical name of the bay.
        """
        if self.from_bays:
            raise exception.OperationNotPermitted

        rpc_bay = api_utils.get_rpc_resource('Bay', bay_ident)

        return Bay.convert_with_links(rpc_bay)

    @wsme_pecan.wsexpose(Bay, body=Bay, status_code=201)
    def post(self, bay):
        """Create a new bay.

        :param bay: a bay within the request body.
        """
        if self.from_bays:
            raise exception.OperationNotPermitted

        bay_dict = bay.as_dict()
        context = pecan.request.context
        auth_token = context.auth_token_info['token']
        bay_dict['project_id'] = auth_token['project']['id']
        bay_dict['user_id'] = auth_token['user']['id']
        new_bay = objects.Bay(context, **bay_dict)
        res_bay = pecan.request.rpcapi.bay_create(new_bay)

        # Set the HTTP Location Header
        pecan.response.location = link.build_url('bays', res_bay.uuid)
        return Bay.convert_with_links(res_bay)

    @wsme.validate(types.uuid, [BayPatchType])
    @wsme_pecan.wsexpose(Bay, types.uuid, body=[BayPatchType])
    def patch(self, bay_uuid, patch):
        """Update an existing bay.

        :param bay_uuid: UUID of a bay.
        :param patch: a json PATCH document to apply to this bay.
        """
        if self.from_bays:
            raise exception.OperationNotPermitted

        rpc_bay = objects.Bay.get_by_uuid(pecan.request.context, bay_uuid)
        try:
            bay_dict = rpc_bay.as_dict()
            bay = Bay(**api_utils.apply_jsonpatch(bay_dict, patch))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        # Update only the fields that have changed
        for field in objects.Bay.fields:
            try:
                patch_val = getattr(bay, field)
            except AttributeError:
                # Ignore fields that aren't exposed in the API
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if rpc_bay[field] != patch_val:
                rpc_bay[field] = patch_val

        res_bay = pecan.request.rpcapi.bay_update(rpc_bay)
        return Bay.convert_with_links(res_bay)

    @wsme_pecan.wsexpose(None, types.uuid_or_name, status_code=204)
    def delete(self, bay_ident):
        """Delete a bay.

        :param bay_ident: UUID of a bay or logical name of the bay.
        """
        if self.from_bays:
            raise exception.OperationNotPermitted

        rpc_bay = api_utils.get_rpc_resource('Bay', bay_ident)

        pecan.request.rpcapi.bay_delete(rpc_bay.uuid)
