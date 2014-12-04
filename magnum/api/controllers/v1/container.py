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


class ContainerPatchType(types.JsonPatchType):

    @staticmethod
    def mandatory_attrs():
        return ['/container_uuid']


class Container(base.APIBase):
    """API representation of a container.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a
    container.
    """

    _container_uuid = None

    def _get_container_uuid(self):
        return self._container_uuid

    def _set_container_uuid(self, value):
        if value and self._container_uuid != value:
            try:
                # FIXME(comstud): One should only allow UUID here, but
                # there seems to be a bug in that tests are passing an
                # ID. See bug #1301046 for more details.
                container = objects.Container.get(pecan.request.context, value)
                self._container_uuid = container.uuid
                # NOTE(lucasagomes): Create the container_id attribute
                # on-the-fly to satisfy the api -> rpc object conversion.
                self.container_id = container.id
            except exception.ContainerNotFound as e:
                # Change error code because 404 (NotFound) is inappropriate
                # response for a POST request to create a Container
                e.code = 400  # BadRequest
                raise e
        elif value == wtypes.Unset:
            self._container_uuid = wtypes.Unset

    uuid = types.uuid
    """Unique UUID for this container"""

    name = wtypes.text
    """Name of this container"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated container links"""

    def __init__(self, **kwargs):
        self.fields = []
        fields = list(objects.Container.fields)
        # NOTE(lucasagomes): container_uuid is not part of
        # objects.Container.fields because it's an API-only attribute
        fields.append('container_uuid')
        for field in fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

        # NOTE(lucasagomes): container_id is an attribute created on-the-fly
        # by _set_container_uuid(), it needs to be present in the fields so
        # that as_dict() will contain container_id field when converting it
        # before saving it in the database.
        self.fields.append('container_id')
        setattr(self, 'container_uuid',
                kwargs.get('container_id', wtypes.Unset))

    @staticmethod
    def _convert_with_links(container, url, expand=True):
        if not expand:
            container.unset_fields_except(['uuid', 'name'])

        # never expose the container_id attribute
        container.container_id = wtypes.Unset

        container.links = [link.Link.make_link('self', url,
                                          'containers', container.uuid),
                      link.Link.make_link('bookmark', url,
                                          'containers', container.uuid,
                                          bookmark=True)
                     ]
        return container

    @classmethod
    def convert_with_links(cls, rpc_container, expand=True):
        container = Container(**rpc_container.as_dict())
        return cls._convert_with_links(container, pecan.request.host_url,
                                       expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(uuid='27e3153e-d5bf-4b7e-b517-fb518e17f34c',
                     name='example',
                     created_at=datetime.datetime.utcnow(),
                     updated_at=datetime.datetime.utcnow())
        # NOTE(lucasagomes): container_uuid getter() method look at the
        # _container_uuid variable
        sample._container_uuid = '7ae81bb3-dec3-4289-8d6c-da80bd8001ae'
        return cls._convert_with_links(sample, 'http://localhost:9511', expand)


class ContainerCollection(collection.Collection):
    """API representation of a collection of containers."""

    containers = [Container]
    """A list containing containers objects"""

    def __init__(self, **kwargs):
        self._type = 'containers'

    @staticmethod
    def convert_with_links(rpc_containers, limit, url=None,
                           expand=False, **kwargs):
        collection = ContainerCollection()
        collection.containers = [Container.convert_with_links(p, expand)
                            for p in rpc_containers]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.containers = [Container.sample(expand=False)]
        return sample


class ContainersController(rest.RestController):
    """REST controller for Containers."""

    from_containers = False
    """A flag to indicate if the requests to this controller are coming
    from the top-level resource Containers."""

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_containers_collection(self, marker, limit,
                              sort_key, sort_dir, expand=False,
                              resource_url=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Container.get_by_uuid(pecan.request.context,
                                                  marker)

        containers = objects.Container.list(pecan.request.context, limit,
                                marker_obj, sort_key=sort_key,
                                sort_dir=sort_dir)

        return ContainerCollection.convert_with_links(containers, limit,
                                                url=resource_url,
                                                expand=expand,
                                                sort_key=sort_key,
                                                sort_dir=sort_dir)

    @wsme_pecan.wsexpose(ContainerCollection, types.uuid,
                         types.uuid, int, wtypes.text, wtypes.text)
    def get_all(self, container_uuid=None, marker=None, limit=None,
                sort_key='id', sort_dir='asc'):
        """Retrieve a list of containers.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        return self._get_containers_collection(marker, limit, sort_key,
                                         sort_dir)

    @wsme_pecan.wsexpose(ContainerCollection, types.uuid,
                         types.uuid, int, wtypes.text, wtypes.text)
    def detail(self, container_uuid=None, marker=None, limit=None,
                sort_key='id', sort_dir='asc'):
        """Retrieve a list of containers with detail.

        :param container_uuid: UUID of a container, to get only containers
                               for that container.
        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        # NOTE(lucasagomes): /detail should only work agaist collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "containers":
            raise exception.HTTPNotFound

        expand = True
        resource_url = '/'.join(['containers', 'detail'])
        return self._get_containers_collection(marker, limit,
                                         sort_key, sort_dir, expand,
                                         resource_url)

    @wsme_pecan.wsexpose(Container, types.uuid)
    def get_one(self, container_uuid):
        """Retrieve information about the given container.

        :param container_uuid: UUID of a container.
        """
        if self.from_containers:
            raise exception.OperationNotPermitted

        rpc_container = objects.Container.get_by_uuid(pecan.request.context,
                                                      container_uuid)
        return Container.convert_with_links(rpc_container)

    @wsme_pecan.wsexpose(Container, body=Container, status_code=201)
    def post(self, container):
        """Create a new container.

        :param container: a container within the request body.
        """
        if self.from_containers:
            raise exception.OperationNotPermitted

        new_container = objects.Container(pecan.request.context,
                                **container.as_dict())
        new_container.create()
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('containers',
                                                 new_container.uuid)
        return Container.convert_with_links(new_container)

    @wsme.validate(types.uuid, [ContainerPatchType])
    @wsme_pecan.wsexpose(Container, types.uuid, body=[ContainerPatchType])
    def patch(self, container_uuid, patch):
        """Update an existing container.

        :param container_uuid: UUID of a container.
        :param patch: a json PATCH document to apply to this container.
        """
        if self.from_containers:
            raise exception.OperationNotPermitted

        rpc_container = objects.Container.get_by_uuid(pecan.request.context,
                                                      container_uuid)
        try:
            container_dict = rpc_container.as_dict()
            # NOTE(lucasagomes):
            # 1) Remove container_id because it's an internal value and
            #    not present in the API object
            # 2) Add container_uuid
            container_dict['container_uuid'] = container_dict.pop(
                'container_id', None)
            container = Container(**api_utils.apply_jsonpatch(
                container_dict, patch))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        # Update only the fields that have changed
        for field in objects.Container.fields:
            try:
                patch_val = getattr(container, field)
            except AttributeError:
                # Ignore fields that aren't exposed in the API
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if rpc_container[field] != patch_val:
                rpc_container[field] = patch_val

        if hasattr(pecan.request, 'rpcapi'):
            rpc_container = objects.Container.get_by_id(pecan.request.context,
                                             rpc_container.container_id)
            topic = pecan.request.rpcapi.get_topic_for(rpc_container)

            new_container = pecan.request.rpcapi.update_container(
                pecan.request.context, rpc_container, topic)

            return Container.convert_with_links(new_container)
        else:
            rpc_container.save()
            return Container.convert_with_links(rpc_container)

    @wsme_pecan.wsexpose(None, types.uuid, status_code=204)
    def delete(self, container_uuid):
        """Delete a container.

        :param container_uuid: UUID of a container.
        """
        if self.from_containers:
            raise exception.OperationNotPermitted

        rpc_container = objects.Container.get_by_uuid(pecan.request.context,
                                            container_uuid)
        rpc_container.destroy()
