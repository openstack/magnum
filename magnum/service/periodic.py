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

from oslo_log import log
from oslo_service import loopingcall
from oslo_service import periodic_task

from pycadf import cadftaxonomy as taxonomy

from magnum.common import clients
from magnum.common import context
from magnum.common import exception
from magnum.common import profiler
from magnum.common import rpc
from magnum.conductor.handlers.common import cert_manager
from magnum.conductor.handlers.common import trust_manager
from magnum.conductor import monitors
from magnum.conductor import utils as conductor_utils
import magnum.conf
from magnum.drivers.common import driver
from magnum import objects


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


class ClusterUpdateJob(object):

    status_to_event = {
        objects.fields.ClusterStatus.DELETE_COMPLETE: taxonomy.ACTION_DELETE,
        objects.fields.ClusterStatus.CREATE_COMPLETE: taxonomy.ACTION_CREATE,
        objects.fields.ClusterStatus.UPDATE_COMPLETE: taxonomy.ACTION_UPDATE,
        objects.fields.ClusterStatus.ROLLBACK_COMPLETE: taxonomy.ACTION_UPDATE,
        objects.fields.ClusterStatus.CREATE_FAILED: taxonomy.ACTION_CREATE,
        objects.fields.ClusterStatus.DELETE_FAILED: taxonomy.ACTION_DELETE,
        objects.fields.ClusterStatus.UPDATE_FAILED: taxonomy.ACTION_UPDATE,
        objects.fields.ClusterStatus.ROLLBACK_FAILED: taxonomy.ACTION_UPDATE
    }

    def __init__(self, ctx, cluster):
        self.ctx = ctx
        self.cluster = cluster

    def update_status(self):
        LOG.debug("Updating status for cluster %s", self.cluster.id)
        # get the driver for the cluster
        cdriver = driver.Driver.get_driver_for_cluster(self.ctx, self.cluster)
        # ask the driver to sync status
        try:
            cdriver.update_cluster_status(self.ctx, self.cluster)
        except exception.AuthorizationFailure as e:
            trust_ex = ("Could not find trust: %s" % self.cluster.trust_id)
            # Try to use admin context if trust not found.
            # This will make sure even with trust got deleted out side of
            # Magnum, we still be able to check cluster status
            if trust_ex in str(e):
                cdriver.update_cluster_status(
                    self.ctx, self.cluster, use_admin_ctx=True)
            else:
                raise

        LOG.debug("Status for cluster %s updated to %s (%s)",
                  self.cluster.id, self.cluster.status,
                  self.cluster.status_reason)
        # status update notifications
        if self.cluster.status.endswith("_COMPLETE"):
            conductor_utils.notify_about_cluster_operation(
                self.ctx, self.status_to_event[self.cluster.status],
                taxonomy.OUTCOME_SUCCESS, self.cluster)
        if self.cluster.status.endswith("_FAILED"):
            conductor_utils.notify_about_cluster_operation(
                self.ctx, self.status_to_event[self.cluster.status],
                taxonomy.OUTCOME_FAILURE, self.cluster)
        # if we're done with it, delete it
        if self.cluster.status == objects.fields.ClusterStatus.DELETE_COMPLETE:
            # Clean up trusts and certificates, if they still exist.
            os_client = clients.OpenStackClients(self.ctx)
            LOG.debug("Calling delete_trustee_and_trusts from periodic "
                      "DELETE_COMPLETE")
            trust_manager.delete_trustee_and_trust(os_client, self.ctx,
                                                   self.cluster)
            cert_manager.delete_certificates_from_cluster(self.cluster,
                                                          context=self.ctx)
            # delete all the nodegroups that belong to this cluster
            for ng in objects.NodeGroup.list(self.ctx, self.cluster.uuid):
                ng.destroy()
            self.cluster.destroy()
        # end the "loop"
        raise loopingcall.LoopingCallDone()


