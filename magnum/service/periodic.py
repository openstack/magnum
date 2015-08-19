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
import six

from oslo_log import log
from oslo_service import periodic_task
from oslo_service import threadgroup

from magnum.common import clients
from magnum.common import context
from magnum.common import exception
from magnum.i18n import _LI
from magnum.i18n import _LW
from magnum import objects
from magnum.objects.bay import Status as bay_status


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
    '''
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

            for sid in (six.viewkeys(sid_to_bay_mapping) &
                        six.viewkeys(sid_to_stack_mapping)):
                stack = sid_to_stack_mapping[sid]
                bay = sid_to_bay_mapping[sid]
                if bay.status != stack.stack_status:
                    old_status = bay.status
                    bay.status = stack.stack_status
                    bay.save()
                    LOG.info(_LI("Sync up bay with id %(id)s from "
                                 "%(old_status)s to %(status)s."),
                             {'id': bay.id, 'old_status': old_status,
                              'status': bay.status})

            for sid in (six.viewkeys(sid_to_bay_mapping) -
                        six.viewkeys(sid_to_stack_mapping)):
                bay = sid_to_bay_mapping[sid]
                if bay.status == bay_status.DELETE_IN_PROGRESS:
                    try:
                        bay.destroy()
                    except exception.BayNotFound:
                        LOG.info(_LI('The bay %s has been deleted by others.')
                                 % bay.uuid)
                    LOG.info(_LI("Bay with id %(id)s has been deleted due "
                                 "to stack with id %(sid)s not found in "
                                 "Heat."),
                             {'id': bay.id, 'sid': sid})
                elif bay.status == bay_status.CREATE_IN_PROGRESS:
                    bay.status = bay_status.CREATE_FAILED
                    bay.save()
                    LOG.info(_LI("Bay with id %(id)s has been set to "
                                 "%(status)s due to stack with id %(sid)s "
                                 "not found in Heat."),
                             {'id': bay.id, 'status': bay.status,
                              'sid': sid})
                elif bay.status == bay_status.UPDATE_IN_PROGRESS:
                    bay.status = bay_status.UPDATE_FAILED
                    bay.save()
                    LOG.info(_LI("Bay with id %(id)s has been set to "
                                 "%(status)s due to stack with id %(sid)s "
                                 "not found in Heat."),
                             {'id': bay.id, 'status': bay.status,
                              'sid': sid})

        except Exception as e:
            LOG.warn(_LW("Ignore error [%s] when syncing up bay status."), e,
                     exc_info=True)


def setup(conf):
    tg = threadgroup.ThreadGroup()
    pt = MagnumPeriodicTasks(conf)
    tg.add_dynamic_timer(
        pt.run_periodic_tasks,
        periodic_interval_max=conf.periodic_interval_max,
        context=None)
    return tg
