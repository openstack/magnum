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

from oslo_log import log as logging
from oslo_utils import timeutils
import pecan
import warnings
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
from magnum.common import name_generator
from magnum.common import policy
from magnum import objects
from magnum.objects import fields

LOG = logging.getLogger(__name__)


class ClusterTemplate(base.APIBase):
    """API representation of a ClusterTemplate.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of
    a ClusterTemplate.
    """

    uuid = types.uuid
    """Unique UUID for this ClusterTemplate"""

    name = wtypes.StringType(min_length=1, max_length=255)
    """The name of the ClusterTemplate"""

    coe = wtypes.Enum(wtypes.text, *fields.ClusterType.ALL, mandatory=True)
    """The Container Orchestration Engine for this clustertemplate"""

    image_id = wsme.wsattr(wtypes.StringType(min_length=1, max_length=255),
                           mandatory=True)
    """The image name or UUID to use as an image for this ClusterTemplate"""

    flavor_id = wtypes.StringType(min_length=1, max_length=255)
    """The flavor of this ClusterTemplate"""

    master_flavor_id = wtypes.StringType(min_length=1, max_length=255)
    """The flavor of the master node for this ClusterTemplate"""

    dns_nameserver = types.dns_list
    """The DNS nameserver address"""

    keypair_id = wsme.wsattr(wtypes.StringType(min_length=1, max_length=255),
                             default=None)
    """The name of the nova ssh keypair"""

    external_network_id = wtypes.StringType(min_length=1, max_length=255)
    """The external network to attach to the Cluster"""

    fixed_network = wtypes.StringType(min_length=1, max_length=255)
    """The fixed network name to attach to the Cluster"""

    fixed_subnet = wtypes.StringType(min_length=1, max_length=255)
    """The fixed subnet name to attach to the Cluster"""

    network_driver = wtypes.StringType(min_length=1, max_length=255)
    """The name of the driver used for instantiating container networks"""

    apiserver_port = wtypes.IntegerType(minimum=1024, maximum=65535)
    """The API server port for k8s"""

    docker_volume_size = wtypes.IntegerType(minimum=1)
    """The size in GB of the docker volume"""

    cluster_distro = wtypes.StringType(min_length=1, max_length=255)
    """The Cluster distro for the Cluster, e.g. coreos, fedora-coreos, etc."""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated ClusterTemplate links"""

    http_proxy = wtypes.StringType(min_length=1, max_length=255)
    """Address of a proxy that will receive all HTTP requests and relay them.
       The format is a URL including a port number.
       """

    https_proxy = wtypes.StringType(min_length=1, max_length=255)
    """Address of a proxy that will receive all HTTPS requests and relay them.
       The format is a URL including a port number.
       """

    no_proxy = wtypes.StringType(min_length=1, max_length=255)
    """A comma separated list of IPs for which proxies should not be
       used in the cluster
       """

    volume_driver = wtypes.StringType(min_length=1, max_length=255)
    """The name of the driver used for instantiating container volumes"""

    registry_enabled = wsme.wsattr(types.boolean, default=False)
    """Indicates whether the docker registry is enabled"""

    labels = wtypes.DictType(
        wtypes.text,
        types.MultiType(wtypes.text, int, bool, float)
    )
    """One or more key/value pairs"""

    tls_disabled = wsme.wsattr(types.boolean, default=False)
    """Indicates whether the TLS should be disabled"""

    public = wsme.wsattr(types.boolean, default=False)
    """Indicates whether the ClusterTemplate is public or not."""

    server_type = wsme.wsattr(wtypes.Enum(wtypes.text, *fields.ServerType.ALL),
                              default='vm')
    """Server type for this ClusterTemplate """

    insecure_registry = wtypes.StringType(min_length=1, max_length=255)
    """Insecure registry URL when creating a ClusterTemplate """

    docker_storage_driver = wtypes.StringType(min_length=1, max_length=255)
    """Docker storage driver"""

    master_lb_enabled = wsme.wsattr(types.boolean, default=False)
    """Indicates whether created clusters should have a load balancer for master
       nodes or not.
       """

    floating_ip_enabled = wsme.wsattr(types.boolean, default=True)
    """Indicates whether created clusters should have a floating ip or not."""

    project_id = wsme.wsattr(wtypes.text, readonly=True)
    """Project id of the cluster belongs to"""

    user_id = wsme.wsattr(wtypes.text, readonly=True)
    """User id of the cluster belongs to"""

    hidden = wsme.wsattr(types.boolean, default=False)
    """Indicates whether the ClusterTemplate is hidden or not."""

    tags = wtypes.StringType(min_length=0, max_length=255)
    """A comma separated list of tags."""

    driver = wtypes.StringType(min_length=0, max_length=255)
    """Driver name set explicitly"""

    def __init__(self, **kwargs):
        self.fields = []
        for field in objects.ClusterTemplate.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @staticmethod
    def _convert_with_links(cluster_template, url):
        cluster_template.links = [link.Link.make_link('self', url,
                                                      'clustertemplates',
                                                      cluster_template.uuid),
                                  link.Link.make_link('bookmark', url,
                                                      'clustertemplates',
                                                      cluster_template.uuid,
                                                      bookmark=True)]
        return cluster_template

    @classmethod
    def convert_with_links(cls, rpc_cluster_template):
        cluster_template = ClusterTemplate(**rpc_cluster_template.as_dict())
        return cls._convert_with_links(cluster_template,
                                       pecan.request.host_url)

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
            fixed_subnet='private-subnet',
            network_driver='libnetwork',
            volume_driver='cinder',
            apiserver_port=8080,
            docker_volume_size=25,
            docker_storage_driver='devicemapper',
            cluster_distro='fedora-coreos',
            coe=fields.ClusterType.KUBERNETES,
            http_proxy='http://proxy.com:123',
            https_proxy='https://proxy.com:123',
            no_proxy='192.168.0.1,192.168.0.2,192.168.0.3',
            labels={'key1': 'val1', 'key2': 'val2'},
            server_type='vm',
            insecure_registry='10.238.100.100:5000',
            created_at=timeutils.utcnow(),
            updated_at=timeutils.utcnow(),
            public=False,
            master_lb_enabled=False,
            floating_ip_enabled=True,
            hidden=False)
        return cls._convert_with_links(sample, 'http://localhost:9511')


class ClusterTemplatePatchType(types.JsonPatchType):
    _api_base = ClusterTemplate
    _extra_non_removable_attrs = {'/network_driver', '/external_network_id',
                                  '/tls_disabled', '/public', '/server_type',
                                  '/coe', '/registry_enabled',
                                  '/cluster_distro', '/hidden'}


class ClusterTemplateCollection(collection.Collection):
    """API representation of a collection of ClusterTemplates."""

    clustertemplates = [ClusterTemplate]
    """A list containing ClusterTemplates objects"""

    def __init__(self, **kwargs):
        self._type = 'clustertemplates'

    @staticmethod
    def convert_with_links(rpc_cluster_templates, limit, url=None, **kwargs):
        collection = ClusterTemplateCollection()
        collection.clustertemplates = [ClusterTemplate.convert_with_links(p)
                                       for p in rpc_cluster_templates]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.clustertemplates = [ClusterTemplate.sample()]
        return sample


class ClusterTemplatesController(base.Controller):
    """REST controller for ClusterTemplates."""

    _custom_actions = {
        'detail': ['GET'],
    }

    _devicemapper_overlay_deprecation_note = (
        "The devicemapper and overlay storage "
        "drivers are deprecated in favor of overlay2 in docker, and will be "
        "removed in a future release from docker. Users of the devicemapper "
        "and overlay storage drivers are recommended to migrate to a "
        "different storage driver, such as overlay2. overlay2 will be set "
        "as the default storage driver from Victoria cycle in Magnum.")

    def _generate_name_for_cluster_template(self, context):
        """Generate a random name like: zeta-22-model."""

        name_gen = name_generator.NameGenerator()
        name = name_gen.generate()
        return name + '-template'

    def _get_cluster_templates_collection(self, marker, limit,
                                          sort_key, sort_dir,
                                          resource_url=None):

        context = pecan.request.context
        if context.is_admin:
            if resource_url == '/'.join(['clustertemplates', 'detail']):
                policy.enforce(context, "clustertemplate:detail_all_projects",
                               action="clustertemplate:detail_all_projects")
            else:
                policy.enforce(context, "clustertemplate:get_all_all_projects",
                               action="clustertemplate:get_all_all_projects")
            # TODO(flwang): Instead of asking an extra 'all_project's
            # parameter, currently the design is allowing admin user to list
            # all clusters from all projects. But the all_tenants is one of
            # the condition to do project filter in DB API. And it's also used
            # by periodic tasks. So this could be removed in the future and
            # a new parameter 'project_id' would be added so that admin user
            # can list clusters for a particular project.
            context.all_tenants = True

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.ClusterTemplate.get_by_uuid(
                pecan.request.context, marker)

        cluster_templates = objects.ClusterTemplate.list(
            pecan.request.context, limit, marker_obj, sort_key=sort_key,
            sort_dir=sort_dir)

        return ClusterTemplateCollection.convert_with_links(cluster_templates,
                                                            limit,
                                                            url=resource_url,
                                                            sort_key=sort_key,
                                                            sort_dir=sort_dir)

    @expose.expose(ClusterTemplateCollection, types.uuid, int, wtypes.text,
                   wtypes.text)
    def get_all(self, marker=None, limit=None, sort_key='id',
                sort_dir='asc'):
        """Retrieve a list of ClusterTemplates.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        context = pecan.request.context
        policy.enforce(context, 'clustertemplate:get_all',
                       action='clustertemplate:get_all')
        return self._get_cluster_templates_collection(marker, limit, sort_key,
                                                      sort_dir)

    @expose.expose(ClusterTemplateCollection, types.uuid, int, wtypes.text,
                   wtypes.text)
    def detail(self, marker=None, limit=None, sort_key='id',
               sort_dir='asc'):
        """Retrieve a list of ClusterTemplates with detail.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        context = pecan.request.context
        policy.enforce(context, 'clustertemplate:detail',
                       action='clustertemplate:detail')

        # NOTE(lucasagomes): /detail should only work against collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "clustertemplates":
            raise exception.HTTPNotFound

        resource_url = '/'.join(['clustertemplates', 'detail'])
        return self._get_cluster_templates_collection(marker, limit,
                                                      sort_key, sort_dir,
                                                      resource_url)

    @expose.expose(ClusterTemplate, types.uuid_or_name)
    def get_one(self, cluster_template_ident):
        """Retrieve information about the given ClusterTemplate.

        :param cluster_template_ident: UUID or logical name of a
        ClusterTemplate.
        """
        context = pecan.request.context

        if context.is_admin:
            policy.enforce(context, "clustertemplate:get_one_all_projects",
                           action="clustertemplate:get_one_all_projects")
            # TODO(flwang): Instead of asking an extra 'all_project's
            # parameter, currently the design is allowing admin user to list
            # all clusters from all projects. But the all_tenants is one of
            # the condition to do project filter in DB API. And it's also used
            # by periodic tasks. So this could be removed in the future and
            # a new parameter 'project_id' would be added so that admin user
            # can list clusters for a particular project.
            context.all_tenants = True

        cluster_template = api_utils.get_resource('ClusterTemplate',
                                                  cluster_template_ident)

        if not cluster_template.public:
            policy.enforce(context, 'clustertemplate:get',
                           cluster_template.as_dict(),
                           action='clustertemplate:get')

        return ClusterTemplate.convert_with_links(cluster_template)

    @expose.expose(ClusterTemplate, body=ClusterTemplate, status_code=201)
    @validation.enforce_server_type()
    @validation.enforce_network_driver_types_create()
    @validation.enforce_volume_driver_types_create()
    @validation.enforce_volume_storage_size_create()
    @validation.enforce_driver_supported()
    def post(self, cluster_template):
        """Create a new ClusterTemplate.

        :param cluster_template: a ClusterTemplate within the request body.
        """
        context = pecan.request.context
        policy.enforce(context, 'clustertemplate:create',
                       action='clustertemplate:create')
        cluster_template_dict = cluster_template.as_dict()
        cli = clients.OpenStackClients(context)
        attr_validator.validate_os_resources(context, cluster_template_dict)
        image_data = attr_validator.validate_image(cli,
                                                   cluster_template_dict[
                                                       'image_id'])
        cluster_template_dict['cluster_distro'] = image_data['os_distro']
        cluster_template_dict['project_id'] = context.project_id
        cluster_template_dict['user_id'] = context.user_id
        # NOTE(jake): read driver from image for now, update client to provide
        # this as param in the future
        cluster_template_dict['driver'] = image_data.get('magnum_driver')
        # check permissions for making cluster_template public or hidden
        if cluster_template_dict['public'] or cluster_template_dict['hidden']:
            if not policy.enforce(context, "clustertemplate:publish", None,
                                  do_raise=False):
                raise exception.ClusterTemplatePublishDenied()

        if (cluster_template.docker_storage_driver in ('devicemapper',
                                                       'overlay')):
            warnings.warn(self._devicemapper_overlay_deprecation_note,
                          DeprecationWarning)
            LOG.warning(self._devicemapper_overlay_deprecation_note)

        if (cluster_template_dict['coe'] == 'kubernetes' and
                cluster_template_dict['cluster_distro'] == 'coreos'):
            warnings.warn(self._coreos_deprecation_note,
                          DeprecationWarning)
            LOG.warning(self._coreos_deprecation_note)

        # NOTE(yuywz): We will generate a random human-readable name for
        # cluster_template if the name is not specified by user.
        arg_name = cluster_template_dict.get('name')
        name = arg_name or self._generate_name_for_cluster_template(context)
        cluster_template_dict['name'] = name

        new_cluster_template = objects.ClusterTemplate(context,
                                                       **cluster_template_dict)
        new_cluster_template.create()
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('clustertemplates',
                                                 new_cluster_template.uuid)
        return ClusterTemplate.convert_with_links(new_cluster_template)

    @wsme.validate(types.uuid_or_name, [ClusterTemplatePatchType])  # noqa
    @expose.expose(ClusterTemplate, types.uuid_or_name,
                   body=[ClusterTemplatePatchType])
    @validation.enforce_network_driver_types_update()
    @validation.enforce_volume_driver_types_update()
    def patch(self, cluster_template_ident, patch):   # noqa
        """Update an existing ClusterTemplate.

        :param cluster_template_ident: UUID or logic name of a
        ClusterTemplate.
        :param patch: a json PATCH document to apply to this
        ClusterTemplate.
        """
        context = pecan.request.context
        if context.is_admin:
            policy.enforce(context, 'clustertemplate:update_all_projects',
                           action='clustertemplate:update_all_projects')
            context.all_tenants = True
        cluster_template = api_utils.get_resource('ClusterTemplate',
                                                  cluster_template_ident)
        policy.enforce(context, 'clustertemplate:update',
                       cluster_template.as_dict(),
                       action='clustertemplate:update')
        try:
            cluster_template_dict = cluster_template.as_dict()
            new_cluster_template = ClusterTemplate(**api_utils.apply_jsonpatch(
                cluster_template_dict,
                patch))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        new_cluster_template_dict = new_cluster_template.as_dict()
        attr_validator.validate_os_resources(context,
                                             new_cluster_template_dict)
        # check permissions when updating ClusterTemplate public or hidden flag
        if (cluster_template.public != new_cluster_template.public or
                cluster_template.hidden != new_cluster_template.hidden):
            if not policy.enforce(context, "clustertemplate:publish", None,
                                  do_raise=False):
                raise exception.ClusterTemplatePublishDenied()

        # Update only the fields that have changed
        for field in objects.ClusterTemplate.fields:
            try:
                patch_val = getattr(new_cluster_template, field)
            except AttributeError:
                # Ignore fields that aren't exposed in the API
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if cluster_template[field] != patch_val:
                cluster_template[field] = patch_val

        if (cluster_template.docker_storage_driver in ('devicemapper',
                                                       'overlay')):
            warnings.warn(self._devicemapper_overlay_deprecation_note,
                          DeprecationWarning)
            LOG.warning(self._devicemapper_overlay_deprecation_note)

        cluster_template.save()
        return ClusterTemplate.convert_with_links(cluster_template)

    @expose.expose(None, types.uuid_or_name, status_code=204)
    def delete(self, cluster_template_ident):
        """Delete a ClusterTemplate.

        :param cluster_template_ident: UUID or logical name of a
         ClusterTemplate.
        """
        context = pecan.request.context
        if context.is_admin:
            policy.enforce(context, 'clustertemplate:delete_all_projects',
                           action='clustertemplate:delete_all_projects')
            context.all_tenants = True

        cluster_template = api_utils.get_resource('ClusterTemplate',
                                                  cluster_template_ident)
        policy.enforce(context, 'clustertemplate:delete',
                       cluster_template.as_dict(),
                       action='clustertemplate:delete')
        cluster_template.destroy()
