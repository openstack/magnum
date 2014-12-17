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
from magnum.common import context
from magnum.common import exception
from magnum.conductor import api
from magnum import objects


class BayPatchType(types.JsonPatchType):

    @staticmethod
    def mandatory_attrs():
        return ['/bay_uuid']


class Bay(base.APIBase):
    """API representation of a bay.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a bay.
    """

    _bay_uuid = None

    def _get_bay_uuid(self):
        return self._bay_uuid

    def _set_bay_uuid(self, value):
        if value and self._bay_uuid != value:
            try:
                # FIXME(comstud): One should only allow UUID here, but
                # there seems to be a bug in that tests are passing an
                # ID. See bug #1301046 for more details.
                bay = objects.Bay.get(pecan.request.context, value)
                self._bay_uuid = bay.uuid
                # NOTE(lucasagomes): Create the bay_id attribute on-the-fly
                #                    to satisfy the api -> rpc object
                #                    conversion.
                self.bay_id = bay.id
            except exception.BayNotFound as e:
                # Change error code because 404 (NotFound) is inappropriate
                # response for a POST request to create a Bay
                e.code = 400  # BadRequest
                raise e
        elif value == wtypes.Unset:
            self._bay_uuid = wtypes.Unset

    uuid = types.uuid
    """Unique UUID for this bay"""

    name = wtypes.text
    """Name of this bay"""

    baymodel_id = wtypes.text
    """The bay model UUID or id"""

    node_count = wtypes.IntegerType()
    """The node count for this bay"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated bay links"""

    def __init__(self, **kwargs):
        super(Bay, self).__init__()
        self.backend_api = api.API(context=context.RequestContext())

        self.fields = []
        fields = list(objects.Bay.fields)
        # NOTE(lucasagomes): bay_uuid is not part of objects.Bay.fields
        #                    because it's an API-only attribute
        fields.append('bay_uuid')
        for field in fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

        # NOTE(lucasagomes): bay_id is an attribute created on-the-fly
        # by _set_bay_uuid(), it needs to be present in the fields so
        # that as_dict() will contain bay_id field when converting it
        # before saving it in the database.
        self.fields.append('bay_id')
        setattr(self, 'bay_uuid', kwargs.get('bay_id', wtypes.Unset))

    @staticmethod
    def _convert_with_links(bay, url, expand=True):
        if not expand:
            bay.unset_fields_except(['uuid', 'name', 'type', 'image_id',
                                    'node_count'])

        # never expose the bay_id attribute
        bay.bay_id = wtypes.Unset

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
                     type='virt',
                     image_id='Fedora-k8s',
                     node_count=1,
                     created_at=datetime.datetime.utcnow(),
                     updated_at=datetime.datetime.utcnow())
        # NOTE(lucasagomes): bay_uuid getter() method look at the
        # _bay_uuid variable
        sample._bay_uuid = '7ae81bb3-dec3-4289-8d6c-da80bd8001ae'
        return cls._convert_with_links(sample, 'http://localhost:9511', expand)


class BayCollection(collection.Collection):
    """API representation of a collection of bays."""

    bays = [Bay]
    """A list containing bays objects"""

    def __init__(self, **kwargs):
        self._type = 'bays'
        self.backend_api = api.API(context=context.RequestContext())

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
        self.backend_api = api.API(context=context.RequestContext())

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

        bays = self.backend_api.bay_list(pecan.request.context, limit,
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

    @wsme_pecan.wsexpose(Bay, types.uuid)
    def get_one(self, bay_uuid):
        """Retrieve information about the given bay.

        :param bay_uuid: UUID of a bay.
        """
        if self.from_bays:
            raise exception.OperationNotPermitted

        rpc_bay = objects.Bay.get_by_uuid(pecan.request.context, bay_uuid)
        return Bay.convert_with_links(rpc_bay)

    @wsme_pecan.wsexpose(Bay, body=Bay, status_code=201)
    def post(self, bay):
        """Create a new bay.

        :param bay: a bay within the request body.
        """
        if self.from_bays:
            raise exception.OperationNotPermitted

        new_bay = objects.Bay(pecan.request.context, **bay.as_dict())
        res_bay = self.backend_api.bay_create(new_bay)

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
            # NOTE(lucasagomes):
            # 1) Remove bay_id because it's an internal value and
            #    not present in the API object
            # 2) Add bay_uuid
            bay_dict['bay_uuid'] = bay_dict.pop('bay_id', None)
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

        if hasattr(pecan.request, 'rpcapi'):
            rpc_bay = objects.Bay.get_by_id(pecan.request.context,
                                             rpc_bay.bay_id)
            topic = pecan.request.rpcapi.get_topic_for(rpc_bay)

            new_bay = pecan.request.rpcapi.update_bay(
                pecan.request.context, rpc_bay, topic)

            return Bay.convert_with_links(new_bay)
        else:
            rpc_bay.save()
            return Bay.convert_with_links(rpc_bay)

    @wsme_pecan.wsexpose(None, types.uuid, status_code=204)
    def delete(self, bay_uuid):
        """Delete a bay.

        :param bay_uuid: UUID of a bay.
        """
        if self.from_bays:
            raise exception.OperationNotPermitted

        rpc_bay = objects.Bay.get_by_uuid(pecan.request.context,
                                            bay_uuid)
        rpc_bay.destroy()
