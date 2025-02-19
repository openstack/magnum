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
from oslo_utils import strutils
from oslo_utils import timeutils
import pecan
import warnings
import wsme
from wsme import types as wtypes

from magnum.api import attr_validator
from magnum.api.controllers import base
from magnum.api.controllers import link
from magnum.api.controllers.v1 import cluster_actions
from magnum.api.controllers.v1 import collection
from magnum.api.controllers.v1 import nodegroup
from magnum.api.controllers.v1 import types
from magnum.api import expose
from magnum.api import utils as api_utils
from magnum.api import validation
from magnum.common import exception
from magnum.common import name_generator
from magnum.common import policy
import magnum.conf
from magnum.i18n import _
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

    uuid = types.uuid
    """Unique UUID for this cluster"""

    name = wtypes.StringType(min_length=1, max_length=242,
                             pattern='^[a-zA-Z][a-zA-Z0-9_.-]*$')
    """Name of this cluster, max length is limited to 242 because of heat
     stack requires max length limit to 255, and Magnum amend a uuid length"""

    cluster_template_id = wsme.wsattr(wtypes.text, mandatory=True)
    """The cluster_template UUID"""

    keypair = wsme.wsattr(wtypes.StringType(min_length=1, max_length=255),
                          default=None)
    """The name of the nova ssh keypair"""

    node_count = wsme.wsattr(wtypes.IntegerType(minimum=0), default=1)
    """The node count for this cluster. Default to 1 if not set"""

    master_count = wsme.wsattr(wtypes.IntegerType(minimum=1), default=1)
    """The number of master nodes for this cluster. Default to 1 if not set"""

    docker_volume_size = wtypes.IntegerType(minimum=1)
    """The size in GB of the docker volume"""

    labels = wtypes.DictType(
        wtypes.text,
        types.MultiType(wtypes.text, int, bool, float)
    )
    """One or more key/value pairs"""

    master_flavor_id = wtypes.StringType(min_length=1, max_length=255)
    """The flavor of the master node for this Cluster"""

    flavor_id = wtypes.StringType(min_length=1, max_length=255)
    """The flavor of this Cluster"""

    create_timeout = wsme.wsattr(wtypes.IntegerType(minimum=0), default=60)
    """Timeout for creating the cluster in minutes. Default to 60 if not set"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated cluster links"""

    stack_id = wsme.wsattr(wtypes.text, readonly=True)
    """Stack id of the heat stack"""

    status = wtypes.Enum(wtypes.text, *fields.ClusterStatus.ALL)
    """Status of the cluster from the heat stack"""

    status_reason = wtypes.text
    """Status reason of the cluster from the heat stack"""

    health_status = wtypes.Enum(wtypes.text, *fields.ClusterHealthStatus.ALL)
    """Health status of the cluster from the native COE API"""

    health_status_reason = wtypes.DictType(wtypes.text, wtypes.text)
    """Health status reason of the cluster from the native COE API"""

    discovery_url = wtypes.text
    """Url used for cluster node discovery"""

    api_address = wsme.wsattr(wtypes.text, readonly=True)
    """Api address of cluster master node"""

    coe_version = wsme.wsattr(wtypes.text, readonly=True)
    """Version of the COE software currently running in this cluster.
    Example: kubernetes version."""

    container_version = wsme.wsattr(wtypes.text, readonly=True)
    """Version of the container software. Example: docker version."""

    project_id = wsme.wsattr(wtypes.text, readonly=True)
    """Project id of the cluster belongs to"""

    user_id = wsme.wsattr(wtypes.text, readonly=True)
    """User id of the cluster belongs to"""

    node_addresses = wsme.wsattr([wtypes.text], readonly=True)
    """IP addresses of cluster slave nodes"""

    master_addresses = wsme.wsattr([wtypes.text], readonly=True)
    """IP addresses of cluster master nodes"""

    faults = wsme.wsattr(wtypes.DictType(wtypes.text, wtypes.text))
    """Fault info collected from the heat resources of this cluster"""

    fixed_network = wtypes.StringType(min_length=1, max_length=255)
    """The fixed network name to attach to the Cluster"""

    fixed_subnet = wtypes.StringType(min_length=1, max_length=255)
    """The fixed subnet name to attach to the Cluster"""

    floating_ip_enabled = wsme.wsattr(types.boolean)
    """Indicates whether created clusters should have a floating ip or not."""

    merge_labels = wsme.wsattr(types.boolean, default=False)
    """Indicates whether the labels will be merged with the CT labels."""

    labels_overridden = wtypes.DictType(
            wtypes.text, types.MultiType(
                wtypes.text, int, bool, float))
    """Contains labels that have a value different than the parent labels."""

    labels_added = wtypes.DictType(
        wtypes.text,
        types.MultiType(wtypes.text, int, bool, float)
    )
    """Contains labels that do not exist in the parent."""

    labels_skipped = wtypes.DictType(
        wtypes.text,
        types.MultiType(wtypes.text, int, bool, float)
    )
    """Contains labels that exist in the parent but were not inherited."""

    master_lb_enabled = wsme.wsattr(types.boolean)
    """Indicates whether created clusters should have a load balancer for master
       nodes or not.
       """  # noqa: E501

    def __init__(self, **kwargs):
        super(Cluster, self).__init__()
        self.fields = []
        for field in objects.Cluster.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))
        nodegroup_fields = ['node_count', 'master_count',
                            'node_addresses', 'master_addresses']
        for field in nodegroup_fields:
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @staticmethod
    def _convert_with_links(cluster, url, expand=True, parent_labels=None):
        if not expand:
            cluster.unset_fields_except(['uuid', 'name', 'cluster_template_id',
                                         'keypair', 'docker_volume_size',
                                         'labels', 'node_count', 'status',
                                         'master_flavor_id', 'flavor_id',
                                         'create_timeout', 'master_count',
                                         'stack_id', 'health_status'])
        else:
            overridden, added, skipped = api_utils.get_labels_diff(
                parent_labels, cluster.labels)
            cluster.labels_overridden = overridden
            cluster.labels_added = added
            cluster.labels_skipped = skipped

        cluster.links = [link.Link.make_link('self', url,
                                             'clusters', cluster.uuid),
                         link.Link.make_link('bookmark', url,
                                             'clusters', cluster.uuid,
                                             bookmark=True)]
        return cluster

    @classmethod
    def convert_with_links(cls, rpc_cluster, expand=True):
        cluster = Cluster(**rpc_cluster.as_dict())
        parent_labels = rpc_cluster.cluster_template.labels
        return cls._convert_with_links(cluster, pecan.request.host_url, expand,
                                       parent_labels)

    @classmethod
    def sample(cls, expand=True):
        temp_id = '4a96ac4b-2447-43f1-8ca6-9fd6f36d146d'
        sample = cls(uuid='27e3153e-d5bf-4b7e-b517-fb518e17f34c',
                     name='example',
                     cluster_template_id=temp_id,
                     keypair=None,
                     node_count=2,
                     master_count=1,
                     docker_volume_size=1,
                     labels={},
                     master_flavor_id='m1.small',
                     flavor_id='m1.small',
                     create_timeout=15,
                     stack_id='49dc23f5-ffc9-40c3-9d34-7be7f9e34d63',
                     status=fields.ClusterStatus.CREATE_COMPLETE,
                     status_reason="CREATE completed successfully",
                     health_status=fields.ClusterHealthStatus.HEALTHY,
                     health_status_reason={"api": "ok",
                                           "node-0.Ready": 'True'},
                     api_address='172.24.4.3',
                     node_addresses=['172.24.4.4', '172.24.4.5'],
                     created_at=timeutils.utcnow(),
                     updated_at=timeutils.utcnow(),
                     coe_version=None,
                     container_version=None,
                     fixed_network=None,
                     fixed_subnet=None,
                     floating_ip_enabled=True,
                     master_lb_enabled=True)
        return cls._convert_with_links(sample, 'http://localhost:9511', expand)


