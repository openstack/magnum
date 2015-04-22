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
from magnum.common import context as magnum_context
from magnum.common import exception
from magnum.conductor import api
from magnum import objects
from magnum.openstack.common import log as logging

LOG = logging.getLogger(__name__)


class ContainerPatchType(types.JsonPatchType):

    @staticmethod
    def mandatory_attrs():
        return ['/bay_uuid']


class Container(base.APIBase):
    """API representation of a container.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a
    container.
    """

    _bay_uuid = None

    def _get_bay_uuid(self):
        return self._bay_uuid

    def _set_bay_uuid(self, value):
        if value and self._bay_uuid != value:
            try:
                bay = objects.Bay.get_by_uuid(pecan.request.context, value)
                self._bay_uuid = bay['uuid']
            except exception.BayNotFound as e:
                # Change error code because 404 (NotFound) is inappropriate
                # response for a POST request to create a Service
                e.code = 400  # BadRequest
                raise e
        elif value == wtypes.Unset:
            self._bay_uuid = wtypes.Unset

    uuid = types.uuid
    """Unique UUID for this container"""

    name = wtypes.text
    """Name of this container"""

    image_id = wtypes.text
    """The image name or UUID to use as a base image for this baymodel"""

    bay_uuid = wsme.wsproperty(types.uuid, _get_bay_uuid, _set_bay_uuid,
                               mandatory=True)
    """Unique UUID of the bay this runs on"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated container links"""

    command = wtypes.text
    """The command execute when container starts"""

    def __init__(self, **kwargs):
        self.fields = []
        for field in objects.Container.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @staticmethod
    def _convert_with_links(container, url, expand=True):
        if not expand:
            container.unset_fields_except(['uuid', 'name', 'bay_uuid',
                                           'image_id', 'command'])

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
                     image_id='ubuntu',
                     command='env',
                     bay_uuid="fff114da-3bfa-4a0f-a123-c0dffad9718e",
                     created_at=datetime.datetime.utcnow(),
                     updated_at=datetime.datetime.utcnow())
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

backend_api = api.API(context=magnum_context.RequestContext())


class StartController(object):
    @wsme_pecan.wsexpose(wtypes.text, wtypes.text)
    def _default(self, container_uuid):
        if pecan.request.method != 'PUT':
            pecan.abort(405, ('HTTP method %s is not allowed'
                              % pecan.request.method))
        LOG.debug('Calling backend_api.container_start with %s' %
                  container_uuid)
        return backend_api.container_start(container_uuid)


class StopController(object):
    @wsme_pecan.wsexpose(wtypes.text, wtypes.text)
    def _default(self, container_uuid, *remainder):
        if pecan.request.method != 'PUT':
            pecan.abort(405, ('HTTP method %s is not allowed'
                              % pecan.request.method))
        LOG.debug('Calling backend_api.container_stop with %s' %
                  container_uuid)
        return backend_api.container_stop(container_uuid)


class RebootController(object):
    @wsme_pecan.wsexpose(wtypes.text, wtypes.text)
    def _default(self, container_uuid, *remainder):
        if pecan.request.method != 'PUT':
            pecan.abort(405, ('HTTP method %s is not allowed'
                              % pecan.request.method))
        LOG.debug('Calling backend_api.container_reboot with %s' %
                  container_uuid)
        return backend_api.container_reboot(container_uuid)


class PauseController(object):
    @wsme_pecan.wsexpose(wtypes.text, wtypes.text)
    def _default(self, container_uuid, *remainder):
        if pecan.request.method != 'PUT':
            pecan.abort(405, ('HTTP method %s is not allowed'
                              % pecan.request.method))
        LOG.debug('Calling backend_api.container_pause with %s' %
                  container_uuid)
        return backend_api.container_pause(container_uuid)


class UnpauseController(object):
    @wsme_pecan.wsexpose(wtypes.text, wtypes.text)
    def _default(self, container_uuid, *remainder):
        if pecan.request.method != 'PUT':
            pecan.abort(405, ('HTTP method %s is not allowed'
                              % pecan.request.method))
        LOG.debug('Calling backend_api.container_unpause with %s' %
                  container_uuid)
        return backend_api.container_unpause(container_uuid)


class LogsController(object):
    @wsme_pecan.wsexpose(wtypes.text, wtypes.text)
    def _default(self, container_uuid, *remainder):
        if pecan.request.method != 'GET':
            pecan.abort(405, ('HTTP method %s is not allowed'
                              % pecan.request.method))
        LOG.debug('Calling backend_api.container_logs with %s' %
        container_uuid)
        return backend_api.container_logs(container_uuid)


class ExecuteController(object):
    @wsme_pecan.wsexpose(wtypes.text, wtypes.text, wtypes.text)
    def _default(self, container_uuid, command, *remainder):
        if pecan.request.method != 'PUT':
            pecan.abort(405, ('HTTP method %s is not allowed'
                              % pecan.request.method))
        LOG.debug('Calling backend_api.container_execute with %s command %s'
                  % (container_uuid, command))
        return backend_api.container_execute(container_uuid, command)


class ContainersController(rest.RestController):
    """REST controller for Containers."""

    def __init__(self):
        super(ContainersController, self).__init__()

    start = StartController()
    stop = StopController()
    reboot = RebootController()
    pause = PauseController()
    unpause = UnpauseController()
    logs = LogsController()
    execute = ExecuteController()

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

        container_dict = container.as_dict()
        context = pecan.request.context
        auth_token = context.auth_token_info['token']
        container_dict['project_id'] = auth_token['project']['id']
        container_dict['user_id'] = auth_token['user']['id']
        new_container = objects.Container(context, **container_dict)
        new_container.create()
        res_container = backend_api.container_create(new_container.name,
                                                     new_container.uuid,
                                                     new_container)

        # Set the HTTP Location Header
        pecan.response.location = link.build_url('containers',
                                                 res_container.uuid)
        return Container.convert_with_links(res_container)

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

        rpc_container.save()
        return Container.convert_with_links(rpc_container)

    @wsme_pecan.wsexpose(None, types.uuid, status_code=204)
    def delete(self, container_uuid):
        """Delete a container.

        :param container_uuid: UUID of a container.
        """
        if self.from_containers:
            raise exception.OperationNotPermitted

        backend_api.container_delete(container_uuid)
        rpc_container = objects.Container.get_by_uuid(pecan.request.context,
                                            container_uuid)
        rpc_container.destroy()
