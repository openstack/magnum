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

import re

import pecan
import wsme
from wsme import types as wtypes

from magnum.api.controllers import base
from magnum.api.controllers.v1 import types
from magnum.api import expose
from magnum.api import utils as api_utils
from magnum.common import exception
from magnum.common import policy
from magnum import objects


def _get_cluster_resource(cluster_ident, admin_action=None):
    context = pecan.request.context
    if context.is_admin and admin_action:
        policy.enforce(context, admin_action, action=admin_action)
        context.all_tenants = True

    return api_utils.get_resource('Cluster', cluster_ident)


def _parse_kube_minor(tag):
    if not tag:
        return None
    m = re.match(r'v?(\d+)\.(\d+)', tag)
    if m:
        return int(m.group(1)) * 1000 + int(m.group(2))
    return None


def _validate_upgrade_version_skew(cluster, new_cluster_template, nodegroup):
    """Reject upgrades where the target kube_tag is >±1 minor from the cluster.

    For default nodegroups the target becomes the new cluster version, so
    only forward skew (+1) is meaningful.  For non-default nodegroups the
    check compares against the current cluster control-plane version.
    """
    new_tag = (new_cluster_template.labels or {}).get('kube_tag')
    cluster_tag = (cluster.labels or {}).get('kube_tag')
    if not cluster_tag:
        cluster_tag = (cluster.cluster_template.labels or {}).get('kube_tag')
    if not new_tag or not cluster_tag:
        return
    # For default nodegroups the upgrade target IS the new cluster version,
    # so skip the skew check — upstream version validation handles it.
    if nodegroup.is_default:
        return
    new_minor = _parse_kube_minor(new_tag)
    cluster_minor = _parse_kube_minor(cluster_tag)
    if new_minor is None or cluster_minor is None:
        return
    if abs(new_minor - cluster_minor) > 1:
        raise exception.InvalidParameterValue(
            "Kubernetes version skew between the cluster control plane "
            "(%s) and the upgrade target (%s) exceeds the supported "
            "range of +/-1 minor version." % (cluster_tag, new_tag))


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

    max_batch_size = wsme.wsattr(wtypes.IntegerType(minimum=1), default=1)
    """Max batch size of nodes to be upgraded in parallel"""

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

    @base.Controller.api_version("1.7")
    @expose.expose(ClusterID, types.uuid_or_name,
                   body=ClusterResizeRequest, status_code=202)
    def resize(self, cluster_ident, cluster_resize_req):
        """Resize a cluster.

        :param cluster_ident: UUID of a cluster or logical name of the cluster.
        """
        context = pecan.request.context
        cluster = _get_cluster_resource(cluster_ident,
                                        'cluster:resize_all_projects')
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

        if nodegroup.role == 'master':
            cluster_template = cluster.cluster_template
            if cluster_resize_req.node_count == 0:
                raise exception.InvalidParameterValue(
                    "Master node count cannot be 0. Kubernetes clusters require at least 1 master node.")
            if (cluster_resize_req.node_count > 1 and 
                not cluster_template.master_lb_enabled):
                raise exception.InvalidParameterValue(
                    "Master node count must be 1 when master_lb_enabled is False")
            
            # Enforce incremental scaling for master scale-down (safety for etcd quorum)
            # Scale-up can be done in larger increments since adding nodes doesn't break quorum
            current_count = nodegroup.node_count
            target_count = cluster_resize_req.node_count
            
            if target_count < current_count:
                # Only enforce incremental scaling for scale-down operations
                scaling_difference = current_count - target_count
                
                if scaling_difference > 1:
                    suggested_target = current_count - 1
                    
                    raise exception.InvalidParameterValue(
                        f"Master nodes can only be scaled down by 1 at a time to maintain etcd quorum. "
                        f"Cannot scale down from {current_count} to {target_count} masters. "
                        f"Please scale down to {suggested_target} first, then continue scaling after "
                        f"the operation completes successfully.")

        # NOTE(ttsiouts): Make sure that the new node count is within
        # the configured boundaries of the selected nodegroup.
        if nodegroup.min_node_count > cluster_resize_req.node_count:
            raise exception.NGResizeOutBounds(
                nodegroup=nodegroup.name, min_nc=nodegroup.min_node_count,
                max_nc=nodegroup.max_node_count)
        if (nodegroup.max_node_count and
                nodegroup.max_node_count < cluster_resize_req.node_count):
            raise exception.NGResizeOutBounds(
                nodegroup=nodegroup.name, min_nc=nodegroup.min_node_count,
                max_nc=nodegroup.max_node_count)

        pecan.request.rpcapi.cluster_resize_async(
            cluster,
            cluster_resize_req.node_count,
            cluster_resize_req.nodes_to_remove,
            nodegroup)
        return ClusterID(cluster.uuid)

    @base.Controller.api_version("1.8")
    @expose.expose(ClusterID, types.uuid_or_name,
                   body=ClusterUpgradeRequest, status_code=202)
    def upgrade(self, cluster_ident, cluster_upgrade_req):
        """Upgrade a cluster.

        :param cluster_ident: UUID of a cluster or logical name of the cluster.
        """
        context = pecan.request.context
        cluster = _get_cluster_resource(cluster_ident,
                                        'cluster:upgrade_all_projects')
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
            # Allow non-default nodegroups to upgrade to any template
            # The cluster_template_id label will be updated in the driver

        _validate_upgrade_version_skew(cluster, new_cluster_template, nodegroup)

        pecan.request.rpcapi.cluster_upgrade(
            cluster,
            new_cluster_template,
            cluster_upgrade_req.max_batch_size,
            nodegroup)
        return ClusterID(cluster.uuid)
