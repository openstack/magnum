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
from pycadf import cadftaxonomy as taxonomy
from pycadf import cadftype
from pycadf import eventfactory
from pycadf import resource

from magnum.common import clients
from magnum.common import rpc
from magnum.objects import cluster
from magnum.objects import cluster_template


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


def notify_about_cluster_operation(context, action, outcome):
    """Send a notification about cluster operation.

    :param action: CADF action being audited
    :param outcome: CADF outcome
    """
    notifier = rpc.get_notifier()
    event = eventfactory.EventFactory().new_event(
        eventType=cadftype.EVENTTYPE_ACTIVITY,
        outcome=outcome,
        action=action,
        initiator=_get_request_audit_info(context),
        target=resource.Resource(typeURI='service/magnum/cluster'),
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
