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

import uuid

from oslo_log import log as logging
from oslo_utils import timeutils
import pecan
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
import magnum.conf
from magnum.i18n import _
from magnum.i18n import _LW
from magnum import objects
from magnum.objects import fields

LOG = logging.getLogger(__name__)
CONF = magnum.conf.CONF


class ClusterID(wtypes.Base):
    """API representation of a cluster ID

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a cluster
    ID.
    """

    uuid = types.uuid
    """Unique UUID for this cluster"""

    def __init__(self, uuid):
        self.uuid = uuid


class Cluster(base.APIBase):
    """API representation of a cluster.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a Cluster.
    """

    _cluster_template_id = None

    def _get_cluster_template_id(self):
        return self._cluster_template_id

    def _set_cluster_template_id(self, value):
        if value and self._cluster_template_id != value:
            try:
                cluster_template = api_utils.get_resource('ClusterTemplate',
                                                          value)
                self._cluster_template_id = cluster_template.uuid
            except exception.ClusterTemplateNotFound as e:
                # Change error code because 404 (NotFound) is inappropriate
                # response for a POST request to create a Cluster
                e.code = 400  # BadRequest
                raise
        elif value == wtypes.Unset:
            self._cluster_template_id = wtypes.Unset

    uuid = types.uuid
    """Unique UUID for this cluster"""

    name = wtypes.StringType(min_length=1, max_length=242,
                             pattern='^[a-zA-Z][a-zA-Z0-9_.-]*$')
    """Name of this cluster, max length is limited to 242 because of heat
     stack requires max length limit to 255, and Magnum amend a uuid length"""

    cluster_template_id = wsme.wsproperty(wtypes.text,
                                          _get_cluster_template_id,
                                          _set_cluster_template_id,
                                          mandatory=True)
    """The cluster_template UUID"""

    keypair = wsme.wsattr(wtypes.StringType(min_length=1, max_length=255),
                          default=None)
    """The name of the nova ssh keypair"""

    node_count = wsme.wsattr(wtypes.IntegerType(minimum=1), default=1)
    """The node count for this cluster. Default to 1 if not set"""

    master_count = wsme.wsattr(wtypes.IntegerType(minimum=1), default=1)
    """The number of master nodes for this cluster. Default to 1 if not set"""

    create_timeout = wsme.wsattr(wtypes.IntegerType(minimum=0), default=60)
    """Timeout for creating the cluster in minutes. Default to 60 if not set"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated cluster links"""

    stack_id = wsme.wsattr(wtypes.text, readonly=True)
    """Stack id of the heat stack"""

    status = wtypes.Enum(str, *fields.ClusterStatus.ALL)
    """Status of the cluster from the heat stack"""

    status_reason = wtypes.text
    """Status reason of the cluster from the heat stack"""

    discovery_url = wtypes.text
    """Url used for cluster node discovery"""

    api_address = wsme.wsattr(wtypes.text, readonly=True)
    """Api address of cluster master node"""

    coe_version = wsme.wsattr(wtypes.text, readonly=True)
    """Version of the COE software currently running in this cluster.
    Example: swarm version or kubernetes version."""

    container_version = wsme.wsattr(wtypes.text, readonly=True)
    """Version of the container software. Example: docker version."""

    node_addresses = wsme.wsattr([wtypes.text], readonly=True)
    """IP addresses of cluster slave nodes"""

    master_addresses = wsme.wsattr([wtypes.text], readonly=True)
    """IP addresses of cluster master nodes"""

    faults = wsme.wsattr(wtypes.DictType(str, wtypes.text))
    """Fault info collected from the heat resources of this cluster"""

    def __init__(self, **kwargs):
        super(Cluster, self).__init__()
        self.fields = []
        for field in objects.Cluster.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @staticmethod
    def _convert_with_links(cluster, url, expand=True):
        if not expand:
            cluster.unset_fields_except(['uuid', 'name', 'cluster_template_id',
                                         'keypair', 'node_count', 'status',
                                         'create_timeout', 'master_count',
                                         'stack_id'])

        cluster.links = [link.Link.make_link('self', url,
                                             'clusters', cluster.uuid),
                         link.Link.make_link('bookmark', url,
                                             'clusters', cluster.uuid,
                                             bookmark=True)]
        return cluster

    @classmethod
    def convert_with_links(cls, rpc_cluster, expand=True):
        cluster = Cluster(**rpc_cluster.as_dict())
        return cls._convert_with_links(cluster, pecan.request.host_url, expand)

    @classmethod
    def sample(cls, expand=True):
        temp_id = '4a96ac4b-2447-43f1-8ca6-9fd6f36d146d'
        sample = cls(uuid='27e3153e-d5bf-4b7e-b517-fb518e17f34c',
                     name='example',
                     cluster_template_id=temp_id,
                     keypair=None,
                     node_count=2,
                     master_count=1,
                     create_timeout=15,
                     stack_id='49dc23f5-ffc9-40c3-9d34-7be7f9e34d63',
                     status=fields.ClusterStatus.CREATE_COMPLETE,
                     status_reason="CREATE completed successfully",
                     api_address='172.24.4.3',
                     node_addresses=['172.24.4.4', '172.24.4.5'],
                     created_at=timeutils.utcnow(),
                     updated_at=timeutils.utcnow(),
                     coe_version=None,
                     container_version=None)
        return cls._convert_with_links(sample, 'http://localhost:9511', expand)


