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

from oslo_utils import timeutils
import pecan
from pecan import rest
import wsme
from wsme import types as wtypes

from magnum.api import attr_validator
from magnum.api.controllers import base
from magnum.api.controllers import link
from magnum.api.controllers.v1 import collection
from magnum.api.controllers.v1 import types
from magnum.api import expose
from magnum.api import utils as api_utils
from magnum.api import validation
from magnum.common import clients
from magnum.common import exception
from magnum.common import policy
from magnum import objects
from magnum.objects import fields


class BayModelPatchType(types.JsonPatchType):

    @staticmethod
    def mandatory_attrs():
        return ['/image_id', '/keypair_id', '/external_network_id', '/coe',
                '/tls_disabled', '/public', '/registry_enabled',
                '/server_type', '/cluster_distro', '/network_driver']


class BayModel(base.APIBase):
    """API representation of a baymodel.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a baymodel.
    """

    uuid = types.uuid
    """Unique UUID for this baymodel"""

    name = wtypes.StringType(min_length=1, max_length=255)
    """The name of the bay model"""

    coe = wtypes.Enum(str, *fields.BayType.ALL, mondatory=True)
    """The Container Orchestration Engine for this bay model"""

    image_id = wsme.wsattr(wtypes.StringType(min_length=1, max_length=255),
                           mandatory=True)
    """The image name or UUID to use as a base image for this baymodel"""

    flavor_id = wtypes.StringType(min_length=1, max_length=255)
    """The flavor of this bay model"""

    master_flavor_id = wtypes.StringType(min_length=1, max_length=255)
    """The flavor of the master node for this bay model"""

    dns_nameserver = wtypes.IPv4AddressType()
    """The DNS nameserver address"""

    keypair_id = wsme.wsattr(wtypes.StringType(min_length=1, max_length=255),
                             mandatory=True)
    """The name or id of the nova ssh keypair"""

    external_network_id = wtypes.StringType(min_length=1, max_length=255)
    """The external network to attach the Bay"""

    fixed_network = wtypes.StringType(min_length=1, max_length=255)
    """The fixed network name to attach the Bay"""

    network_driver = wtypes.StringType(min_length=1, max_length=255)
    """The name of the driver used for instantiating container networks"""

    apiserver_port = wtypes.IntegerType(minimum=1024, maximum=65535)
    """The API server port for k8s"""

    docker_volume_size = wtypes.IntegerType(minimum=1)
    """The size in GB of the docker volume"""

    cluster_distro = wtypes.StringType(min_length=1, max_length=255)
    """The Cluster distro for the bay, ex - coreos, fedora-atomic."""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated baymodel links"""

    http_proxy = wtypes.StringType(min_length=1, max_length=255)
    """Address of a proxy that will receive all HTTP requests and relay them.
       The format is a URL including a port number.
       """

    https_proxy = wtypes.StringType(min_length=1, max_length=255)
    """Address of a proxy that will receive all HTTPS requests and relay them.
       The format is a URL including a port number.
       """

    no_proxy = wtypes.StringType(min_length=1, max_length=255)
    """A comma separated list of ips for which proxies should not
       used in the bay
       """

    volume_driver = wtypes.StringType(min_length=1, max_length=255)
    """The name of the driver used for instantiating container volume driver"""

    registry_enabled = wsme.wsattr(types.boolean, default=False)
    """Indicates whether the docker registry is enabled"""

    labels = wtypes.DictType(str, str)
    """One or more key/value pairs"""

    tls_disabled = wsme.wsattr(types.boolean, default=False)
    """Indicates whether the TLS should be disabled"""

    public = wsme.wsattr(types.boolean, default=False)
    """Indicates whether the baymodel is public or not."""

    server_type = wsme.wsattr(wtypes.StringType(min_length=1,
                                                max_length=255),
                              default='vm')
    """Server type for this bay model """

    insecure_registry = wtypes.StringType(min_length=1, max_length=255)
    """insecure registry url when create baymodel """

    docker_storage_driver = wtypes.Enum(str, *fields.DockerStorageDriver.ALL)
    """Docker storage driver"""

    def __init__(self, **kwargs):
        self.fields = []
        for field in objects.BayModel.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @staticmethod
    def _convert_with_links(baymodel, url):
        baymodel.links = [link.Link.make_link('self', url,
                                              'baymodels', baymodel.uuid),
                          link.Link.make_link('bookmark', url,
                                              'baymodels', baymodel.uuid,
                                              bookmark=True)]
        return baymodel

    @classmethod
    def convert_with_links(cls, rpc_baymodel):
        baymodel = BayModel(**rpc_baymodel.as_dict())
        return cls._convert_with_links(baymodel, pecan.request.host_url)

    @classmethod
    def sample(cls):
        sample = cls(
            uuid='27e3153e-d5bf-4b7e-b517-fb518e17f34c',
            name='example',
            image_id='Fedora-k8s',
            flavor_id='m1.small',
            master_flavor_id='m1.small',
            dns_nameserver='8.8.1.1',
            keypair_id='keypair1',
            external_network_id='ffc44e4a-2319-4062-bce0-9ae1c38b05ba',
            fixed_network='private',
            network_driver='libnetwork',
            volume_driver='cinder',
            apiserver_port=8080,
            docker_volume_size=25,
            docker_storage_driver='devicemapper',
            cluster_distro='fedora-atomic',
            coe=fields.BayType.KUBERNETES,
            http_proxy='http://proxy.com:123',
            https_proxy='https://proxy.com:123',
            no_proxy='192.168.0.1,192.168.0.2,192.168.0.3',
            labels={'key1': 'val1', 'key2': 'val2'},
            server_type='vm',
            insecure_registry='10.238.100.100:5000',
            created_at=timeutils.utcnow(),
            updated_at=timeutils.utcnow(),
            public=False),
        return cls._convert_with_links(sample, 'http://localhost:9511')


class BayModelCollection(collection.Collection):
    """API representation of a collection of baymodels."""

    baymodels = [BayModel]
    """A list containing baymodels objects"""

    def __init__(self, **kwargs):
        self._type = 'baymodels'

    @staticmethod
    def convert_with_links(rpc_baymodels, limit, url=None, **kwargs):
        collection = BayModelCollection()
        collection.baymodels = [BayModel.convert_with_links(p)
                                for p in rpc_baymodels]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.baymodels = [BayModel.sample()]
        return sample


class BayModelsController(rest.RestController):
    """REST controller for BayModels."""

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_baymodels_collection(self, marker, limit,
                                  sort_key, sort_dir, resource_url=None):

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
                                                     sort_key=sort_key,
                                                     sort_dir=sort_dir)

    @expose.expose(BayModelCollection, types.uuid, int, wtypes.text,
                   wtypes.text)
    def get_all(self, marker=None, limit=None, sort_key='id',
                sort_dir='asc'):
        """Retrieve a list of baymodels.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        context = pecan.request.context
        policy.enforce(context, 'baymodel:get_all',
                       action='baymodel:get_all')
        return self._get_baymodels_collection(marker, limit, sort_key,
                                              sort_dir)

    @expose.expose(BayModelCollection, types.uuid, int, wtypes.text,
                   wtypes.text)
    def detail(self, marker=None, limit=None, sort_key='id',
               sort_dir='asc'):
        """Retrieve a list of baymodels with detail.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        context = pecan.request.context
        policy.enforce(context, 'baymodel:detail',
                       action='baymodel:detail')

        # NOTE(lucasagomes): /detail should only work against collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "baymodels":
            raise exception.HTTPNotFound

        resource_url = '/'.join(['baymodels', 'detail'])
        return self._get_baymodels_collection(marker, limit,
                                              sort_key, sort_dir, resource_url)

    @expose.expose(BayModel, types.uuid_or_name)
    def get_one(self, baymodel_ident):
        """Retrieve information about the given baymodel.

        :param baymodel_ident: UUID or logical name of a baymodel.
        """
        context = pecan.request.context
        baymodel = api_utils.get_resource('BayModel', baymodel_ident)
        if not baymodel.public:
            policy.enforce(context, 'baymodel:get', baymodel,
                           action='baymodel:get')

        return BayModel.convert_with_links(baymodel)

    @expose.expose(BayModel, body=BayModel, status_code=201)
    @validation.enforce_network_driver_types_create()
    @validation.enforce_volume_driver_types_create()
    def post(self, baymodel):
        """Create a new baymodel.

        :param baymodel: a baymodel within the request body.
        """
        context = pecan.request.context
        policy.enforce(context, 'baymodel:create',
                       action='baymodel:create')
        baymodel_dict = baymodel.as_dict()
        context = pecan.request.context
        cli = clients.OpenStackClients(context)
        attr_validator.validate_os_resources(context, baymodel_dict)
        image_data = attr_validator.validate_image(cli,
                                                   baymodel_dict['image_id'])
        baymodel_dict['cluster_distro'] = image_data['os_distro']
        baymodel_dict['project_id'] = context.project_id
        baymodel_dict['user_id'] = context.user_id
        # check permissions for making baymodel public
        if baymodel_dict['public']:
            if not policy.enforce(context, "baymodel:publish", None,
                                  do_raise=False):
                raise exception.BaymodelPublishDenied()

        new_baymodel = objects.BayModel(context, **baymodel_dict)
        new_baymodel.create()
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('baymodels',
                                                 new_baymodel.uuid)
        return BayModel.convert_with_links(new_baymodel)

    @wsme.validate(types.uuid_or_name, [BayModelPatchType])
    @expose.expose(BayModel, types.uuid_or_name, body=[BayModelPatchType])
    @validation.enforce_network_driver_types_update()
    @validation.enforce_volume_driver_types_update()
    def patch(self, baymodel_ident, patch):
        """Update an existing baymodel.

        :param baymodel_ident: UUID or logic name of a baymodel.
        :param patch: a json PATCH document to apply to this baymodel.
        """
        context = pecan.request.context
        baymodel = api_utils.get_resource('BayModel', baymodel_ident)
        policy.enforce(context, 'baymodel:update', baymodel,
                       action='baymodel:update')
        try:
            baymodel_dict = baymodel.as_dict()
            new_baymodel = BayModel(**api_utils.apply_jsonpatch(
                baymodel_dict,
                patch))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        new_baymodel_dict = new_baymodel.as_dict()
        attr_validator.validate_os_resources(context, new_baymodel_dict)
        # check permissions when updating baymodel public flag
        if baymodel.public != new_baymodel.public:
            if not policy.enforce(context, "baymodel:publish", None,
                                  do_raise=False):
                raise exception.BaymodelPublishDenied()

        # Update only the fields that have changed
        for field in objects.BayModel.fields:
            try:
                patch_val = getattr(new_baymodel, field)
            except AttributeError:
                # Ignore fields that aren't exposed in the API
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if baymodel[field] != patch_val:
                baymodel[field] = patch_val

        baymodel.save()
        return BayModel.convert_with_links(baymodel)

    @expose.expose(None, types.uuid_or_name, status_code=204)
    def delete(self, baymodel_ident):
        """Delete a baymodel.

        :param baymodel_ident: UUID or logical name of a baymodel.
        """
        context = pecan.request.context
        baymodel = api_utils.get_resource('BayModel', baymodel_ident)
        policy.enforce(context, 'baymodel:delete', baymodel,
                       action='baymodel:delete')
        baymodel.destroy()
