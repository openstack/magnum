# Copyright (c) 2018 European Organization for Nuclear Research.
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

import pecan
import six
import uuid
import wsme
from wsme import types as wtypes

from magnum.api.controllers import base
from magnum.api.controllers import link
from magnum.api.controllers.v1 import collection
from magnum.api.controllers.v1 import types
from magnum.api import expose
from magnum.api import utils as api_utils
from magnum.common import exception
from magnum.common import policy
from magnum import objects
from magnum.objects import fields


def _validate_node_count(ng):
    if ng.max_node_count:
        if ng.max_node_count < ng.min_node_count:
            expl = ("min_node_count (%s) should be less or equal to "
                    "max_node_count (%s)" % (ng.min_node_count,
                                             ng.max_node_count))
            raise exception.NodeGroupInvalidInput(attr='max_node_count',
                                                  nodegroup=ng.name,
                                                  expl=expl)
        if ng.node_count > ng.max_node_count:
            expl = ("node_count (%s) should be less or equal to "
                    "max_node_count (%s)" % (ng.node_count,
                                             ng.max_node_count))
            raise exception.NodeGroupInvalidInput(attr='max_node_count',
                                                  nodegroup=ng.name,
                                                  expl=expl)
    if ng.min_node_count > ng.node_count:
        expl = ('min_node_count (%s) should be less or equal to '
                'node_count (%s)' % (ng.min_node_count, ng.node_count))
        raise exception.NodeGroupInvalidInput(attr='min_node_count',
                                              nodegroup=ng.name,
                                              expl=expl)


class NodeGroup(base.APIBase):
    """API representation of a Node group.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of NodeGroup.
    """
    id = wsme.wsattr(wtypes.IntegerType(minimum=1))
    """unique id"""

    uuid = types.uuid
    """Unique UUID for this nodegroup"""

    name = wsme.wsattr(wtypes.StringType(min_length=1, max_length=255),
                       default=None)
    """Name of this nodegroup"""

    cluster_id = types.uuid
    """Unique UUID for the cluster where the nodegroup belongs to"""

    project_id = wsme.wsattr(wtypes.text, readonly=True)
    """Project UUID for this nodegroup"""

    docker_volume_size = wtypes.IntegerType(minimum=1)
    """The size in GB of the docker volume"""

    labels = wtypes.DictType(wtypes.text, types.MultiType(wtypes.text,
                                                          six.integer_types,
                                                          bool,
                                                          float))
    """One or more key/value pairs"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated nodegroup links"""

    flavor_id = wtypes.StringType(min_length=1, max_length=255)
    """The flavor of this nodegroup"""

    image_id = wtypes.StringType(min_length=1, max_length=255)
    """The image used for this nodegroup"""

    node_addresses = wsme.wsattr([wtypes.text], readonly=True)
    """IP addresses of nodegroup nodes"""

    node_count = wsme.wsattr(wtypes.IntegerType(minimum=0), default=1)
    """The node count for this nodegroup. Default to 1 if not set"""

    role = wsme.wsattr(wtypes.StringType(min_length=1, max_length=255),
                       default='worker')
    """The role of the nodes included in this nodegroup"""

    min_node_count = wsme.wsattr(wtypes.IntegerType(minimum=0), default=0)
    """The minimum allowed nodes for this nodegroup. Default to 0 if not set"""

    max_node_count = wsme.wsattr(wtypes.IntegerType(minimum=0), default=None)
    """The maximum allowed nodes for this nodegroup."""

    is_default = types.BooleanType()
    """Specifies is a nodegroup was created by default or not"""

    stack_id = wsme.wsattr(wtypes.text, readonly=True)
    """Stack id of the heat stack"""

    status = wtypes.Enum(wtypes.text, *fields.ClusterStatus.ALL)
    """Status of the nodegroup from the heat stack"""

    status_reason = wtypes.text
    """Status reason of the nodegroup from the heat stack"""

    version = wtypes.text
    """Version of the nodegroup"""

    merge_labels = wsme.wsattr(types.boolean, default=False)
    """Indicates whether the labels will be merged with the cluster labels."""

    labels_overridden = wtypes.DictType(
            wtypes.text, types.MultiType(
                wtypes.text, six.integer_types, bool, float))
    """Contains labels that have a value different than the parent labels."""

    labels_added = wtypes.DictType(
            wtypes.text, types.MultiType(
                wtypes.text, six.integer_types, bool, float))
    """Contains labels that do not exist in the parent."""

    labels_skipped = wtypes.DictType(
            wtypes.text, types.MultiType(
                wtypes.text, six.integer_types, bool, float))
    """Contains labels that exist in the parent but were not inherited."""

    def __init__(self, **kwargs):
        super(NodeGroup, self).__init__()
        self.fields = []
        for field in objects.NodeGroup.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @classmethod
    def convert(cls, nodegroup, expand=True):
        url = pecan.request.host_url
        cluster_path = 'clusters/%s' % nodegroup.cluster_id
        nodegroup_path = 'nodegroups/%s' % nodegroup.uuid

        ng = NodeGroup(**nodegroup.as_dict())
        if not expand:
            ng.unset_fields_except(["uuid", "name", "flavor_id", "node_count",
                                    "role", "is_default", "image_id", "status",
                                    "stack_id"])
        else:
            ng.links = [link.Link.make_link('self', url, cluster_path,
                                            nodegroup_path),
                        link.Link.make_link('bookmark', url,
                                            cluster_path, nodegroup_path,
                                            bookmark=True)]
            cluster = api_utils.get_resource('Cluster', ng.cluster_id)

            overridden, added, skipped = api_utils.get_labels_diff(
                    cluster.labels, ng.labels)
            ng.labels_overridden = overridden
            ng.labels_added = added
            ng.labels_skipped = skipped

        return ng


