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

import re

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


def _get_cluster_resource(cluster_id, admin_action=None):
    context = pecan.request.context
    if context.is_admin and admin_action:
        policy.enforce(context, admin_action, action=admin_action)
        context.all_tenants = True

    return api_utils.get_resource('Cluster', cluster_id)


# Per-nodegroup Kubernetes node metadata, transported as the well-known
# labels ``node_labels`` ("k1=v1;k2=v2") and ``node_taints``
# ("key=value:Effect;..."). Validated server-side so a bad entry fails the
# API call instead of surfacing as a node-side reconciler warning.
NODE_TAINT_EFFECTS = ("NoSchedule", "PreferNoSchedule", "NoExecute")
_LABEL_NAME_RE = re.compile(r'^[A-Za-z0-9]([A-Za-z0-9._-]{0,61}[A-Za-z0-9])?$')
_LABEL_PREFIX_RE = re.compile(
    r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?'
    r'(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*$')
_RESERVED_TAINT_PREFIXES = ("node-role.kubernetes.io/", "node.kubernetes.io/")
_RESERVED_LABEL_KEYS = ("magnum.openstack.org/role",
                        "magnum.openstack.org/nodegroup")


def _valid_metadata_key(key):
    if '/' in key:
        prefix, _, name = key.partition('/')
        if (not prefix or len(prefix) > 253
                or not _LABEL_PREFIX_RE.match(prefix)):
            return False
    else:
        name = key
    return bool(name) and bool(_LABEL_NAME_RE.match(name))


def _validate_node_metadata(ng_name, labels):
    if not labels:
        return
    node_labels = labels.get('node_labels')
    if node_labels:
        for item in str(node_labels).split(';'):
            item = item.strip()
            if not item:
                continue
            key, _, value = item.partition('=')
            key = key.strip()
            value = value.strip()
            if not _valid_metadata_key(key):
                _raise_node_metadata('node_labels', ng_name,
                                     'invalid label key %r' % key)
            if key in _RESERVED_LABEL_KEYS:
                _raise_node_metadata('node_labels', ng_name,
                                     'label key %r is reserved' % key)
            if value and not _LABEL_NAME_RE.match(value):
                _raise_node_metadata('node_labels', ng_name,
                                     'invalid label value %r' % value)
    node_taints = labels.get('node_taints')
    if node_taints:
        for item in str(node_taints).split(';'):
            item = item.strip()
            if not item:
                continue
            body, sep, effect = item.rpartition(':')
            if not sep or effect not in NODE_TAINT_EFFECTS:
                _raise_node_metadata(
                    'node_taints', ng_name,
                    'taint %r must end with :NoSchedule, :PreferNoSchedule '
                    'or :NoExecute' % item)
            key, _, value = body.partition('=')
            key = key.strip()
            value = value.strip()
            if not _valid_metadata_key(key):
                _raise_node_metadata('node_taints', ng_name,
                                     'invalid taint key %r' % key)
            if any(key.startswith(p) for p in _RESERVED_TAINT_PREFIXES):
                _raise_node_metadata('node_taints', ng_name,
                                     'taint key %r is reserved' % key)
            if value and not _LABEL_NAME_RE.match(value):
                _raise_node_metadata('node_taints', ng_name,
                                     'invalid taint value %r' % value)


def _raise_node_metadata(attr, ng_name, expl):
    raise exception.NodeGroupInvalidInput(attr=attr, nodegroup=ng_name,
                                          expl=expl)


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
    # min_node_count > node_count is allowed: the cluster autoscaler will
    # scale the nodegroup up to meet the configured minimum.


def _parse_kube_minor(tag):
    """Extract the minor version number from a kube_tag like 'v1.29.14'."""
    if not tag:
        return None
    m = re.match(r'v?(\d+)\.(\d+)', tag)
    if m:
        return int(m.group(1)) * 1000 + int(m.group(2))
    return None


