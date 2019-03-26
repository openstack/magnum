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
import wsme
from wsme import types as wtypes

from magnum.api.controllers import base
from magnum.api.controllers import link
from magnum.api.controllers.v1 import collection
from magnum.api.controllers.v1 import types
from magnum.api import expose
from magnum.api import utils as api_utils
from magnum.common import policy
from magnum import objects


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

    labels = wtypes.DictType(str, str)
    """One or more key/value pairs"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated nodegroup links"""

    flavor_id = wtypes.StringType(min_length=1, max_length=255)
    """The flavor of this nodegroup"""

    image_id = wtypes.StringType(min_length=1, max_length=255)
    """The image used for this nodegroup"""

    node_addresses = wsme.wsattr([wtypes.text], readonly=True)
    """IP addresses of nodegroup nodes"""

    node_count = wsme.wsattr(wtypes.IntegerType(minimum=1), default=1)
    """The node count for this nodegroup. Default to 1 if not set"""

    role = wtypes.StringType(min_length=1, max_length=255)
    """The role of the nodes included in this nodegroup"""

    min_node_count = wsme.wsattr(wtypes.IntegerType(minimum=1), default=1)
    """The minimum allowed nodes for this nodegroup. Default to 1 if not set"""

    max_node_count = wsme.wsattr(wtypes.IntegerType(minimum=1), default=None)
    """The maximum allowed nodes for this nodegroup. Default to 1 if not set"""

    is_default = types.BooleanType()
    """Specifies is a nodegroup was created by default or not"""

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
                                    "role", "is_default", "image_id"])
        else:
            ng.links = [link.Link.make_link('self', url, cluster_path,
                                            nodegroup_path),
                        link.Link.make_link('bookmark', url,
                                            cluster_path, nodegroup_path,
                                            bookmark=True)]
        return ng


class NodeGroupCollection(collection.Collection):
    """API representation of a collection of Node Groups."""

    nodegroups = [NodeGroup]
    """A list containing quota objects"""

    def __init__(self, **kwargs):
        self._type = 'nodegroups'

    @staticmethod
    def convert(nodegroups, limit, expand=True, **kwargs):
        collection = NodeGroupCollection()
        collection.nodegroups = [NodeGroup.convert(ng, expand)
                                 for ng in nodegroups]
        collection.next = collection.get_next(limit,
                                              marker_attribute='id',
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
            marker_obj = objects.NodeGroup.list(pecan.request.context,
                                                cluster_id,
                                                marker)

        nodegroups = objects.NodeGroup.list(pecan.request.context,
                                            cluster_id,
                                            limit,
                                            marker_obj,
                                            sort_key=sort_key,
                                            sort_dir=sort_dir,
                                            filters=filters)

        return NodeGroupCollection.convert(nodegroups,
                                           limit,
                                           expand=expand,
                                           sort_key=sort_key,
                                           sort_dir=sort_dir)

    @expose.expose(NodeGroupCollection, types.uuid_or_name, int, int,
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
