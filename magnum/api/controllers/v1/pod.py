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

from magnum.api.controllers import link
from magnum.api.controllers.v1 import base as v1_base
from magnum.api.controllers.v1 import collection
from magnum.api.controllers.v1 import types
from magnum.api.controllers.v1 import utils as api_utils
from magnum.common import exception
from magnum.common import k8s_manifest
from magnum import objects


class PodPatchType(v1_base.K8sPatchType):
    pass


class Pod(v1_base.K8sResourceBase):
    """API representation of a pod.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a pod.
    """

    uuid = types.uuid
    """Unique UUID for this pod"""

    desc = wtypes.text
    """Description of this pod"""

    images = [wtypes.text]
    """A list of images used by containers in this pod."""

    status = wtypes.text
    """Staus of this pod """

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated pod links"""

    def __init__(self, **kwargs):
        super(Pod, self).__init__()

        self.fields = []
        for field in objects.Pod.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @staticmethod
    def _convert_with_links(pod, url, expand=True):
        if not expand:
            pod.unset_fields_except(['uuid', 'name', 'desc', 'bay_uuid',
                                     'images', 'labels', 'status'])

        pod.links = [link.Link.make_link('self', url,
                                         'pods', pod.uuid),
                     link.Link.make_link('bookmark', url,
                                         'pods', pod.uuid,
                                         bookmark=True)
                     ]
        return pod

    @classmethod
    def convert_with_links(cls, rpc_pod, expand=True):
        pod = Pod(**rpc_pod.as_dict())
        return cls._convert_with_links(pod, pecan.request.host_url, expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(uuid='f978db47-9a37-4e9f-8572-804a10abc0aa',
                     name='MyPod',
                     desc='Pod - Description',
                     bay_uuid='7ae81bb3-dec3-4289-8d6c-da80bd8001ae',
                     images=['MyImage'],
                     labels={'name': 'foo'},
                     status='Running',
                     manifest_url='file:///tmp/rc.yaml',
                     manifest='''{
                         "id": "name_of_pod",
                         "labels": {
                             "foo": "foo1"
                         }
                     }''',
                     created_at=datetime.datetime.utcnow(),
                     updated_at=datetime.datetime.utcnow())
        return cls._convert_with_links(sample, 'http://localhost:9511', expand)

    def parse_manifest(self):
        manifest = k8s_manifest.parse(self._get_manifest())
        self.name = manifest["id"]
        if "labels" in manifest:
            self.labels = manifest["labels"]


class PodCollection(collection.Collection):
    """API representation of a collection of pods."""

    pods = [Pod]
    """A list containing pods objects"""

    def __init__(self, **kwargs):
        self._type = 'pods'

    @staticmethod
    def convert_with_links(rpc_pods, limit, url=None, expand=False, **kwargs):
        collection = PodCollection()
        collection.pods = [Pod.convert_with_links(p, expand)
                           for p in rpc_pods]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.pods = [Pod.sample(expand=False)]
        return sample


class PodsController(rest.RestController):
    """REST controller for Pods."""

    def __init__(self):
        super(PodsController, self).__init__()

    from_pods = False
    """A flag to indicate if the requests to this controller are coming
    from the top-level resource Pods."""

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_pods_collection(self, marker, limit,
                             sort_key, sort_dir, expand=False,
                             resource_url=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Pod.get_by_uuid(pecan.request.context,
                                                 marker)

        pods = pecan.request.rpcapi.pod_list(pecan.request.context, limit,
                                         marker_obj, sort_key=sort_key,
                                         sort_dir=sort_dir)

        return PodCollection.convert_with_links(pods, limit,
                                                url=resource_url,
                                                expand=expand,
                                                sort_key=sort_key,
                                                sort_dir=sort_dir)

    @wsme_pecan.wsexpose(PodCollection, types.uuid,
                         types.uuid, int, wtypes.text, wtypes.text)
    def get_all(self, pod_uuid=None, marker=None, limit=None,
                sort_key='id', sort_dir='asc'):
        """Retrieve a list of pods.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        return self._get_pods_collection(marker, limit, sort_key,
                                         sort_dir)

    @wsme_pecan.wsexpose(PodCollection, types.uuid,
                         types.uuid, int, wtypes.text, wtypes.text)
    def detail(self, pod_uuid=None, marker=None, limit=None,
               sort_key='id', sort_dir='asc'):
        """Retrieve a list of pods with detail.

        :param pod_uuid: UUID of a pod, to get only pods for that pod.
        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        # NOTE(lucasagomes): /detail should only work agaist collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "pods":
            raise exception.HTTPNotFound

        expand = True
        resource_url = '/'.join(['pods', 'detail'])
        return self._get_pods_collection(marker, limit,
                                         sort_key, sort_dir, expand,
                                         resource_url)

    @wsme_pecan.wsexpose(Pod, types.uuid)
    def get_one(self, pod_uuid):
        """Retrieve information about the given pod.

        :param pod_uuid: UUID of a pod.
        """
        if self.from_pods:
            raise exception.OperationNotPermitted

        rpc_pod = objects.Pod.get_by_uuid(pecan.request.context, pod_uuid)
        return Pod.convert_with_links(rpc_pod)

    @wsme_pecan.wsexpose(Pod, body=Pod, status_code=201)
    def post(self, pod):
        """Create a new pod.

        :param pod: a pod within the request body.
        """
        if self.from_pods:
            raise exception.OperationNotPermitted

        pod.parse_manifest()
        pod_obj = objects.Pod(pecan.request.context,
                              **pod.as_dict())
        new_pod = pecan.request.rpcapi.pod_create(pod_obj)
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('pods', new_pod.uuid)
        return Pod.convert_with_links(new_pod)

    @wsme.validate(types.uuid, [PodPatchType])
    @wsme_pecan.wsexpose(Pod, types.uuid, body=[PodPatchType])
    def patch(self, pod_uuid, patch):
        """Update an existing pod.

        :param pod_uuid: UUID of a pod.
        :param patch: a json PATCH document to apply to this pod.
        """
        if self.from_pods:
            raise exception.OperationNotPermitted

        rpc_pod = objects.Pod.get_by_uuid(pecan.request.context, pod_uuid)
        try:
            pod_dict = rpc_pod.as_dict()
            pod = Pod(**api_utils.apply_jsonpatch(pod_dict, patch))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        # Update only the fields that have changed
        for field in objects.Pod.fields:
            # ignore manifest_url as it was used for create pod
            if field == 'manifest_url':
                continue
            if field == 'manifest':
                continue
            try:
                patch_val = getattr(pod, field)
            except AttributeError:
                # Ignore fields that aren't exposed in the API
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if rpc_pod[field] != patch_val:
                rpc_pod[field] = patch_val

        rpc_pod.save()
        return Pod.convert_with_links(rpc_pod)

    @wsme_pecan.wsexpose(None, types.uuid, status_code=204)
    def delete(self, pod_uuid):
        """Delete a pod.

        :param pod_uuid: UUID of a pod.
        """
        if self.from_pods:
            raise exception.OperationNotPermitted

        pecan.request.rpcapi.pod_delete(pod_uuid)
