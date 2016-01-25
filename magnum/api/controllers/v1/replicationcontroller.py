# Copyright 2015 IBM Corp.
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

from oslo_utils import timeutils
import pecan
from pecan import rest
import wsme
from wsme import types as wtypes

from magnum.api.controllers import link
from magnum.api.controllers.v1 import base as v1_base
from magnum.api.controllers.v1 import collection
from magnum.api.controllers.v1 import types
from magnum.api import expose
from magnum.api import utils as api_utils
from magnum.api import validation
from magnum.common import exception
from magnum.common import k8s_manifest
from magnum.common import policy
from magnum.i18n import _
from magnum import objects


class ReplicationControllerPatchType(v1_base.K8sPatchType):

    @staticmethod
    def internal_attrs():
        defaults = v1_base.K8sPatchType.internal_attrs()
        return defaults + ['/replicas']


class ReplicationController(v1_base.K8sResourceBase):
    """API representation of a ReplicationController.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a
    ReplicationController.
    """

    uuid = types.uuid
    """Unique UUID for this ReplicationController"""

    images = [wtypes.text]
    """A list of images used by containers in this ReplicationController."""

    replicas = wsme.wsattr(wtypes.IntegerType(), readonly=True)
    """Replicas of this ReplicationController"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated rc links"""

    def __init__(self, **kwargs):
        super(ReplicationController, self).__init__()

        self.fields = []
        for field in objects.ReplicationController.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @staticmethod
    def _convert_with_links(rc, url, expand=True):
        if not expand:
            rc.unset_fields_except(['uuid', 'name', 'images', 'bay_uuid',
                                    'labels', 'replicas'])

        rc.links = [link.Link.make_link('self', url,
                                        'rcs', rc.uuid),
                    link.Link.make_link('bookmark', url,
                                        'rcs', rc.uuid,
                                        bookmark=True)]
        return rc

    @classmethod
    def convert_with_links(cls, rpc_rc, expand=True):
        rc = ReplicationController(**rpc_rc.as_dict())
        return cls._convert_with_links(rc, pecan.request.host_url, expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(uuid='f978db47-9a37-4e9f-8572-804a10abc0aa',
                     name='MyReplicationController',
                     images=['MyImage'],
                     bay_uuid='f978db47-9a37-4e9f-8572-804a10abc0ab',
                     labels={'name': 'foo'},
                     replicas=2,
                     manifest_url='file:///tmp/rc.yaml',
                     manifest='''{
                         "metadata": {
                             "name": "name_of_rc"
                         },
                         "spec":{
                             "replicas":2,
                             "selector":{
                                 "name":"frontend"
                             },
                             "template":{
                                 "metadata":{
                                     "labels":{
                                         "name":"frontend"
                                     }
                                 },
                                 "spec":{
                                     "containers":[
                                         {
                                             "name":"test-redis",
                                             "image":"steak/for-dinner",
                                             "ports":[
                                                 {
                                                     "containerPort":80,
                                                     "protocol":"TCP"
                                                 }
                                             ]
                                         }
                                     ]
                                 }
                             }
                         }
                     }''',
                     created_at=timeutils.utcnow(),
                     updated_at=timeutils.utcnow())
        return cls._convert_with_links(sample, 'http://localhost:9511', expand)

    def parse_manifest(self):
        try:
            manifest = k8s_manifest.parse(self._get_manifest())
        except ValueError as e:
            raise exception.InvalidParameterValue(message=str(e))
        try:
            self.name = manifest["metadata"]["name"]
        except (KeyError, TypeError):
            raise exception.InvalidParameterValue(
                _("Field metadata['name'] can't be empty in manifest."))
        try:
            self.replicas = manifest["spec"]["replicas"]
        except (KeyError, TypeError):
            pass
        try:
            self.selector = manifest["spec"]["selector"]
        except (KeyError, TypeError):
            raise exception.InvalidParameterValue(
                _("Field spec['selector'] can't be empty in manifest."))
        try:
            self.labels = manifest["spec"]["template"]["metadata"]["labels"]
        except (KeyError, TypeError):
            raise exception.InvalidParameterValue(_(
                "Field spec['template']['metadata']['labels'] "
                "can't be empty in manifest."))
        try:
            images = []
            for cont in manifest["spec"]["template"]["spec"]["containers"]:
                images.append(cont["image"])
            self.images = images
        except (KeyError, TypeError):
            raise exception.InvalidParameterValue(_(
                "Field spec['template']['spec']['containers'] "
                "can't be empty in manifest."))


class ReplicationControllerCollection(collection.Collection):
    """API representation of a collection of ReplicationControllers."""

    rcs = [ReplicationController]
    """A list containing ReplicationController objects"""

    def __init__(self, **kwargs):
        self._type = 'rcs'

    @staticmethod
    def convert_with_links(rpc_rcs, limit, url=None, expand=False, **kwargs):
        collection = ReplicationControllerCollection()
        collection.rcs = [ReplicationController.convert_with_links(p, expand)
                          for p in rpc_rcs]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.rcs = [ReplicationController.sample(expand=False)]
        return sample


class ReplicationControllersController(rest.RestController):
    """REST controller for ReplicationControllers."""

    def __init__(self):
        super(ReplicationControllersController, self).__init__()

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_rcs_collection(self, marker, limit,
                            sort_key, sort_dir,
                            bay_ident, expand=False,
                            resource_url=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)
        rcs = pecan.request.rpcapi.rc_list(pecan.request.context, bay_ident)

        return ReplicationControllerCollection.convert_with_links(
            rcs, limit,
            url=resource_url,
            expand=expand,
            sort_key=sort_key,
            sort_dir=sort_dir)

    @expose.expose(ReplicationControllerCollection, types.uuid,
                   types.uuid_or_name, int, wtypes.text, wtypes.text)
    @policy.enforce_wsgi("rc")
    @validation.enforce_bay_types('kubernetes')
    def get_all(self, marker=None, bay_ident=None, limit=None, sort_key='id',
                sort_dir='asc'):
        """Retrieve a list of ReplicationControllers.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param bay_ident: UUID or logical name of the Bay.
        """
        return self._get_rcs_collection(marker, limit, sort_key,
                                        sort_dir, bay_ident)

    @expose.expose(ReplicationControllerCollection, types.uuid,
                   types.uuid_or_name, int, wtypes.text, wtypes.text)
    @policy.enforce_wsgi("rc")
    @validation.enforce_bay_types('kubernetes')
    def detail(self, marker=None, bay_ident=None, limit=None, sort_key='id',
               sort_dir='asc'):
        """Retrieve a list of ReplicationControllers with detail.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param bay_ident: UUID or logical name of the Bay.
        """
        # NOTE(jay-lau-513): /detail should only work against collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "rcs":
            raise exception.HTTPNotFound

        expand = True
        resource_url = '/'.join(['rcs', 'detail'])
        return self._get_rcs_collection(marker, limit,
                                        sort_key, sort_dir,
                                        bay_ident, expand,
                                        resource_url)

    @expose.expose(ReplicationController, types.uuid_or_name,
                   types.uuid_or_name)
    @policy.enforce_wsgi("rc", "get")
    @validation.enforce_bay_types('kubernetes')
    def get_one(self, rc_ident, bay_ident):
        """Retrieve information about the given ReplicationController.

        :param rc_ident: UUID or logical name of a ReplicationController.
        :param bay_ident: UUID or logical name of the Bay.
        """
        context = pecan.request.context
        rpc_rc = pecan.request.rpcapi.rc_show(context, rc_ident, bay_ident)
        return ReplicationController.convert_with_links(rpc_rc)

    @expose.expose(ReplicationController, body=ReplicationController,
                   status_code=201)
    @policy.enforce_wsgi("rc", "create")
    @validation.enforce_bay_types('kubernetes')
    def post(self, rc):
        """Create a new ReplicationController.

        :param rc: a ReplicationController within the request body.
        """
        rc.parse_manifest()
        rc_dict = rc.as_dict()
        context = pecan.request.context
        rc_dict['project_id'] = context.project_id
        rc_dict['user_id'] = context.user_id
        rc_obj = objects.ReplicationController(context, **rc_dict)
        new_rc = pecan.request.rpcapi.rc_create(rc_obj)
        if not new_rc:
            raise exception.InvalidState()

        # Set the HTTP Location Header
        pecan.response.location = link.build_url('rcs', new_rc.uuid)
        return ReplicationController.convert_with_links(new_rc)

    @wsme.validate(types.uuid, [ReplicationControllerPatchType])
    @expose.expose(ReplicationController, types.uuid_or_name,
                   types.uuid_or_name, body=[ReplicationControllerPatchType])
    @policy.enforce_wsgi("rc", "update")
    @validation.enforce_bay_types('kubernetes')
    def patch(self, rc_ident, bay_ident, patch):
        """Update an existing rc.

        :param rc_ident: UUID or logical name of a ReplicationController.
        :param bay_ident: UUID or logical name of the Bay.
        :param patch: a json PATCH document to apply to this rc.
        """
        rc_dict = {}
        rc_dict['manifest'] = None
        rc_dict['manifest_url'] = None
        try:
            rc = ReplicationController(**api_utils.apply_jsonpatch(rc_dict,
                                                                   patch))
            if rc.manifest or rc.manifest_url:
                rc.parse_manifest()
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        rpc_rc = pecan.request.rpcapi.rc_update(rc_ident,
                                                bay_ident,
                                                rc.manifest)
        return ReplicationController.convert_with_links(rpc_rc)

    @expose.expose(None, types.uuid_or_name,
                   types.uuid_or_name, status_code=204)
    @policy.enforce_wsgi("rc")
    @validation.enforce_bay_types('kubernetes')
    def delete(self, rc_ident, bay_ident):
        """Delete a ReplicationController.

        :param rc_ident: UUID or logical name of a ReplicationController.
        :param bay_ident: UUID or logical name of the Bay.
        """
        pecan.request.rpcapi.rc_delete(rc_ident, bay_ident)