class ClusterHealthUpdateJob(object):

    def __init__(self, ctx, cluster):
        self.ctx = ctx
        self.cluster = cluster

    def _update_health_status(self):
        monitor = monitors.create_monitor(self.ctx, self.cluster)
        if monitor is None:
            return

        try:
            monitor.poll_health_status()
        except Exception as e:
            LOG.warning(
                "Skip pulling data from cluster %(cluster)s due to "
                "error: %(e)s",
                {'e': e, 'cluster': self.cluster.uuid}, exc_info=True)
            # TODO(flwang): Should we mark this cluster's health status as
            # UNKNOWN if Magnum failed to pull data from the cluster? Because
            # that basically means the k8s API doesn't work at that moment.
            return

        if monitor.data.get('health_status'):
            self.cluster.health_status = monitor.data.get('health_status')
            self.cluster.health_status_reason = monitor.data.get(
                'health_status_reason')
            self.cluster.save()

    def update_health_status(self):
        LOG.debug("Updating health status for cluster %s", self.cluster.id)
        self._update_health_status()
        LOG.debug("Status for cluster %s updated to %s (%s)",
                  self.cluster.id, self.cluster.health_status,
                  self.cluster.health_status_reason)
        # TODO(flwang): Health status update notifications?
        # end the "loop"
        raise loopingcall.LoopingCallDone()


@profiler.trace_cls("rpc")
class MagnumPeriodicTasks(periodic_task.PeriodicTasks):
    """Magnum periodic Task class

    Any periodic task job need to be added into this class

    NOTE(suro-patz):
    - oslo_service.periodic_task runs tasks protected within try/catch
      block, with default raise_on_error as 'False', in run_periodic_tasks(),
      which ensures the process does not die, even if a task encounters an
      Exception.
    - The periodic tasks here does not necessarily need another
      try/catch block. The present try/catch block here helps putting
      magnum-periodic-task-specific log/error message.

    """

    def __init__(self, conf):
        super(MagnumPeriodicTasks, self).__init__(conf)
        self.notifier = rpc.get_notifier()

    @periodic_task.periodic_task(spacing=10, run_immediately=True)
    @set_context
    def sync_cluster_status(self, ctx):
        try:
            LOG.debug('Starting to sync up cluster status')

            # get all the clusters that are IN_PROGRESS
            status = [objects.fields.ClusterStatus.CREATE_IN_PROGRESS,
                      objects.fields.ClusterStatus.UPDATE_IN_PROGRESS,
                      objects.fields.ClusterStatus.DELETE_IN_PROGRESS,
                      objects.fields.ClusterStatus.ROLLBACK_IN_PROGRESS]
            filters = {'status': status}
            clusters = objects.Cluster.list(ctx, filters=filters)
            if not clusters:
                return

            # synchronize with underlying orchestration
            for cluster in clusters:
                job = ClusterUpdateJob(ctx, cluster)
                # though this call isn't really looping, we use this
                # abstraction anyway to avoid dealing directly with eventlet
                # hooey
                lc = loopingcall.FixedIntervalLoopingCall(f=job.update_status)
                lc.start(1, stop_on_exception=True)

        except Exception as e:
            LOG.warning(
                "Ignore error [%s] when syncing up cluster status.",
                e, exc_info=True)

    @periodic_task.periodic_task(
        spacing=CONF.kubernetes.health_polling_interval,
        run_immediately=True)
    @set_context
    def sync_cluster_health_status(self, ctx):
        try:
            LOG.debug('Starting to sync up cluster health status')

            status = [objects.fields.ClusterStatus.CREATE_COMPLETE,
                      objects.fields.ClusterStatus.UPDATE_COMPLETE,
                      objects.fields.ClusterStatus.UPDATE_IN_PROGRESS,
                      objects.fields.ClusterStatus.ROLLBACK_IN_PROGRESS]
            filters = {'status': status}
            clusters = objects.Cluster.list(ctx, filters=filters)
            if not clusters:
                return

            # synchronize using native COE API
            for cluster in clusters:
                job = ClusterHealthUpdateJob(ctx, cluster)
                # though this call isn't really looping, we use this
                # abstraction anyway to avoid dealing directly with eventlet
                # hooey
                lc = loopingcall.FixedIntervalLoopingCall(
                    f=job.update_health_status)
                lc.start(1, stop_on_exception=True)

        except Exception as e:
            LOG.warning(
                "Ignore error [%s] when syncing up cluster status.",
                e, exc_info=True)


def setup(conf, tg):
    pt = MagnumPeriodicTasks(conf)
    tg.add_dynamic_timer(
        pt.run_periodic_tasks,
        periodic_interval_max=conf.periodic_interval_max,
        context=None)
