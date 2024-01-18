# Copyright 2015 Huawei Technologies Co.,LTD.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_utils import uuidutils
from pycadf import attachment
from pycadf import cadftaxonomy as taxonomy
from pycadf import cadftype
from pycadf import eventfactory
from pycadf import resource
from wsme import types as wtypes

from magnum.common import clients
from magnum.common import rpc
from magnum.objects import cluster
from magnum.objects import cluster_template
from magnum.objects import fields
from magnum.objects import nodegroup


def retrieve_cluster(context, cluster_ident):
    if not uuidutils.is_uuid_like(cluster_ident):
        return cluster.Cluster.get_by_name(context, cluster_ident)
    else:
        return cluster.Cluster.get_by_uuid(context, cluster_ident)


def retrieve_cluster_template(context, cluster):
    return cluster_template.ClusterTemplate.get_by_uuid(
        context, cluster.cluster_template_id)


def retrieve_cluster_uuid(context, cluster_ident):
    if not uuidutils.is_uuid_like(cluster_ident):
        cluster_obj = cluster.Cluster.get_by_name(context, cluster_ident)
        return cluster_obj.uuid
    else:
        return cluster_ident


def retrieve_ct_by_name_or_uuid(context, cluster_template_ident):
    if not uuidutils.is_uuid_like(cluster_template_ident):
        return cluster_template.ClusterTemplate.get_by_name(
            context,
            cluster_template_ident)
    else:
        return cluster_template.ClusterTemplate.get_by_uuid(
            context,
            cluster_template_ident)


def object_has_stack(context, cluster_uuid):
    osc = clients.OpenStackClients(context)
    obj = retrieve_cluster(context, cluster_uuid)

    stack = osc.heat().stacks.get(obj.stack_id)
    if (stack.stack_status == 'DELETE_COMPLETE' or
            stack.stack_status == 'DELETE_IN_PROGRESS'):
        return False

    return True


def _get_request_audit_info(context):
    """Collect audit information about the request used for CADF.

    :param context: Request context
    :returns: Auditing data about the request
    :rtype: :class:'pycadf.Resource'
    """
    user_id = None
    project_id = None
    domain_id = None

    if context:
        user_id = context.user_id
        project_id = context.project_id
        domain_id = context.domain_id

    initiator = resource.Resource(typeURI=taxonomy.ACCOUNT_USER)

    if user_id:
        initiator.user_id = user_id

    if project_id:
        initiator.project_id = project_id

    if domain_id:
        initiator.domain_id = domain_id

    return initiator


def _get_event_target(cluster_obj=None):
    if cluster_obj:
        target = resource.Resource(
            id=cluster_obj.uuid,
            name=cluster_obj.name,
            typeURI='service/magnum/cluster'
        )
        target.add_attachment(attach_val=attachment.Attachment(
            typeURI='service/magnum/cluster',
            content={
                'status': cluster_obj.status,
                'status_reason': cluster_obj.status_reason,
                'project_id': cluster_obj.project_id,
                'created_at': cluster_obj.created_at,
                'updated_at': cluster_obj.updated_at,
                'cluster_template_id': cluster_obj.cluster_template_id,
                'keypair': cluster_obj.keypair,
                'docker_volume_size:': cluster_obj.docker_volume_size,
                'labels': cluster_obj.labels,
                'master_flavor_id': cluster_obj.master_flavor_id,
                'flavor_id': cluster_obj.flavor_id,
                'stack_id': cluster_obj.stack_id,
                'health_status': cluster_obj.health_status,
                'create_timeout': cluster_obj.create_timeout,
                'api_address': cluster_obj.api_address,
                'discovery_url': cluster_obj.discovery_url,
                'node_addresses': cluster_obj.node_addresses,
                'master_addresses': cluster_obj.master_addresses,
                'node_count': cluster_obj.node_count,
                'master_count': cluster_obj.master_count,
            },
            name='cluster_data'
        ))
        return target
    return resource.Resource(typeURI='service/magnum/cluster')


def notify_about_cluster_operation(context, action, outcome, cluster_obj=None):
    """Send a notification about cluster operation.

    :param action: CADF action being audited
    :param outcome: CADF outcome
    :param cluster_obj: the cluster the notification is related to
    """
    notifier = rpc.get_notifier()

    event = eventfactory.EventFactory().new_event(
        eventType=cadftype.EVENTTYPE_ACTIVITY,
        outcome=outcome,
        action=action,
        initiator=_get_request_audit_info(context),
        target=_get_event_target(cluster_obj=cluster_obj),
        observer=resource.Resource(typeURI='service/magnum/cluster'))
    service = 'magnum'
    event_type = '%(service)s.cluster.%(action)s' % {
        'service': service, 'action': action}
    payload = event.as_dict()

    if outcome == taxonomy.OUTCOME_FAILURE:
        method = notifier.error
    else:
        method = notifier.info

    method(context, event_type, payload)


def _get_nodegroup_object(context, cluster, node_count, is_master=False):
    """Returns a nodegroup object based on the given cluster object."""
    ng = nodegroup.NodeGroup(context)
    ng.cluster_id = cluster.uuid
    ng.project_id = cluster.project_id
    ng.labels = cluster.labels
    ng.node_count = node_count
    ng.image_id = cluster.cluster_template.image_id
    ng.docker_volume_size = (cluster.docker_volume_size or
                             cluster.cluster_template.docker_volume_size)

    if is_master:
        ng.flavor_id = (cluster.master_flavor_id or
                        cluster.cluster_template.master_flavor_id)
        ng.role = "master"
    else:
        ng.flavor_id = cluster.flavor_id or cluster.cluster_template.flavor_id
        ng.role = "worker"
        if (cluster.labels != wtypes.Unset and cluster.labels is not None
                and 'min_node_count' in cluster.labels):
            ng.min_node_count = cluster.labels['min_node_count']
    ng.name = "default-%s" % ng.role
    ng.is_default = True
    ng.status = fields.ClusterStatus.CREATE_IN_PROGRESS
    return ng
