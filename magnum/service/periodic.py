# Copyright (c) 2015 Intel Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import functools

from heatclient import exc as heat_exc
from oslo_log import log
from oslo_service import periodic_task
import six

from magnum.common import clients
from magnum.common import context
from magnum.common import exception
from magnum.common import rpc
from magnum.conductor import monitors
import magnum.conf
from magnum.i18n import _
from magnum.i18n import _LI
from magnum.i18n import _LW
from magnum import objects
from magnum.objects import fields


CONF = magnum.conf.CONF
LOG = log.getLogger(__name__)


def set_context(func):
    @functools.wraps(func)
    def handler(self, ctx):
        ctx = context.make_admin_context(all_tenants=True)
        context.set_ctx(ctx)
        func(self, ctx)
        context.set_ctx(None)
    return handler


class MagnumPeriodicTasks(periodic_task.PeriodicTasks):
    '''Magnum periodic Task class

    Any periodic task job need to be added into this class

    NOTE(suro-patz):
    - oslo_service.periodic_task runs tasks protected within try/catch
      block, with default raise_on_error as 'False', in run_periodic_tasks(),
      which ensures the process does not die, even if a task encounters an
      Exception.
    - The periodic tasks here does not necessarily need another
      try/catch block. The present try/catch block here helps putting
      magnum-periodic-task-specific log/error message.

    '''

    def __init__(self, conf):
        super(MagnumPeriodicTasks, self).__init__(conf)
        self.notifier = rpc.get_notifier()

    @periodic_task.periodic_task(run_immediately=True)
    @set_context
    def sync_cluster_status(self, ctx):
        try:
            LOG.debug('Starting to sync up cluster status')
            osc = clients.OpenStackClients(ctx)
            status = [fields.ClusterStatus.CREATE_IN_PROGRESS,
                      fields.ClusterStatus.UPDATE_IN_PROGRESS,
                      fields.ClusterStatus.DELETE_IN_PROGRESS,
                      fields.ClusterStatus.ROLLBACK_IN_PROGRESS]
            filters = {'status': status}
            clusters = objects.Cluster.list(ctx, filters=filters)
            if not clusters:
                return
            sid_to_cluster_mapping = {cluster.stack_id:
                                      cluster for cluster in clusters}
            cluster_stack_ids = sid_to_cluster_mapping.keys()

            if CONF.periodic_global_stack_list:
                stacks = osc.heat().stacks.list(
                    global_tenant=True, filters={'id': cluster_stack_ids})
            else:
                ret = self._get_cluster_stacks(
                    clusters, sid_to_cluster_mapping, cluster_stack_ids)
                [stacks, clusters, cluster_stack_ids,
                 sid_to_cluster_mapping] = ret

            sid_to_stack_mapping = {s.id: s for s in stacks}

            # intersection of clusters magnum has and heat has
            for sid in (six.viewkeys(sid_to_cluster_mapping) &
                        six.viewkeys(sid_to_stack_mapping)):
                stack = sid_to_stack_mapping[sid]
                cluster = sid_to_cluster_mapping[sid]
                self._sync_existing_cluster(cluster, stack)

            # the stacks that magnum has but heat doesn't have
            for sid in (six.viewkeys(sid_to_cluster_mapping) -
                        six.viewkeys(sid_to_stack_mapping)):
                cluster = sid_to_cluster_mapping[sid]
                self._sync_missing_heat_stack(cluster)

        except Exception as e:
            LOG.warning(_LW(
                "Ignore error [%s] when syncing up cluster status."
            ), e, exc_info=True)

    def _get_cluster_stacks(
            self, clusters, sid_to_cluster_mapping, cluster_stack_ids):
        stacks = []

        _clusters = clusters
        _sid_to_cluster_mapping = sid_to_cluster_mapping
        _cluster_stack_ids = cluster_stack_ids

        for cluster in _clusters:
            try:
                # Create client with cluster's trustee user context
                bosc = clients.OpenStackClients(
                    context.make_cluster_context(cluster))
                stack = bosc.heat().stacks.get(cluster.stack_id)
                stacks.append(stack)
            # No need to do anything in this case
            except heat_exc.HTTPNotFound:
                pass
            except Exception as e:
                # Any other exception means we do not perform any
                # action on this cluster in the current sync run, so remove
                # it from all records.
                LOG.warning(
                    _LW("Exception while attempting to retrieve "
                        "Heat stack %(stack_id)s for cluster %(cluster_id)s. "
                        "Traceback follows."),
                    {'stack_id': cluster.stack_id, 'cluster_id': cluster.id})
                LOG.warning(e)
                _sid_to_cluster_mapping.pop(cluster.stack_id)
                _cluster_stack_ids.remove(cluster.stack_id)
                _clusters.remove(cluster)
        return [stacks, _clusters, _cluster_stack_ids, _sid_to_cluster_mapping]

    def _sync_existing_cluster(self, cluster, stack):
        if cluster.status != stack.stack_status:
            old_status = cluster.status
            cluster.status = stack.stack_status
            cluster.status_reason = stack.stack_status_reason
            cluster.save()
            LOG.info(_LI("Sync up cluster with id %(id)s from "
                         "%(old_status)s to %(status)s."),
                     {'id': cluster.id, 'old_status': old_status,
                      'status': cluster.status})

    def _sync_missing_heat_stack(self, cluster):
        if cluster.status == fields.ClusterStatus.DELETE_IN_PROGRESS:
            self._sync_deleted_stack(cluster)
        elif cluster.status == fields.ClusterStatus.CREATE_IN_PROGRESS:
            self._sync_missing_stack(cluster,
                                     fields.ClusterStatus.CREATE_FAILED)
        elif cluster.status == fields.ClusterStatus.UPDATE_IN_PROGRESS:
            self._sync_missing_stack(cluster,
                                     fields.ClusterStatus.UPDATE_FAILED)

    def _sync_deleted_stack(self, cluster):
        try:
            cluster.destroy()
        except exception.ClusterNotFound:
            LOG.info(_LI('The cluster %s has been deleted by others.'),
                     cluster.uuid)
        else:
            LOG.info(_LI("cluster with id %(id)s not found in heat "
                         "with stack id %(sid)s, with status_reason: "
                         "%(reason)s."), {'id': cluster.id,
                                          'sid': cluster.stack_id,
                                          'reason': cluster.status_reason})

    def _sync_missing_stack(self, cluster, new_status):
        cluster.status = new_status
        cluster.status_reason = _("Stack with id %s not found in "
                                  "Heat.") % cluster.stack_id
        cluster.save()
        LOG.info(_LI("Cluster with id %(id)s has been set to "
                     "%(status)s due to stack with id %(sid)s "
                     "not found in Heat."),
                 {'id': cluster.id, 'status': cluster.status,
                  'sid': cluster.stack_id})

    @periodic_task.periodic_task(run_immediately=True)
    @set_context
    def _send_cluster_metrics(self, ctx):
        LOG.debug('Starting to send cluster metrics')
        for cluster in objects.Cluster.list(ctx):
            if cluster.status not in [fields.ClusterStatus.CREATE_COMPLETE,
                                      fields.ClusterStatus.UPDATE_COMPLETE]:
                continue

            monitor = monitors.create_monitor(ctx, cluster)
            if monitor is None:
                continue

            try:
                monitor.pull_data()
            except Exception as e:
                LOG.warning(
                    _LW("Skip pulling data from cluster %(cluster)s due to "
                        "error: %(e)s"),
                    {'e': e, 'cluster': cluster.uuid}, exc_info=True)
                continue

            metrics = list()
            for name in monitor.get_metric_names():
                try:
                    metric = {
                        'name': name,
                        'value': monitor.compute_metric_value(name),
                        'unit': monitor.get_metric_unit(name),
                    }
                    metrics.append(metric)
                except Exception as e:
                    LOG.warning(_LW("Skip adding metric %(name)s due to "
                                    "error: %(e)s"),
                                {'e': e, 'name': name}, exc_info=True)

            message = dict(metrics=metrics,
                           user_id=cluster.user_id,
                           project_id=cluster.project_id,
                           resource_id=cluster.uuid)
            LOG.debug("About to send notification: '%s'", message)
            self.notifier.info(ctx, "magnum.cluster.metrics.update",
                               message)


def setup(conf, tg):
    pt = MagnumPeriodicTasks(conf)
    tg.add_dynamic_timer(
        pt.run_periodic_tasks,
        periodic_interval_max=conf.periodic_interval_max,
        context=None)