class ClusterPatchType(types.JsonPatchType):
    _api_base = Cluster

    @staticmethod
    def internal_attrs():
        internal_attrs = ['/api_address', '/node_addresses',
                          '/master_addresses', '/stack_id',
                          '/ca_cert_ref', '/magnum_cert_ref',
                          '/trust_id', '/trustee_user_name',
                          '/trustee_password', '/trustee_user_id']
        return types.JsonPatchType.internal_attrs() + internal_attrs


class ClusterCollection(collection.Collection):
    """API representation of a collection of clusters."""

    clusters = [Cluster]
    """A list containing cluster objects"""

    def __init__(self, **kwargs):
        self._type = 'clusters'

    @staticmethod
    def convert_with_links(rpc_clusters, limit, url=None, expand=False,
                           **kwargs):
        collection = ClusterCollection()
        collection.clusters = [Cluster.convert_with_links(p, expand)
                               for p in rpc_clusters]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.clusters = [Cluster.sample(expand=False)]
        return sample


class ClustersController(base.Controller):
    """REST controller for Clusters."""

    def __init__(self):
        super(ClustersController, self).__init__()

    _custom_actions = {
        'detail': ['GET'],
    }

    def _generate_name_for_cluster(self, context):
        """Generate a random name like: zeta-22-cluster."""
        name_gen = name_generator.NameGenerator()
        name = name_gen.generate()
        return name + '-cluster'

    def _get_clusters_collection(self, marker, limit,
                                 sort_key, sort_dir, expand=False,
                                 resource_url=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Cluster.get_by_uuid(pecan.request.context,
                                                     marker)

        clusters = objects.Cluster.list(pecan.request.context, limit,
                                        marker_obj, sort_key=sort_key,
                                        sort_dir=sort_dir)

        return ClusterCollection.convert_with_links(clusters, limit,
                                                    url=resource_url,
                                                    expand=expand,
                                                    sort_key=sort_key,
                                                    sort_dir=sort_dir)

    @expose.expose(ClusterCollection, types.uuid, int, wtypes.text,
                   wtypes.text)
    def get_all(self, marker=None, limit=None, sort_key='id',
                sort_dir='asc'):
        """Retrieve a list of clusters.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        context = pecan.request.context
        policy.enforce(context, 'cluster:get_all',
                       action='cluster:get_all')
        return self._get_clusters_collection(marker, limit, sort_key,
                                             sort_dir)

    @expose.expose(ClusterCollection, types.uuid, int, wtypes.text,
                   wtypes.text)
    def detail(self, marker=None, limit=None, sort_key='id',
               sort_dir='asc'):
        """Retrieve a list of clusters with detail.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        context = pecan.request.context
        policy.enforce(context, 'cluster:detail',
                       action='cluster:detail')

        # NOTE(lucasagomes): /detail should only work against collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "clusters":
            raise exception.HTTPNotFound

        expand = True
        resource_url = '/'.join(['clusters', 'detail'])
        return self._get_clusters_collection(marker, limit,
                                             sort_key, sort_dir, expand,
                                             resource_url)

    def _collect_fault_info(self, context, cluster):
        """Collect fault info from heat resources of given cluster

        and store them into cluster.faults.
        """
        osc = clients.OpenStackClients(context)
        filters = {'status': 'FAILED'}
        try:
            failed_resources = osc.heat().resources.list(
                cluster.stack_id, nested_depth=2, filters=filters)
        except Exception as e:
            failed_resources = []
            LOG.warning(_LW("Failed to retrieve failed resources for "
                            "cluster %(cluster)s from Heat stack "
                            "%(stack)s due to error: %(e)s"),
                        {'cluster': cluster.uuid,
                         'stack': cluster.stack_id, 'e': e},
                        exc_info=True)

        return {res.resource_name: res.resource_status_reason
                for res in failed_resources}

    @expose.expose(Cluster, types.uuid_or_name)
    def get_one(self, cluster_ident):
        """Retrieve information about the given Cluster.

        :param cluster_ident: UUID or logical name of the Cluster.
        """
        context = pecan.request.context
        cluster = api_utils.get_resource('Cluster', cluster_ident)
        policy.enforce(context, 'cluster:get', cluster,
                       action='cluster:get')

        cluster = Cluster.convert_with_links(cluster)

        if cluster.status in fields.ClusterStatus.STATUS_FAILED:
            cluster.faults = self._collect_fault_info(context, cluster)

        return cluster

    def _check_cluster_quota_limit(self, context):
        try:
            # Check if there is any explicit quota limit set in Quotas table
            quota = objects.Quota.get_quota_by_project_id_resource(
                context,
                context.project_id,
                'Cluster')
            cluster_limit = quota.hard_limit
        except exception.QuotaNotFound:
            # If explicit quota was not set for the project, use default limit
            cluster_limit = CONF.quotas.max_clusters_per_project

        if objects.Cluster.get_count_all(context) >= cluster_limit:
            msg = _("You have reached the maximum clusters per project, "
                    "%d. You may delete a cluster to make room for a new "
                    "one.") % cluster_limit
            raise exception.ResourceLimitExceeded(msg=msg)

    @expose.expose(ClusterID, body=Cluster, status_code=202)
    @validation.enforce_cluster_type_supported()
    def post(self, cluster):
        """Create a new cluster.

        :param cluster: a cluster within the request body.
        """
        context = pecan.request.context
        policy.enforce(context, 'cluster:create',
                       action='cluster:create')

        self._check_cluster_quota_limit(context)

        temp_id = cluster.cluster_template_id
        cluster_template = objects.ClusterTemplate.get_by_uuid(context,
                                                               temp_id)
        # If keypair not present, use cluster_template value
        if cluster.keypair is None:
            cluster.keypair = cluster_template.keypair_id

        cluster_dict = cluster.as_dict()

        attr_validator.validate_os_resources(context,
                                             cluster_template.as_dict(),
                                             cluster_dict)
        attr_validator.validate_master_count(cluster_dict,
                                             cluster_template.as_dict())

        cluster_dict['project_id'] = context.project_id
        cluster_dict['user_id'] = context.user_id
        # NOTE(yuywz): We will generate a random human-readable name for
        # cluster if the name is not specified by user.
        name = cluster_dict.get('name') or \
            self._generate_name_for_cluster(context)
        cluster_dict['name'] = name
        cluster_dict['coe_version'] = None
        cluster_dict['container_version'] = None

        new_cluster = objects.Cluster(context, **cluster_dict)
        new_cluster.uuid = uuid.uuid4()
        pecan.request.rpcapi.cluster_create_async(new_cluster,
                                                  cluster.create_timeout)

        return ClusterID(new_cluster.uuid)

    @base.Controller.api_version("1.1", "1.2")
    @wsme.validate(types.uuid, [ClusterPatchType])
    @expose.expose(ClusterID, types.uuid_or_name, body=[ClusterPatchType],
                   status_code=202)
    def patch(self, cluster_ident, patch):
        """Update an existing Cluster.

        :param cluster_ident: UUID or logical name of a cluster.
        :param patch: a json PATCH document to apply to this cluster.
        """
        cluster = self._patch(cluster_ident, patch)
        pecan.request.rpcapi.cluster_update_async(cluster)
        return ClusterID(cluster.uuid)

    @base.Controller.api_version("1.3")  # noqa
    @wsme.validate(types.uuid, bool, [ClusterPatchType])
    @expose.expose(ClusterID, types.uuid_or_name, types.boolean,
                   body=[ClusterPatchType], status_code=202)
    def patch(self, cluster_ident, rollback=False, patch=None):
        """Update an existing Cluster.

        :param cluster_ident: UUID or logical name of a cluster.
        :param rollback: whether to rollback cluster on update failure.
        :param patch: a json PATCH document to apply to this cluster.
        """
        cluster = self._patch(cluster_ident, patch)
        pecan.request.rpcapi.cluster_update_async(cluster, rollback)
        return ClusterID(cluster.uuid)

    def _patch(self, cluster_ident, patch):
        context = pecan.request.context
        cluster = api_utils.get_resource('Cluster', cluster_ident)
        policy.enforce(context, 'cluster:update', cluster,
                       action='cluster:update')
        try:
            cluster_dict = cluster.as_dict()
            new_cluster = Cluster(**api_utils.apply_jsonpatch(cluster_dict,
                                                              patch))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        # Update only the fields that have changed
        for field in objects.Cluster.fields:
            try:
                patch_val = getattr(new_cluster, field)
            except AttributeError:
                # Ignore fields that aren't exposed in the API
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if cluster[field] != patch_val:
                cluster[field] = patch_val

        delta = cluster.obj_what_changed()

        validation.validate_cluster_properties(delta)
        return cluster

    @expose.expose(None, types.uuid_or_name, status_code=204)
    def delete(self, cluster_ident):
        """Delete a cluster.

        :param cluster_ident: UUID of cluster or logical name of the cluster.
        """
        context = pecan.request.context
        cluster = api_utils.get_resource('Cluster', cluster_ident)
        policy.enforce(context, 'cluster:delete', cluster,
                       action='cluster:delete')

        pecan.request.rpcapi.cluster_delete_async(cluster.uuid)
