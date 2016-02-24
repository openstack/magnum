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
from oslo_service import periodic_task
import six

from magnum.common import clients
from magnum.common import context
from magnum.common import exception
from magnum.common import rpc
from magnum.conductor import monitors
from magnum.i18n import _
from magnum.i18n import _LI
from magnum.i18n import _LW
from magnum import objects
from magnum.objects.fields import BayStatus as bay_status


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
    def sync_bay_status(self, ctx):
        try:
            LOG.debug('Starting to sync up bay status')
            osc = clients.OpenStackClients(ctx)
            status = [bay_status.CREATE_IN_PROGRESS,
                      bay_status.UPDATE_IN_PROGRESS,
                      bay_status.DELETE_IN_PROGRESS]
            filters = {'status': status}
            bays = objects.Bay.list(ctx, filters=filters)
            if not bays:
                return
            sid_to_bay_mapping = {bay.stack_id: bay for bay in bays}
            bay_stack_ids = sid_to_bay_mapping.keys()

            stacks = osc.heat().stacks.list(global_tenant=True,
                                            filters={'id': bay_stack_ids})
            sid_to_stack_mapping = {s.id: s for s in stacks}

            # intersection of bays magnum has and heat has
            for sid in (six.viewkeys(sid_to_bay_mapping) &
                        six.viewkeys(sid_to_stack_mapping)):
                stack = sid_to_stack_mapping[sid]
                bay = sid_to_bay_mapping[sid]
                self._sync_existing_bay(bay, stack)

            # the stacks that magnum has but heat doesn't have
            for sid in (six.viewkeys(sid_to_bay_mapping) -
                        six.viewkeys(sid_to_stack_mapping)):
                bay = sid_to_bay_mapping[sid]
                self._sync_missing_heat_stack(bay)

        except Exception as e:
            LOG.warning(_LW(
                "Ignore error [%s] when syncing up bay status."
            ), e, exc_info=True)

    def _sync_existing_bay(self, bay, stack):
        if bay.status != stack.stack_status:
            old_status = bay.status
            bay.status = stack.stack_status
            bay.status_reason = stack.stack_status_reason
            bay.save()
            LOG.info(_LI("Sync up bay with id %(id)s from "
                         "%(old_status)s to %(status)s."),
                     {'id': bay.id, 'old_status': old_status,
                      'status': bay.status})

    def _sync_missing_heat_stack(self, bay):
        if bay.status == bay_status.DELETE_IN_PROGRESS:
            self._sync_deleted_stack(bay)
        elif bay.status == bay_status.CREATE_IN_PROGRESS:
            self._sync_missing_stack(bay, bay_status.CREATE_FAILED)
        elif bay.status == bay_status.UPDATE_IN_PROGRESS:
            self._sync_missing_stack(bay, bay_status.UPDATE_FAILED)

    def _sync_deleted_stack(self, bay):
        try:
            bay.destroy()
        except exception.BayNotFound:
            LOG.info(_LI('The bay %s has been deleted by others.'), bay.uuid)
        else:
            LOG.info(_LI("Bay with id %(id)s not found in heat "
                         "with stack id %(sid)s, with status_reason: "
                         "%(reason)."), {'id': bay.id, 'sid': bay.stack_id,
                                         'reason': bay.status_reason})

    def _sync_missing_stack(self, bay, new_status):
        bay.status = new_status
        bay.status_reason = _("Stack with id %s not found in "
                              "Heat.") % bay.stack_id
        bay.save()
        LOG.info(_LI("Bay with id %(id)s has been set to "
                     "%(status)s due to stack with id %(sid)s "
                     "not found in Heat."),
                 {'id': bay.id, 'status': bay.status,
                  'sid': bay.stack_id})

    @periodic_task.periodic_task(run_immediately=True)
    @set_context
    def _send_bay_metrics(self, ctx):
        LOG.debug('Starting to send bay metrics')
        for bay in objects.Bay.list(ctx):
            if bay.status not in [bay_status.CREATE_COMPLETE,
                                  bay_status.UPDATE_COMPLETE]:
                continue

            monitor = monitors.create_monitor(ctx, bay)
            if monitor is None:
                continue

            try:
                monitor.pull_data()
            except Exception as e:
                LOG.warning(_LW("Skip pulling data from bay %(bay)s due to "
                                "error: %(e)s"),
                            {'e': e, 'bay': bay.uuid}, exc_info=True)
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
                           user_id=bay.user_id,
                           project_id=bay.project_id,
                           resource_id=bay.uuid)
            LOG.debug("About to send notification: '%s'", message)
            self.notifier.info(ctx, "magnum.bay.metrics.update",
                               message)


def setup(conf, tg):
    pt = MagnumPeriodicTasks(conf)
    tg.add_dynamic_timer(
        pt.run_periodic_tasks,
        periodic_interval_max=conf.periodic_interval_max,
        context=None)