class NodeGroupPatchType(types.JsonPatchType):
    _api_base = NodeGroup

    @staticmethod
    def internal_attrs():
        # Allow updating only min/max_node_count
        internal_attrs = ["/name", "/cluster_id", "/project_id",
                          "/docker_volume_size", "/labels", "/flavor_id",
                          "/image_id", "/node_addresses", "/node_count",
                          "/role", "/is_default", "/stack_id", "/status",
                          "/status_reason", "/version"]
        return types.JsonPatchType.internal_attrs() + internal_attrs


class NodeGroupCollection(collection.Collection):
    """API representation of a collection of Node Groups."""

    nodegroups = [NodeGroup]
    """A list containing quota objects"""

    def __init__(self, **kwargs):
        self._type = 'nodegroups'

    @staticmethod
    def convert(nodegroups, cluster_id, limit, expand=True, **kwargs):
        collection = NodeGroupCollection()
        collection.nodegroups = [NodeGroup.convert(ng, expand)
                                 for ng in nodegroups]
        url = "clusters/%s/nodegroups" % cluster_id
        collection.next = collection.get_next(limit,
                                              url=url,
                                              **kwargs)
        return collection


class NodeGroupController(base.Controller):
    """REST controller for Node Groups."""

    def __init__(self):
        super(NodeGroupController, self).__init__()

    def _get_nodegroup_collection(self, cluster_id, marker, limit, sort_key,
                                  sort_dir, filters, expand=True):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.NodeGroup.get(pecan.request.context,
                                               cluster_id,
                                               marker)

        nodegroups = objects.NodeGroup.list(pecan.request.context,
                                            cluster_id,
                                            limit=limit,
                                            marker=marker_obj,
                                            sort_key=sort_key,
                                            sort_dir=sort_dir,
                                            filters=filters)

        return NodeGroupCollection.convert(nodegroups,
                                           cluster_id,
                                           limit,
                                           expand=expand,
                                           sort_key=sort_key,
                                           sort_dir=sort_dir)

    @base.Controller.api_version("1.9")
    @expose.expose(NodeGroupCollection, types.uuid_or_name, types.uuid, int,
                   wtypes.text, wtypes.text, wtypes.text)
    def get_all(self, cluster_id, marker=None, limit=None, sort_key='id',
                sort_dir='asc', role=None):
        """Retrieve a list of nodegroups.

        :param cluster_id: the cluster id or name
        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param role: list all nodegroups with the specified role.
        """
        context = pecan.request.context
        policy.enforce(context, 'nodegroup:get_all',
                       action='nodegroup:get_all')

        if context.is_admin:
            policy.enforce(context, 'nodegroup:get_all_all_projects',
                           action='nodegroup:get_all_all_projects')
            context.all_tenants = True

        cluster = api_utils.get_resource('Cluster', cluster_id)

        filters = {}
        if not context.is_admin:
            filters = {"project_id": context.project_id}
        if role:
            filters.update({'role': role})

        return self._get_nodegroup_collection(cluster.uuid,
                                              marker,
                                              limit,
                                              sort_key,
                                              sort_dir,
                                              filters,
                                              expand=False)

    @base.Controller.api_version("1.9")
    @expose.expose(NodeGroup, types.uuid_or_name, types.uuid_or_name)
    def get_one(self, cluster_id, nodegroup_id):
        """Retrieve information for the given nodegroup in a cluster.

        :param id: cluster id.
        :param resource: nodegroup id.
        """
        context = pecan.request.context
        policy.enforce(context, 'nodegroup:get', action='nodegroup:get')
        if context.is_admin:
            policy.enforce(context, "nodegroup:get_one_all_projects",
                           action="nodegroup:get_one_all_projects")
            context.all_tenants = True
        cluster = api_utils.get_resource('Cluster', cluster_id)
        nodegroup = objects.NodeGroup.get(context, cluster.uuid, nodegroup_id)
        return NodeGroup.convert(nodegroup)

    @base.Controller.api_version("1.9")
    @expose.expose(NodeGroup, types.uuid_or_name, NodeGroup, body=NodeGroup,
                   status_code=202)
    def post(self, cluster_id, nodegroup):
        """Create NodeGroup.

        :param nodegroup: a json document to create this NodeGroup.
        """

        context = pecan.request.context
        policy.enforce(context, 'nodegroup:create', action='nodegroup:create')

        cluster = api_utils.get_resource('Cluster', cluster_id)
        # Before we start, we need to check that the cluster has an
        # api_address. If not, just fail.
        if 'api_address' not in cluster or not cluster.api_address:
            raise exception.ClusterAPIAddressUnavailable()
        cluster_ngs = [ng.name for ng in cluster.nodegroups]
        if nodegroup.name in cluster_ngs:
            raise exception.NodeGroupAlreadyExists(name=nodegroup.name,
                                                   cluster_id=cluster.name)
        _validate_node_count(nodegroup)

        if nodegroup.role == "master":
            # Currently we don't support adding master nodegroups.
            # Keep this until we start supporting it.
            raise exception.CreateMasterNodeGroup()
        if nodegroup.image_id is None or nodegroup.image_id == wtypes.Unset:
            nodegroup.image_id = cluster.cluster_template.image_id
        if nodegroup.flavor_id is None or nodegroup.flavor_id == wtypes.Unset:
            nodegroup.flavor_id = cluster.flavor_id
        if nodegroup.labels is None or nodegroup.labels == wtypes.Unset:
            nodegroup.labels = cluster.labels
        else:
            # If labels are provided check if the user wishes to merge
            # them with the values from the cluster.
            if nodegroup.merge_labels:
                labels = cluster.labels
                labels.update(nodegroup.labels)
                nodegroup.labels = labels

        nodegroup_dict = nodegroup.as_dict()
        nodegroup_dict['cluster_id'] = cluster.uuid
        nodegroup_dict['project_id'] = context.project_id

        new_obj = objects.NodeGroup(context, **nodegroup_dict)
        new_obj.uuid = uuid.uuid4()
        pecan.request.rpcapi.nodegroup_create_async(cluster, new_obj)
        return NodeGroup.convert(new_obj)

    @base.Controller.api_version("1.9")
    @expose.expose(NodeGroup, types.uuid_or_name, types.uuid_or_name,
                   body=[NodeGroupPatchType], status_code=202)
    def patch(self, cluster_id, nodegroup_id, patch):
        """Update NodeGroup.

        :param cluster_id: cluster id.
        :param : resource name.
        :param values: a json document to update a nodegroup.
        """
        cluster = api_utils.get_resource('Cluster', cluster_id)
        nodegroup = self._patch(cluster.uuid, nodegroup_id, patch)
        pecan.request.rpcapi.nodegroup_update_async(cluster, nodegroup)
        return NodeGroup.convert(nodegroup)

    @base.Controller.api_version("1.9")
    @expose.expose(None, types.uuid_or_name, types.uuid_or_name,
                   status_code=204)
    def delete(self, cluster_id,  nodegroup_id):
        """Delete NodeGroup for a given project_id and resource.

        :param cluster_id: cluster id.
        :param nodegroup_id: resource name.
        """
        context = pecan.request.context
        policy.enforce(context, 'nodegroup:delete', action='nodegroup:delete')
        cluster = api_utils.get_resource('Cluster', cluster_id)
        nodegroup = objects.NodeGroup.get(context, cluster.uuid, nodegroup_id)
        if nodegroup.is_default:
            raise exception.DeletingDefaultNGNotSupported()
        pecan.request.rpcapi.nodegroup_delete_async(cluster, nodegroup)

    def _patch(self, cluster_uuid, nodegroup_id, patch):
        context = pecan.request.context
        policy.enforce(context, 'nodegroup:update', action='nodegroup:update')
        nodegroup = objects.NodeGroup.get(context, cluster_uuid, nodegroup_id)

        try:
            ng_dict = nodegroup.as_dict()
            new_nodegroup = NodeGroup(**api_utils.apply_jsonpatch(ng_dict,
                                                                  patch))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        # Update only the fields that have changed
        for field in objects.NodeGroup.fields:
            try:
                patch_val = getattr(new_nodegroup, field)
            except AttributeError:
                # Ignore fields that aren't exposed in the API
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if nodegroup[field] != patch_val:
                nodegroup[field] = patch_val
        _validate_node_count(nodegroup)

        return nodegroup
