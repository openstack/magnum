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

import glanceclient.exc
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
from magnum.common import clients
from magnum.common import exception
from magnum import objects


class BayModelPatchType(types.JsonPatchType):
    pass


class BayModel(base.APIBase):
    """API representation of a baymodel.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a baymodel.
    """

    _coe = None

    def _get_coe(self):
        return self._coe

    def _set_coe(self, value):
        if value and self._coe != value:
            self._coe = value
        elif value == wtypes.Unset:
            self._coe = wtypes.Unset

    uuid = types.uuid
    """Unique UUID for this baymodel"""

    name = wtypes.text
    """The name of the bay model"""

    coe = wsme.wsproperty(wtypes.text, _get_coe, _set_coe, mandatory=True)
    """The Container Orchestration Engine for this bay model"""

    image_id = wtypes.text
    """The image name or UUID to use as a base image for this baymodel"""

    flavor_id = wtypes.text
    """The flavor of this bay model"""

    master_flavor_id = wtypes.text
    """The flavor of the master node for this bay model"""

    dns_nameserver = wtypes.text
    """The DNS nameserver address"""

    keypair_id = wtypes.text
    """The name or id of the nova ssh keypair"""

    external_network_id = wtypes.text
    """The external network to attach the Bay"""

    fixed_network = wtypes.text
    """The fixed network name to attach the Bay"""

    apiserver_port = wtypes.IntegerType()
    """The API server port for k8s"""

    docker_volume_size = wtypes.IntegerType()
    """The size in GB of the docker volume"""

    ssh_authorized_key = wtypes.text
    """The SSH Authorized Key"""

    cluster_distro = wtypes.text
    """The Cluster distro for the bay, ex - coreos, fedora-atomic."""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated baymodel links"""

    def __init__(self, **kwargs):
        self.fields = []
        for field in objects.BayModel.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @staticmethod
    def _convert_with_links(baymodel, url, expand=True):
        if not expand:
            baymodel.unset_fields_except(['uuid', 'name', 'image_id',
                                          'apiserver_port', 'coe'])

        baymodel.links = [link.Link.make_link('self', url,
                                          'baymodels', baymodel.uuid),
                      link.Link.make_link('bookmark', url,
                                          'baymodels', baymodel.uuid,
                                          bookmark=True)
                     ]
        return baymodel

    @classmethod
    def convert_with_links(cls, rpc_baymodel, expand=True):
        baymodel = BayModel(**rpc_baymodel.as_dict())
        return cls._convert_with_links(baymodel, pecan.request.host_url,
                                       expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(uuid='27e3153e-d5bf-4b7e-b517-fb518e17f34c',
                    name='example',
                    image_id='Fedora-k8s',
                    flavor_id='m1.small',
                    master_flavor_id='m1.small',
                    dns_nameserver='8.8.1.1',
                    keypair_id='keypair1',
                    external_network_id='ffc44e4a-2319-4062-bce0-9ae1c38b05ba',
                    fixed_network='private',
                    apiserver_port=8080,
                    docker_volume_size=25,
                    cluster_distro='fedora-atomic',
                    ssh_authorized_key='ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAB',
                    coe='kubernetes',
                    created_at=datetime.datetime.utcnow(),
                    updated_at=datetime.datetime.utcnow())
        return cls._convert_with_links(sample, 'http://localhost:9511', expand)


class BayModelCollection(collection.Collection):
    """API representation of a collection of baymodels."""

    baymodels = [BayModel]
    """A list containing baymodels objects"""

    def __init__(self, **kwargs):
        self._type = 'baymodels'

    @staticmethod
    def convert_with_links(rpc_baymodels, limit, url=None, expand=False,
                           **kwargs):
        collection = BayModelCollection()
        collection.baymodels = [BayModel.convert_with_links(p, expand)
                            for p in rpc_baymodels]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.baymodels = [BayModel.sample(expand=False)]
        return sample


class BayModelsController(rest.RestController):
    """REST controller for BayModels."""

    from_baymodels = False
    """A flag to indicate if the requests to this controller are coming
    from the top-level resource BayModels."""

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_baymodels_collection(self, marker, limit,
                              sort_key, sort_dir, expand=False,
                              resource_url=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.BayModel.get_by_uuid(pecan.request.context,
                                                  marker)

        baymodels = objects.BayModel.list(pecan.request.context, limit,
                                marker_obj, sort_key=sort_key,
                                sort_dir=sort_dir)

        return BayModelCollection.convert_with_links(baymodels, limit,
                                                url=resource_url,
                                                expand=expand,
                                                sort_key=sort_key,
                                                sort_dir=sort_dir)

    def _get_image_data(self, context, image_id):
        """Retrieves os_distro and other metadata from the Glance image.

        :param image_id: image_id of baymodel.
        """
        try:
            cli = clients.OpenStackClients(context)
            image_data = cli.glance().images.get(image_id)
            return image_data
        except glanceclient.exc.NotFound:
            raise exception.ImageNotFound(image_id=image_id)
        except glanceclient.exc.HTTPForbidden:
            raise exception.ImageNotAuthorized(image_id=image_id)

    @wsme_pecan.wsexpose(BayModelCollection, types.uuid,
                         types.uuid, int, wtypes.text, wtypes.text)
    def get_all(self, baymodel_uuid=None, marker=None, limit=None,
                sort_key='id', sort_dir='asc'):
        """Retrieve a list of baymodels.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        return self._get_baymodels_collection(marker, limit, sort_key,
                                         sort_dir)

    @wsme_pecan.wsexpose(BayModelCollection, types.uuid,
                         types.uuid, int, wtypes.text, wtypes.text)
    def detail(self, baymodel_uuid=None, marker=None, limit=None,
                sort_key='id', sort_dir='asc'):
        """Retrieve a list of baymodels with detail.

        :param baymodel_uuid: UUID of a baymodel, to get only baymodels for
               that baymodel.
        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        # NOTE(lucasagomes): /detail should only work agaist collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "baymodels":
            raise exception.HTTPNotFound

        expand = True
        resource_url = '/'.join(['baymodels', 'detail'])
        return self._get_baymodels_collection(marker, limit,
                                         sort_key, sort_dir, expand,
                                         resource_url)

    @wsme_pecan.wsexpose(BayModel, types.uuid_or_name)
    def get_one(self, baymodel_ident):
        """Retrieve information about the given baymodel.

        :param baymodel_ident: UUID or logical name of a baymodel.
        """
        if self.from_baymodels:
            raise exception.OperationNotPermitted

        rpc_baymodel = api_utils.get_rpc_resource('BayModel', baymodel_ident)
        return BayModel.convert_with_links(rpc_baymodel)

    @wsme_pecan.wsexpose(BayModel, body=BayModel, status_code=201)
    def post(self, baymodel):
        """Create a new baymodel.

        :param baymodel: a baymodel within the request body.
        """
        if self.from_baymodels:
            raise exception.OperationNotPermitted

        baymodel_dict = baymodel.as_dict()
        context = pecan.request.context
        auth_token = context.auth_token_info['token']
        baymodel_dict['project_id'] = auth_token['project']['id']
        baymodel_dict['user_id'] = auth_token['user']['id']
        image_data = self._get_image_data(context, baymodel_dict['image_id'])
        if image_data['os_distro']:
            baymodel_dict['cluster_distro'] = image_data['os_distro']
        else:
            raise exception.OSDistroFieldNotFound(baymodel_dict['image_id'])
        new_baymodel = objects.BayModel(context, **baymodel_dict)
        new_baymodel.create()
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('baymodels',
                                  new_baymodel.uuid)
        return BayModel.convert_with_links(new_baymodel)

    @wsme.validate(types.uuid, [BayModelPatchType])
    @wsme_pecan.wsexpose(BayModel, types.uuid, body=[BayModelPatchType])
    def patch(self, baymodel_uuid, patch):
        """Update an existing baymodel.

        :param baymodel_uuid: UUID of a baymodel.
        :param patch: a json PATCH document to apply to this baymodel.
        """
        if self.from_baymodels:
            raise exception.OperationNotPermitted

        rpc_baymodel = objects.BayModel.get_by_uuid(pecan.request.context,
            baymodel_uuid)
        try:
            baymodel_dict = rpc_baymodel.as_dict()
            baymodel = BayModel(**api_utils.apply_jsonpatch(baymodel_dict,
                patch))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        # Update only the fields that have changed
        for field in objects.BayModel.fields:
            try:
                patch_val = getattr(baymodel, field)
            except AttributeError:
                # Ignore fields that aren't exposed in the API
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if rpc_baymodel[field] != patch_val:
                rpc_baymodel[field] = patch_val

        rpc_baymodel.save()
        return BayModel.convert_with_links(rpc_baymodel)

    @wsme_pecan.wsexpose(None, types.uuid_or_name, status_code=204)
    def delete(self, baymodel_ident):
        """Delete a baymodel.

        :param baymodel_uuid: UUID or logical name of a baymodel.
        """
        if self.from_baymodels:
            raise exception.OperationNotPermitted

        rpc_baymodel = api_utils.get_rpc_resource('BayModel', baymodel_ident)
        rpc_baymodel.destroy()
