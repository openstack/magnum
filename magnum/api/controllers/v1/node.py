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

from oslo_utils import timeutils
import pecan
from pecan import rest
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


class NodePatchType(types.JsonPatchType):
    pass


class Node(base.APIBase):
    """API representation of a node.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a node.
    """

    uuid = types.uuid
    """Unique UUID for this node"""

    type = wtypes.text
    """Type of this node"""

    image_id = wtypes.text
    """The image name or UUID to use as a base image for this node"""

    ironic_node_id = wtypes.text
    """The Ironic node ID associated with this node"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated node links"""

    def __init__(self, **kwargs):
        self.fields = []
        for field in objects.Node.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @staticmethod
    def _convert_with_links(node, url, expand=True):
        if not expand:
            node.unset_fields_except(['uuid', 'name', 'type', 'image_id',
                                      'ironic_node_id'])

        node.links = [link.Link.make_link('self', url,
                                          'nodes', node.uuid),
                      link.Link.make_link('bookmark', url,
                                          'nodes', node.uuid,
                                          bookmark=True)]
        return node

    @classmethod
    def convert_with_links(cls, rpc_node, expand=True):
        node = Node(**rpc_node.as_dict())
        return cls._convert_with_links(node, pecan.request.host_url, expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(uuid='27e3153e-d5bf-4b7e-b517-fb518e17f34c',
                     type='virt',
                     image_id='Fedora-k8s',
                     ironic_node_id='4b6ec4a9-d412-494a-be77-a2fd16361402',
                     created_at=timeutils.utcnow(),
                     updated_at=timeutils.utcnow())
        return cls._convert_with_links(sample, 'http://localhost:9511', expand)


class NodeCollection(collection.Collection):
    """API representation of a collection of nodes."""

    nodes = [Node]
    """A list containing nodes objects"""

    def __init__(self, **kwargs):
        self._type = 'nodes'

    @staticmethod
    def convert_with_links(rpc_nodes, limit, url=None, expand=False, **kwargs):
        collection = NodeCollection()
        collection.nodes = [Node.convert_with_links(p, expand)
                            for p in rpc_nodes]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.nodes = [Node.sample(expand=False)]
        return sample


class NodesController(rest.RestController):
    """REST controller for Nodes."""

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_nodes_collection(self, marker, limit,
                              sort_key, sort_dir, expand=False,
                              resource_url=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Node.get_by_uuid(pecan.request.context,
                                                  marker)

        nodes = objects.Node.list(pecan.request.context, limit,
                                  marker_obj, sort_key=sort_key,
                                  sort_dir=sort_dir)

        return NodeCollection.convert_with_links(nodes, limit,
                                                 url=resource_url,
                                                 expand=expand,
                                                 sort_key=sort_key,
                                                 sort_dir=sort_dir)

    @expose.expose(NodeCollection, types.uuid, int, wtypes.text,
                   wtypes.text)
    @policy.enforce_wsgi("node")
    def get_all(self, marker=None, limit=None, sort_key='id',
                sort_dir='asc'):
        """Retrieve a list of nodes.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        return self._get_nodes_collection(marker, limit, sort_key,
                                          sort_dir)

    @expose.expose(NodeCollection, types.uuid, int, wtypes.text,
                   wtypes.text)
    @policy.enforce_wsgi("node")
    def detail(self, marker=None, limit=None, sort_key='id',
               sort_dir='asc'):
        """Retrieve a list of nodes with detail.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        # NOTE(lucasagomes): /detail should only work against collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "nodes":
            raise exception.HTTPNotFound

        expand = True
        resource_url = '/'.join(['nodes', 'detail'])
        return self._get_nodes_collection(marker, limit,
                                          sort_key, sort_dir, expand,
                                          resource_url)

    @expose.expose(Node, types.uuid)
    @policy.enforce_wsgi("node", "get")
    def get_one(self, node_uuid):
        """Retrieve information about the given node.

        :param node_uuid: UUID of a node.
        """
        rpc_node = objects.Node.get_by_uuid(pecan.request.context, node_uuid)
        return Node.convert_with_links(rpc_node)

    @expose.expose(Node, body=Node, status_code=201)
    @policy.enforce_wsgi("node", "create")
    def post(self, node):
        """Create a new node.

        :param node: a node within the request body.
        """
        node_dict = node.as_dict()
        context = pecan.request.context
        node_dict['project_id'] = context.project_id
        node_dict['user_id'] = context.user_id
        new_node = objects.Node(context, **node_dict)
        new_node.create()
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('nodes', new_node.uuid)
        return Node.convert_with_links(new_node)

    @wsme.validate(types.uuid, [NodePatchType])
    @expose.expose(Node, types.uuid, body=[NodePatchType])
    @policy.enforce_wsgi("node", "update")
    def patch(self, node_uuid, patch):
        """Update an existing node.

        :param node_uuid: UUID of a node.
        :param patch: a json PATCH document to apply to this node.
        """
        rpc_node = objects.Node.get_by_uuid(pecan.request.context, node_uuid)
        try:
            node_dict = rpc_node.as_dict()
            node = Node(**api_utils.apply_jsonpatch(node_dict, patch))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        # Update only the fields that have changed
        for field in objects.Node.fields:
            try:
                patch_val = getattr(node, field)
            except AttributeError:
                # Ignore fields that aren't exposed in the API
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if rpc_node[field] != patch_val:
                rpc_node[field] = patch_val

        rpc_node.save()
        return Node.convert_with_links(rpc_node)

    @expose.expose(None, types.uuid, status_code=204)
    @policy.enforce_wsgi("node", "delete")
    def delete(self, node_uuid):
        """Delete a node.

        :param node_uuid: UUID of a node.
        """
        rpc_node = objects.Node.get_by_uuid(pecan.request.context,
                                            node_uuid)
        rpc_node.destroy()
