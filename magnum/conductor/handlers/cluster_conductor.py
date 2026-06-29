# Copyright 2014 NEC Corporation.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import eventlet
from heatclient import exc
from oslo_log import log as logging
from pycadf import cadftaxonomy as taxonomy
import six
from wsme import types as wtypes

from magnum.common import clients
from magnum.common import exception
from magnum.common import profiler
from magnum.conductor.handlers.common import cert_manager
from magnum.conductor.handlers.common import trust_manager
from magnum.conductor import scale_manager
from magnum.conductor import utils as conductor_utils
import magnum.conf
from magnum.drivers.common import driver
from magnum.i18n import _
from magnum import objects
from magnum.objects import fields

CONF = magnum.conf.CONF

LOG = logging.getLogger(__name__)


@profiler.trace_cls("rpc")
class Handler(object):

    def __init__(self):
        super(Handler, self).__init__()

    # Cluster Operations

    def cluster_create(self, context, cluster, master_count, node_count,
                       create_timeout):
        LOG.debug('cluster_heat cluster_create')

        osc = clients.OpenStackClients(context)

        cluster.status = fields.ClusterStatus.CREATE_IN_PROGRESS
        cluster.status_reason = None
        cluster.create()

        # Master nodegroup
        master_ng = conductor_utils._get_nodegroup_object(
            context, cluster, master_count, is_master=True)
        master_ng.create()
        # Minion nodegroup
        minion_ng = conductor_utils._get_nodegroup_object(
            context, cluster, node_count, is_master=False)
        minion_ng.create()

        try:
            # Create trustee/trust and set them to cluster
            trust_manager.create_trustee_and_trust(osc, cluster)
            # Generate certificate and set the cert reference to cluster
            cert_manager.generate_certificates_to_cluster(cluster,
                                                          context=context)
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_CREATE, taxonomy.OUTCOME_PENDING,
                cluster)
            # Get driver
            cluster_driver = driver.Driver.get_driver_for_cluster(context,
                                                                  cluster)
            # Create cluster
            cluster_driver.create_cluster(context, cluster, create_timeout)
            cluster.save()
            for ng in cluster.nodegroups:
                ng.stack_id = cluster.stack_id
                ng.save()

        except Exception as e:
            cluster.status = fields.ClusterStatus.CREATE_FAILED
            cluster.status_reason = six.text_type(e)
            cluster.save()
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_CREATE, taxonomy.OUTCOME_FAILURE,
                cluster)

            if isinstance(e, exc.HTTPBadRequest):
                e = exception.InvalidParameterValue(message=six.text_type(e))

                raise e
            raise

        return cluster

    def cluster_update(self, context, cluster, node_count,
                       health_status, health_status_reason, rollback=False,
                       labels_changed=False):
        LOG.debug('cluster_heat cluster_update')

        osc = clients.OpenStackClients(context)
        allow_update_status = (
            fields.ClusterStatus.CREATE_COMPLETE,
            fields.ClusterStatus.UPDATE_COMPLETE,
            fields.ClusterStatus.RESUME_COMPLETE,
            fields.ClusterStatus.RESTORE_COMPLETE,
            fields.ClusterStatus.ROLLBACK_COMPLETE,
            fields.ClusterStatus.SNAPSHOT_COMPLETE,
            fields.ClusterStatus.CHECK_COMPLETE,
            fields.ClusterStatus.ADOPT_COMPLETE,
            fields.ClusterStatus.UPDATE_FAILED,
        )
        if cluster.status not in allow_update_status:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_FAILURE,
                cluster)
            reason = _('Updating a cluster when status is '
                       '"%s"') % cluster.status
            failed_details = self._collect_heat_failed_resources(
                context, cluster)
            if failed_details:
                reason = _('%(reason)s. Failed stack resources: '
                           '%(details)s. Delete and recreate the cluster, '
                           'or resolve the failed resources manually before '
                           'retrying.') % {'reason': reason,
                                           'details': failed_details}
            raise exception.NotSupported(operation=reason)

        # Updates will be only reflected to the default worker
        # nodegroup.
        worker_ng = cluster.default_ng_worker
        node_count_changed = worker_ng.node_count != node_count
        health_changed = (cluster.health_status != health_status or
                          cluster.health_status_reason != health_status_reason)

        if not node_count_changed and not health_changed and not labels_changed:
            return

        cluster.health_status = health_status
        cluster.health_status_reason = health_status_reason

        # If only health status changed, save and return — no stack update.
        if not node_count_changed and not labels_changed:
            cluster.save()
            return cluster

        # Get driver
        ct = conductor_utils.retrieve_cluster_template(context, cluster)
        cluster_driver = driver.Driver.get_driver(ct.server_type,
                                                  ct.cluster_distro,
                                                  ct.coe)

        # Backup the old node count so that we can restore it
        # in case of an exception.
        old_node_count = worker_ng.node_count

        try:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_PENDING,
                cluster)

            if labels_changed and not node_count_changed:
                # Labels-only update: re-extract template definition with
                # new labels and push to all nodegroups. This triggers the
                # reconciler on each node to converge to the new desired
                # state (enable/disable addons, change chart versions, etc.)
                LOG.info('Updating cluster %s labels (reconfigure)',
                         cluster.uuid)

                # Sync patched cluster labels to default nodegroups so
                # that a later upgrade (which reads nodegroup.labels via
                # get_new_labels) does not revert user changes.
                for ng in [cluster.default_ng_master,
                           cluster.default_ng_worker]:
                    if ng is not None:
                        ng.labels = cluster.labels.copy()
                        ng.save()

                cluster_driver.reconfigure_cluster(context, cluster)
            else:
                # Node count change (scaling) — original behavior.
                manager = scale_manager.get_scale_manager(
                    context, osc, cluster)
                worker_ng.node_count = node_count
                worker_ng.save()
                cluster_driver.update_cluster(
                    context, cluster, manager, rollback)

            cluster.status = fields.ClusterStatus.UPDATE_IN_PROGRESS
            cluster.status_reason = None
        except Exception as e:
            cluster.status = fields.ClusterStatus.UPDATE_FAILED
            cluster.status_reason = six.text_type(e)
            cluster.save()
            if node_count_changed:
                # Restore the node_count
                worker_ng.node_count = old_node_count
                worker_ng.save()
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_FAILURE,
                cluster)
            if isinstance(e, exc.HTTPBadRequest):
                e = exception.InvalidParameterValue(message=six.text_type(e))
                raise e
            raise

        cluster.save()
        return cluster

    def cluster_delete(self, context, uuid):
        LOG.debug('cluster_conductor cluster_delete')
        osc = clients.OpenStackClients(context)
        cluster = objects.Cluster.get_by_uuid(context, uuid)
        ct = conductor_utils.retrieve_cluster_template(context, cluster)
        cluster_driver = driver.Driver.get_driver(ct.server_type,
                                                  ct.cluster_distro,
                                                  ct.coe)
        try:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_DELETE, taxonomy.OUTCOME_PENDING,
                cluster)
            cluster_driver.delete_cluster(context, cluster)
            cluster.status = fields.ClusterStatus.DELETE_IN_PROGRESS
            cluster.status_reason = None
        except exc.HTTPNotFound:
            LOG.info('The cluster %s was not found during cluster'
                     ' deletion.', cluster.id)
            try:
                trust_manager.delete_trustee_and_trust(osc, context, cluster)
                cert_manager.delete_certificates_from_cluster(cluster,
                                                              context=context)
                # delete all cluster's nodegroups
                for ng in cluster.nodegroups:
                    ng.destroy()
                cluster.destroy()
            except exception.ClusterNotFound:
                LOG.info('The cluster %s has been deleted by others.',
                         uuid)
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_DELETE, taxonomy.OUTCOME_SUCCESS,
                cluster)
            return None
        except exc.HTTPConflict:
            # If the cluster is already DELETE_FAILED, allow the retry —
            # the user is explicitly asking to delete again.
            if cluster.status == fields.ClusterStatus.DELETE_FAILED:
                LOG.info('Retrying delete for DELETE_FAILED cluster %s',
                         cluster.uuid)
                cluster.status = fields.ClusterStatus.DELETE_IN_PROGRESS
                cluster.status_reason = None
                cluster.save()
            else:
                conductor_utils.notify_about_cluster_operation(
                    context, taxonomy.ACTION_DELETE, taxonomy.OUTCOME_FAILURE,
                    cluster)
                raise exception.OperationInProgress(
                    cluster_name=cluster.name)
        except Exception as unexp:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_DELETE, taxonomy.OUTCOME_FAILURE,
                cluster)
            cluster.status = fields.ClusterStatus.DELETE_FAILED
            reason = six.text_type(unexp)
            # Append blocking Heat resource details so the user can see
            # exactly what prevented deletion.
            failed_details = self._collect_heat_failed_resources(
                context, cluster)
            if failed_details:
                reason = '%s | Blocking resources: %s' % (
                    reason, failed_details)
            cluster.status_reason = reason
            cluster.save()
            raise

        cluster.save()
        return None

    def cluster_resize(self, context, cluster,
                       node_count, nodes_to_remove, nodegroup):
        LOG.debug('cluster_conductor cluster_resize')

        osc = clients.OpenStackClients(context)
        # NOTE(flwang): One of important user cases of /resize API is
        # supporting the auto scaling action triggered by Kubernetes Cluster
        # Autoscaler, so there are 2 cases may happen:
        # 1. API could be triggered very offen
        # 2. Scale up or down may fail and we would like to offer the ability
        #    that recover the cluster to allow it being resized when last
        #    update failed.
        allow_update_status = (
            fields.ClusterStatus.CREATE_COMPLETE,
            fields.ClusterStatus.UPDATE_COMPLETE,
            fields.ClusterStatus.RESUME_COMPLETE,
            fields.ClusterStatus.RESTORE_COMPLETE,
            fields.ClusterStatus.ROLLBACK_COMPLETE,
            fields.ClusterStatus.SNAPSHOT_COMPLETE,
            fields.ClusterStatus.CHECK_COMPLETE,
            fields.ClusterStatus.ADOPT_COMPLETE,
            fields.ClusterStatus.UPDATE_FAILED,
            fields.ClusterStatus.UPDATE_IN_PROGRESS,
            # Allow recovery from a failed rollback (e.g. a migration update
            # that aborted then could not roll back) by retrying the resize.
            fields.ClusterStatus.ROLLBACK_FAILED,
        )
        if cluster.status not in allow_update_status:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_FAILURE,
                cluster)
            reason = _('Resizing a cluster when status is '
                       '"%s"') % cluster.status
            failed_details = self._collect_heat_failed_resources(
                context, cluster)
            if failed_details:
                reason = _('%(reason)s. Failed stack resources: '
                           '%(details)s. Delete and recreate the cluster, '
                           'or resolve the failed resources manually before '
                           'retrying.') % {'reason': reason,
                                           'details': failed_details}
            raise exception.NotSupported(operation=reason)

        resize_manager = scale_manager.get_scale_manager(context, osc, cluster)

        # Get driver
        ct = conductor_utils.retrieve_cluster_template(context, cluster)
        cluster_driver = driver.Driver.get_driver(ct.server_type,
                                                  ct.cluster_distro,
                                                  ct.coe)
        # Backup the old node count so that we can restore it
        # in case of an exception.
        old_node_count = nodegroup.node_count

        # Resize cluster
        try:
            nodegroup.node_count = node_count
            nodegroup.status = fields.ClusterStatus.UPDATE_IN_PROGRESS
            nodegroup.save()
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_PENDING,
                cluster)
            cluster_driver.resize_cluster(context, cluster, resize_manager,
                                          node_count, nodes_to_remove,
                                          nodegroup)
            cluster.status = fields.ClusterStatus.UPDATE_IN_PROGRESS
            cluster.status_reason = None
        except Exception as e:
            cluster.status = fields.ClusterStatus.UPDATE_FAILED
            cluster.status_reason = six.text_type(e)
            cluster.save()
            nodegroup.node_count = old_node_count
            nodegroup.status = fields.ClusterStatus.UPDATE_FAILED
            nodegroup.status_reason = six.text_type(e)
            nodegroup.save()
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_FAILURE,
                cluster)
            if isinstance(e, exc.HTTPBadRequest):
                e = exception.InvalidParameterValue(message=six.text_type(e))
                raise e
            raise

        cluster.save()
        return cluster

    def _collect_heat_failed_resources(self, context, cluster):
        """Query Heat for FAILED resources in the cluster stack.

        Returns a human-readable summary string, or empty string if
        no failed resources found or Heat is unreachable.
        """
        try:
            osc = clients.OpenStackClients(context)
            stack_id = cluster.stack_id
            if not stack_id:
                return ''
            failed_resources = osc.heat().resources.list(
                stack_id, nested_depth=2,
                filters={'status': 'FAILED'})
        except Exception as e:
            LOG.warning("Failed to retrieve failed resources for "
                        "cluster %(cluster)s from Heat stack %(stack)s: "
                        "%(err)s",
                        {'cluster': cluster.uuid,
                         'stack': cluster.stack_id, 'err': e})
            return ''

        if not failed_resources:
            return ''

        parts = []
        for res in failed_resources:
            parts.append('%s (%s): %s' % (
                res.resource_name, res.resource_type,
                res.resource_status_reason))
        return '; '.join(parts)

    def cluster_upgrade(self, context, cluster, cluster_template,
                        max_batch_size, nodegroup, rollback=False):
        LOG.debug('cluster_conductor cluster_upgrade')

        # osc = clients.OpenStackClients(context)
        allow_update_status = (
            fields.ClusterStatus.CREATE_COMPLETE,
            fields.ClusterStatus.UPDATE_COMPLETE,
            fields.ClusterStatus.RESUME_COMPLETE,
            fields.ClusterStatus.RESTORE_COMPLETE,
            fields.ClusterStatus.ROLLBACK_COMPLETE,
            fields.ClusterStatus.SNAPSHOT_COMPLETE,
            fields.ClusterStatus.CHECK_COMPLETE,
            fields.ClusterStatus.ADOPT_COMPLETE,
            fields.ClusterStatus.UPDATE_FAILED,
            # Allow recovery from a failed rollback (e.g. a migration update
            # that aborted then could not roll back) by retrying the upgrade.
            fields.ClusterStatus.ROLLBACK_FAILED,
        )
        if cluster.status not in allow_update_status:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_FAILURE,
                cluster)
            reason = _('Upgrading a cluster when status is '
                       '"%s"') % cluster.status
            # Collect failed Heat resources to give the user actionable info.
            failed_details = self._collect_heat_failed_resources(
                context, cluster)
            if failed_details:
                reason = _('%(reason)s. Failed stack resources: '
                           '%(details)s. Delete and recreate the cluster, '
                           'or resolve the failed resources manually before '
                           'retrying.') % {'reason': reason,
                                           'details': failed_details}
            raise exception.NotSupported(operation=reason)

        # Get driver - use nodegroup's cluster_template_id if available for non-default nodegroups
        if (nodegroup and not nodegroup.is_default and 
            nodegroup.labels and 'cluster_template_id' in nodegroup.labels):
            # Use the nodegroup's specific cluster template to get the driver
            ng_cluster_template_id = nodegroup.labels['cluster_template_id']
            current_ct = conductor_utils.retrieve_ct_by_name_or_uuid(context, ng_cluster_template_id)
            ct = current_ct
        else:
            # Use the cluster's default template
            current_ct = conductor_utils.retrieve_cluster_template(context, cluster)
            ct = current_ct
        
        # Validate that the new cluster template has the same driver type
        new_ct = cluster_template
        if ((current_ct.server_type, current_ct.cluster_distro, current_ct.coe) != 
            (new_ct.server_type, new_ct.cluster_distro, new_ct.coe)):
            raise exception.InvalidParameterValue(
                "Driver change during upgrade is not supported. "
                f"Current driver: ({current_ct.server_type}, {current_ct.cluster_distro}, {current_ct.coe}), "
                f"New driver: ({new_ct.server_type}, {new_ct.cluster_distro}, {new_ct.coe})")
        
        cluster_driver = driver.Driver.get_driver(ct.server_type,
                                                  ct.cluster_distro,
                                                  ct.coe)

        # Heal a broken/missing Keystone trust before the Heat update. A trust
        # whose trustor (e.g. a disabled/deleted OIDC user) was removed is gone
        # for good; recreate it with the current operator as trustor so the new
        # trust_id flows through heat-params into the node cloud.conf and the
        # in-cluster OCCM / CSI / auto-healer stop getting 403s.
        #
        # This is strictly best-effort and MUST NOT block the upgrade. The heal
        # makes synchronous Keystone calls (read the trust as trustee, re-grant
        # roles); if Keystone is slow or a call stalls, a plain try/except would
        # not help because a hung request never raises -- it just blocks this
        # greenthread forever, so driver.upgrade_cluster never runs and the
        # nodes never get triggered. Bound the whole heal with a hard timeout so
        # the upgrade always proceeds.
        heal_timeout = CONF.trust.heal_timeout
        if heal_timeout > 0:
            try:
                with eventlet.Timeout(heal_timeout):
                    trust_manager.ensure_trust(
                        clients.OpenStackClients(context), context, cluster)
            except eventlet.Timeout:
                LOG.warning(
                    'Pre-upgrade trust heal exceeded %ss for cluster %s; '
                    'continuing with the upgrade', heal_timeout, cluster.uuid)
            except Exception:
                LOG.exception(
                    'Pre-upgrade trust heal failed for cluster %s; continuing',
                    cluster.uuid)

        # Upgrade cluster

        try:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_PENDING,
                cluster)
            cluster_driver.upgrade_cluster(context, cluster, cluster_template,
                                           max_batch_size, nodegroup, rollback)
            cluster.status = fields.ClusterStatus.UPDATE_IN_PROGRESS
            nodegroup.status = fields.ClusterStatus.UPDATE_IN_PROGRESS
            cluster.status_reason = None
            if (cluster.labels != wtypes.Unset and cluster.labels is not None
              and 'min_node_count' in cluster.labels):
                nodegroup.min_node_count = cluster.labels['min_node_count']
            if (cluster.labels != wtypes.Unset and cluster.labels is not None
              and 'max_node_count' in cluster.labels):
                nodegroup.max_node_count = cluster.labels['max_node_count']
        except Exception as e:
            cluster.status = fields.ClusterStatus.UPDATE_FAILED
            cluster.status_reason = six.text_type(e)
            cluster.save()
            nodegroup.status = fields.ClusterStatus.UPDATE_FAILED
            nodegroup.status_reason = six.text_type(e)
            nodegroup.save()
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_FAILURE,
                cluster)
            if isinstance(e, exc.HTTPBadRequest):
                e = exception.InvalidParameterValue(message=six.text_type(e))
                raise e
            raise

        nodegroup.save()
        cluster.save()
        return cluster