def _validate_version_skew(cluster, nodegroup_labels):
    """Reject nodegroups whose kube_tag is more than ±1 minor from the cluster."""
    ng_labels = nodegroup_labels or {}
    ng_tag = ng_labels.get('kube_tag')
    # If the nodegroup uses a different cluster template, resolve its kube_tag
    if not ng_tag and 'cluster_template_id' in ng_labels:
        context = pecan.request.context
        try:
            ct = api_utils.get_resource('ClusterTemplate',
                                        ng_labels['cluster_template_id'])
            ng_tag = (ct.labels or {}).get('kube_tag')
        except Exception:
            pass
    cluster_tag = (cluster.labels or {}).get('kube_tag')
    if not cluster_tag:
        cluster_tag = (cluster.cluster_template.labels or {}).get('kube_tag')
    if not ng_tag or not cluster_tag:
        return
    ng_minor = _parse_kube_minor(ng_tag)
    cluster_minor = _parse_kube_minor(cluster_tag)
    if ng_minor is None or cluster_minor is None:
        return
    diff = abs(ng_minor - cluster_minor)
    if diff > 1:
        raise exception.NodeGroupInvalidInput(
            attr='kube_tag',
            nodegroup='-',
            expl=("Kubernetes version skew between the cluster (%s) "
                  "and the nodegroup (%s) exceeds the supported "
                  "range of +/-1 minor version" % (cluster_tag, ng_tag)))


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
        # Allow updating min/max_node_count and labels (labels carry the
        # per-nodegroup node_labels/node_taints node metadata; the heat
        # driver pushes changed metadata to the nodegroup stack).
        internal_attrs = ["/name", "/cluster_id", "/project_id",
                          "/docker_volume_size", "/flavor_id",
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
        cluster = _get_cluster_resource(cluster_id,
                                        'nodegroup:get_all_all_projects')

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
        cluster = _get_cluster_resource(cluster_id,
                                        'nodegroup:get_one_all_projects')
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
        cluster = _get_cluster_resource(cluster_id,
                                        'nodegroup:create_all_projects')
        # Before we start, we need to check that the cluster has an
        # api_address. If not, just fail.
        if 'api_address' not in cluster or not cluster.api_address:
            raise exception.ClusterAPIAddressUnavailable()
        cluster_ngs = [ng.name for ng in cluster.nodegroups]
        if nodegroup.name in cluster_ngs:
            raise exception.NodeGroupAlreadyExists(name=nodegroup.name,
                                                   cluster_id=cluster.name)
        _validate_node_count(nodegroup)

        role = (nodegroup.role or "").strip().lower()
        if role in ("master", "control-plane", "controlplane"):
            # Currently we don't support adding master nodegroups. Reject the
            # control-plane spellings too: the node-side reconciler detects
            # its role from NODEGROUP_ROLE and would bootstrap such a node
            # down the master path (etcd join, apiserver) inside a worker
            # nodegroup.
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

        _validate_version_skew(cluster, nodegroup.labels)
        _validate_node_metadata(nodegroup.name, nodegroup.labels)

        nodegroup_dict = nodegroup.as_dict()
        nodegroup_dict['cluster_id'] = cluster.uuid
        nodegroup_dict['project_id'] = cluster.project_id

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
        cluster = _get_cluster_resource(cluster_id,
                                        'nodegroup:update_all_projects')
        nodegroup, needs_resize, labels_changed = self._patch(
            cluster, nodegroup_id, patch)
        if needs_resize and labels_changed:
            # A labels change rides a params-only stack update while a resize
            # changes the group size; combining them in one heat update would
            # entangle two failure domains. Trivial to do as two PATCHes.
            raise exception.InvalidParameterValue(
                "labels cannot be updated together with a node count "
                "change; update labels and counts in separate requests")
        if needs_resize:
            pecan.request.rpcapi.cluster_resize_async(
                cluster, nodegroup.node_count, None, nodegroup)
        else:
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
        cluster = _get_cluster_resource(cluster_id,
                                        'nodegroup:delete_all_projects')
        nodegroup = objects.NodeGroup.get(context, cluster.uuid, nodegroup_id)
        if nodegroup.is_default:
            raise exception.DeletingDefaultNGNotSupported()
        pecan.request.rpcapi.nodegroup_delete_async(cluster, nodegroup)

    def _patch(self, cluster, nodegroup_id, patch):
        context = pecan.request.context
        policy.enforce(context, 'nodegroup:update', action='nodegroup:update')
        nodegroup = objects.NodeGroup.get(context, cluster.uuid, nodegroup_id)
        old_node_count = nodegroup.node_count
        old_labels = dict(nodegroup.labels or {})

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

        # When min_node_count is raised above the current node_count,
        # bump node_count to match so Magnum triggers an actual resize.
        # Without this the autoscaler would only react to unschedulable
        # pods, leaving the nodegroup at 0 indefinitely.
        if nodegroup.min_node_count > nodegroup.node_count:
            nodegroup.node_count = nodegroup.min_node_count

        _validate_node_count(nodegroup)

        labels_changed = dict(nodegroup.labels or {}) != old_labels
        if labels_changed:
            # kube_tag can ride a labels patch — keep the version-skew guard.
            _validate_version_skew(cluster, nodegroup.labels)
            _validate_node_metadata(nodegroup.name, nodegroup.labels)

        needs_resize = nodegroup.node_count != old_node_count
        return nodegroup, needs_resize, labels_changed