class ClusterPatchType(types.JsonPatchType):
    _api_base = Cluster

    @staticmethod
    def internal_attrs():
        internal_attrs = ['/api_address', '/node_addresses',
                          '/master_addresses', '/stack_id',
                          '/ca_cert_ref', '/magnum_cert_ref',
                          '/trust_id', '/trustee_user_name',
                          '/trustee_password', '/trustee_user_id',
                          '/etcd_ca_cert_ref', '/front_proxy_ca_cert_ref']
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

    _in_tree_cinder_volume_driver_deprecation_note = (
        "The in-tree Cinder volume driver is deprecated and will be removed "
        "in X cycle in favour of out-of-tree Cinder CSI driver which requires "
        "the label cinder_csi_enabled set to True (default behaviour from "
        "V cycle) when volume_driver is cinder.")

    actions = cluster_actions.ActionsController()

    def _generate_name_for_cluster(self, context):
        """Generate a random name like: zeta-22-cluster."""
        name_gen = name_generator.NameGenerator()
        name = name_gen.generate()
        return name + '-cluster'

    def _get_clusters_collection(self, marker, limit,
                                 sort_key, sort_dir, expand=False,
                                 resource_url=None):

        context = pecan.request.context
        if context.is_admin:
            if expand:
                policy.enforce(context, "cluster:detail_all_projects",
                               action="cluster:detail_all_projects")
            else:
                policy.enforce(context, "cluster:get_all_all_projects",
                               action="cluster:get_all_all_projects")
            # TODO(flwang): Instead of asking an extra 'all_project's
            # parameter, currently the design is allowing admin user to list
            # all clusters from all projects. But the all_tenants is one of
            # the condition to do project filter in DB API. And it's also used
            # by periodic tasks. So the could be removed in the future and
            # a new parameter 'project_id' would be added so that admin user
            # can list clusters for a particular project.
            context.all_tenants = True

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

    nodegroups = nodegroup.NodeGroupController()

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
        # Gather fault info from the cluster nodegroups.
        return {
            ng.name: ng.status_reason for ng in cluster.nodegroups
            if ng.status.endswith('FAILED')
        }

    @expose.expose(Cluster, types.uuid_or_name)
    def get_one(self, cluster_ident):
        """Retrieve information about the given Cluster.

        :param cluster_ident: UUID or logical name of the Cluster.
        """
        context = pecan.request.context
        if context.is_admin:
            policy.enforce(context, "cluster:get_one_all_projects",
                           action="cluster:get_one_all_projects")
            # TODO(flwang): Instead of asking an extra 'all_project's
            # parameter, currently the design is allowing admin user to list
            # all clusters from all projects. But the all_tenants is one of
            # the condition to do project filter in DB API. And it's also used
            # by periodic tasks. So this could be removed in the future and
            # a new parameter 'project_id' would be added so that admin user
            # can list clusters for a particular project.
            context.all_tenants = True

        cluster = api_utils.get_resource('Cluster', cluster_ident)
        policy.enforce(context, 'cluster:get', cluster.as_dict(),
                       action='cluster:get')

        api_cluster = Cluster.convert_with_links(cluster)

        if api_cluster.status in fields.ClusterStatus.STATUS_FAILED:
            api_cluster.faults = self._collect_fault_info(context, cluster)

        return api_cluster

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

    @base.Controller.api_version("1.1", "1.9")
    @expose.expose(ClusterID, body=Cluster, status_code=202)
    @validation.ct_not_found_to_bad_request()
    @validation.enforce_cluster_type_supported()
    @validation.enforce_cluster_volume_storage_size()
    @validation.enforce_cluster_master_size_supported()
    def post(self, cluster):
        if cluster.node_count == 0:
            raise exception.ZeroNodeCountNotSupported()
        return self._post(cluster)

    @base.Controller.api_version("1.10")  # noqa
    @expose.expose(ClusterID, body=Cluster, status_code=202)
    @validation.enforce_cluster_type_supported()
    @validation.enforce_cluster_volume_storage_size()
    @validation.enforce_cluster_master_size_supported()
    def post(self, cluster):  # noqa
        return self._post(cluster)

    def _post(self, cluster):
        """Create a new cluster.

        :param cluster: a cluster within the request body.
        """
        context = pecan.request.context
        policy.enforce(context, 'cluster:create',
                       action='cluster:create')

        self._check_cluster_quota_limit(context)

        temp_id = cluster.cluster_template_id
        cluster_template = objects.ClusterTemplate.get(context, temp_id)
        # We are not sure if we got a uuid or name here. So just set
        # explicitly the uuid of the cluster template in the cluster.
        cluster.cluster_template_id = cluster_template.uuid
        # If keypair not present, use cluster_template value
        if cluster.keypair is None:
            cluster.keypair = cluster_template.keypair_id

        # If labels is not present, use cluster_template value
        if cluster.labels == wtypes.Unset or not cluster.labels:
            cluster.labels = cluster_template.labels
        else:
            # If labels are provided check if the user wishes to merge
            # them with the values from the cluster template.
            if cluster.merge_labels:
                labels = cluster_template.labels
                labels.update(cluster.labels)
                cluster.labels = labels

        cinder_csi_enabled = cluster.labels.get('cinder_csi_enabled', True)
        if (cluster_template.volume_driver == 'cinder' and
                not strutils.bool_from_string(cinder_csi_enabled)):
            warnings.warn(self._in_tree_cinder_volume_driver_deprecation_note,
                          DeprecationWarning)
            LOG.warning(self._in_tree_cinder_volume_driver_deprecation_note)

        # If floating_ip_enabled is not present, use cluster_template value
        if cluster.floating_ip_enabled == wtypes.Unset:
            cluster.floating_ip_enabled = cluster_template.floating_ip_enabled

        # If master_lb_enabled is not present, use cluster_template value
        if cluster.master_lb_enabled == wtypes.Unset:
            cluster.master_lb_enabled = cluster_template.master_lb_enabled

        attributes = ["docker_volume_size", "master_flavor_id", "flavor_id",
                      "fixed_network", "fixed_subnet"]
        for attr in attributes:
            if (getattr(cluster, attr) == wtypes.Unset or
                    not getattr(cluster, attr)):
                setattr(cluster, attr, getattr(cluster_template, attr))

        cluster_dict = cluster.as_dict()

        attr_validator.validate_os_resources(context,
                                             cluster_template.as_dict(),
                                             cluster_dict)
        attr_validator.validate_master_count(context,
                                             cluster_dict)

        cluster_dict['project_id'] = context.project_id
        cluster_dict['user_id'] = context.user_id
        # NOTE(yuywz): We will generate a random human-readable name for
        # cluster if the name is not specified by user.
        name = cluster_dict.get('name') or \
            self._generate_name_for_cluster(context)
        cluster_dict['name'] = name
        cluster_dict['coe_version'] = None
        cluster_dict['container_version'] = None

        node_count = cluster_dict.pop('node_count')
        master_count = cluster_dict.pop('master_count')
        new_cluster = objects.Cluster(context, **cluster_dict)
        new_cluster.uuid = uuid.uuid4()
        pecan.request.rpcapi.cluster_create_async(new_cluster,
                                                  master_count, node_count,
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
        (cluster, node_count,
         health_status,
         health_status_reason) = self._patch(cluster_ident, patch)
        if node_count == 0:
            raise exception.ZeroNodeCountNotSupported()
        pecan.request.rpcapi.cluster_update_async(cluster, node_count,
                                                  health_status,
                                                  health_status_reason)
        return ClusterID(cluster.uuid)

    @base.Controller.api_version("1.3", "1.9")  # noqa
    @wsme.validate(types.uuid, bool, [ClusterPatchType])
    @expose.expose(ClusterID, types.uuid_or_name, types.boolean,
                   body=[ClusterPatchType], status_code=202)
    def patch(self, cluster_ident, rollback=False, patch=None):  # noqa
        """Update an existing Cluster.

        :param cluster_ident: UUID or logical name of a cluster.
        :param rollback: whether to rollback cluster on update failure.
        :param patch: a json PATCH document to apply to this cluster.
        """
        (cluster, node_count,
         health_status,
         health_status_reason) = self._patch(cluster_ident, patch)
        if node_count == 0:
            raise exception.ZeroNodeCountNotSupported()
        pecan.request.rpcapi.cluster_update_async(cluster, node_count,
                                                  health_status,
                                                  health_status_reason,
                                                  rollback)
        return ClusterID(cluster.uuid)

    @base.Controller.api_version("1.10")  # noqa
    @wsme.validate(types.uuid, bool, [ClusterPatchType])
    @expose.expose(ClusterID, types.uuid_or_name, types.boolean,
                   body=[ClusterPatchType], status_code=202)
    def patch(self, cluster_ident, rollback=False, patch=None):  # noqa
        """Update an existing Cluster.

        :param cluster_ident: UUID or logical name of a cluster.
        :param rollback: whether to rollback cluster on update failure.
        :param patch: a json PATCH document to apply to this cluster.
        """
        (cluster, node_count,
         health_status,
         health_status_reason) = self._patch(cluster_ident, patch)
        pecan.request.rpcapi.cluster_update_async(cluster, node_count,
                                                  health_status,
                                                  health_status_reason,
                                                  rollback)
        return ClusterID(cluster.uuid)

    def _patch(self, cluster_ident, patch):
        context = pecan.request.context
        if context.is_admin:
            policy.enforce(context, "cluster:update_all_projects",
                           action="cluster:update_all_projects")
            context.all_tenants = True

        cluster = api_utils.get_resource('Cluster', cluster_ident)
        policy.enforce(context, 'cluster:update', cluster.as_dict(),
                       action='cluster:update')
        policy.enforce(context, "cluster:update_health_status",
                       action="cluster:update_health_status")
        try:
            cluster_dict = cluster.as_dict()
            new_cluster = Cluster(**api_utils.apply_jsonpatch(cluster_dict,
                                                              patch))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        # NOTE(ttsiouts): magnum.objects.Cluster.node_count will be a
        # property so we won't be able to store it in the object. So
        # instead of object_what_changed compare the new and the old
        # clusters.
        delta = set()
        for field in new_cluster.fields:
            if getattr(cluster, field) != getattr(new_cluster, field):
                delta.add(field)

        validation.validate_cluster_properties(delta)

        # NOTE(brtknr): cluster.node_count is the size of the whole cluster
        # which includes non-default nodegroups. However cluster_update expects
        # node_count to be the size of the default_ng_worker therefore return
        # this value unless the patch object says otherwise.
        node_count = cluster.default_ng_worker.node_count
        for p in patch:
            if p['path'] == '/node_count':
                node_count = p.get('value') or new_cluster.node_count

        return (cluster, node_count,
                new_cluster.health_status, new_cluster.health_status_reason)

    @expose.expose(None, types.uuid_or_name, status_code=204)
    def delete(self, cluster_ident):
        """Delete a cluster.

        :param cluster_ident: UUID of cluster or logical name of the cluster.
        """
        context = pecan.request.context
        if context.is_admin:
            policy.enforce(context, 'cluster:delete_all_projects',
                           action='cluster:delete_all_projects')
            context.all_tenants = True

        cluster = api_utils.get_resource('Cluster', cluster_ident)
        policy.enforce(context, 'cluster:delete', cluster.as_dict(),
                       action='cluster:delete')

        pecan.request.rpcapi.cluster_delete_async(cluster.uuid)
