#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import pecan
import wsme
from wsme import types as wtypes

from magnum.api.controllers import base
from magnum.api.controllers.v1 import types
from magnum.api import expose
from magnum.api import utils as api_utils
from magnum.common import exception
from magnum.common import policy
from magnum.drivers.common.driver import Driver
from magnum import objects


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


class ClusterResizeRequest(base.APIBase):
    """API object for handling resize requests.

    This class enforces type checking and value constraints.
    """

    node_count = wsme.wsattr(wtypes.IntegerType(minimum=0), mandatory=True)
    """The expected node count after resize."""

    nodes_to_remove = wsme.wsattr([wtypes.text], mandatory=False,
                                  default=[])
    """Instance ID list for nodes to be removed."""

    nodegroup = wtypes.StringType(min_length=1, max_length=255)
    """Group of nodes to be uprgaded (master or node)"""


class ClusterUpgradeRequest(base.APIBase):
    """API object for handling upgrade requests.

    This class enforces type checking and value constraints.
    """

    max_batch_size = wtypes.IntegerType(minimum=1)
    """Max batch size of nodes to be upraded in parallel"""

    nodegroup = wtypes.StringType(min_length=1, max_length=255)
    """Group of nodes to be uprgaded (master or node)"""

    cluster_template = wtypes.StringType(min_length=1, max_length=255)
    """The cluster_template UUID"""


class ActionsController(base.Controller):
    """REST controller for cluster actions."""
    def __init__(self):
        super(ActionsController, self).__init__()

    _custom_actions = {
        'resize': ['POST'],
        'upgrade': ['POST']
    }

    @base.Controller.api_version("1.7", "1.9")
    @expose.expose(ClusterID, types.uuid_or_name,
                   body=ClusterResizeRequest, status_code=202)
    def resize(self, cluster_ident, cluster_resize_req):
        if cluster_resize_req.node_count == 0:
            raise exception.ZeroNodeCountNotSupported()
        return self._resize(cluster_ident, cluster_resize_req)

    @base.Controller.api_version("1.10")  # noqa
    @expose.expose(ClusterID, types.uuid_or_name,
                   body=ClusterResizeRequest, status_code=202)
    def resize(self, cluster_ident, cluster_resize_req):  # noqa
        return self._resize(cluster_ident, cluster_resize_req)

    def _resize(self, cluster_ident, cluster_resize_req):
        """Resize a cluster.

        :param cluster_ident: UUID of a cluster or logical name of the cluster.
        """
        context = pecan.request.context
        cluster = api_utils.get_resource('Cluster', cluster_ident)
        policy.enforce(context, 'cluster:resize', cluster,
                       action='cluster:resize')

        if (cluster_resize_req.nodegroup == wtypes.Unset or
                not cluster_resize_req.nodegroup):
            # NOTE(ttsiouts): If the nodegroup is not specified
            # reflect the change to the default worker nodegroup
            nodegroup = cluster.default_ng_worker
        else:
            nodegroup = objects.NodeGroup.get(
                context, cluster.uuid, cluster_resize_req.nodegroup)

        # NOTE(ttsiouts): Make sure that the new node count is within
        # the configured boundaries of the selected nodegroup.
        if (nodegroup.role != "master" and
           nodegroup.min_node_count > cluster_resize_req.node_count):
            raise exception.NGResizeOutBounds(
                nodegroup=nodegroup.name, min_nc=nodegroup.min_node_count,
                max_nc=nodegroup.max_node_count)
        if (nodegroup.role != "master" and nodegroup.max_node_count and
                nodegroup.max_node_count < cluster_resize_req.node_count):
            raise exception.NGResizeOutBounds(
                nodegroup=nodegroup.name, min_nc=nodegroup.min_node_count,
                max_nc=nodegroup.max_node_count)

        if nodegroup.role == "master":
            cluster_driver = Driver.get_driver_for_cluster(context, cluster)
            cluster_driver.validate_master_resize(
                cluster_resize_req.node_count)

        pecan.request.rpcapi.cluster_resize_async(
            cluster,
            cluster_resize_req.node_count,
            cluster_resize_req.nodes_to_remove,
            nodegroup)
        return ClusterID(cluster.uuid)

    @base.Controller.api_version("1.7", "1.7")
    @expose.expose(ClusterID, types.uuid_or_name,
                   body=ClusterUpgradeRequest, status_code=202)
    def upgrade(self, cluster_ident, cluster_upgrade_req):
        raise exception.ClusterUpgradeNotSupported()

    @base.Controller.api_version("1.8")  # noqa
    @expose.expose(ClusterID, types.uuid_or_name,
                   body=ClusterUpgradeRequest, status_code=202)
    def upgrade(self, cluster_ident, cluster_upgrade_req):  # noqa
        return self._upgrade(cluster_ident, cluster_upgrade_req)

    def _upgrade(self, cluster_ident, cluster_upgrade_req):
        """Upgrade a cluster.

        :param cluster_ident: UUID of a cluster or logical name of the cluster.
        """
        context = pecan.request.context
        if context.is_admin:
            policy.enforce(context, "cluster:upgrade_all_projects",
                           action="cluster:upgrade_all_projects")
            context.all_tenants = True

        cluster = api_utils.get_resource('Cluster', cluster_ident)
        policy.enforce(context, 'cluster:upgrade', cluster,
                       action='cluster:upgrade')

        new_cluster_template = api_utils.get_resource(
            'ClusterTemplate', cluster_upgrade_req.cluster_template)

        if (cluster_upgrade_req.nodegroup == wtypes.Unset or
                not cluster_upgrade_req.nodegroup):
            # NOTE(ttsiouts): If the nodegroup is not specified
            # reflect the change to the default worker nodegroup
            nodegroup = cluster.default_ng_worker
        else:
            nodegroup = objects.NodeGroup.get(
                context, cluster.uuid, cluster_upgrade_req.nodegroup)
            if (new_cluster_template.uuid != cluster.cluster_template_id
                    and not nodegroup.is_default):
                reason = ("Nodegroup %s can be upgraded only to "
                          "match cluster's template (%s).")
                reason = reason % (nodegroup.name,
                                   cluster.cluster_template.name)
                raise exception.InvalidClusterTemplateForUpgrade(reason=reason)

        pecan.request.rpcapi.cluster_upgrade(
            cluster,
            new_cluster_template,
            cluster_upgrade_req.max_batch_size,
            nodegroup)
        return ClusterID(cluster.uuid)
