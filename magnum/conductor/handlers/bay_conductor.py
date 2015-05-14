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

from heatclient.common import template_utils
from heatclient import exc
from oslo_config import cfg

from magnum.common import clients
from magnum.common import exception
from magnum.common import short_id
from magnum.conductor.template_definition import TemplateDefinition as TDef
from magnum.i18n import _
from magnum.i18n import _LE
from magnum.i18n import _LI
from magnum import objects
from magnum.openstack.common import log as logging
from magnum.openstack.common import loopingcall


bay_heat_opts = [
    cfg.IntOpt('max_attempts',
               default=2000,
               help=('Number of attempts to query the Heat stack for '
                     'finding out the status of the created stack and '
                     'getting template outputs.  This value is ignored '
                     'during bay creation if timeout is set as the poll '
                     'will continue until bay creation either ends '
                     'or times out.')),
    cfg.IntOpt('wait_interval',
               default=1,
               help=('Sleep time interval between two attempts of querying '
                     'the Heat stack.  This interval is in seconds.')),
    cfg.IntOpt('bay_create_timeout',
               default=None,
               help=('The length of time to let bay creation continue.  This '
                    'interval is in minutes.  The default is no timeout.'))
]

cfg.CONF.register_opts(bay_heat_opts, group='bay_heat')


LOG = logging.getLogger(__name__)


def _get_baymodel(context, bay):
    baymodel = objects.BayModel.get_by_uuid(context, bay.baymodel_id)
    return baymodel


def _extract_template_definition(context, bay):
    baymodel = _get_baymodel(context, bay)
    cluster_distro = baymodel.cluster_distro
    cluster_coe = baymodel.coe
    definition = TDef.get_template_definition('vm', cluster_distro,
                                              cluster_coe)
    return definition.extract_definition(baymodel, bay)


def _create_stack(context, osc, bay, bay_create_timeout):
    template_path, heat_params = _extract_template_definition(context, bay)

    tpl_files, template = template_utils.get_template_contents(template_path)
    # Make sure no duplicate stack name
    stack_name = '%s-%s' % (bay.name, short_id.generate_id())
    if bay_create_timeout:
        heat_timeout = bay_create_timeout
    elif bay_create_timeout == 0:
        heat_timeout = None
    else:
        # no bay_create_timeout value was passed in to the request
        # so falling back on configuration file value
        heat_timeout = cfg.CONF.bay_heat.bay_create_timeout
    fields = {
        'stack_name': stack_name,
        'parameters': heat_params,
        'template': template,
        'files': dict(list(tpl_files.items())),
        'timeout_mins': heat_timeout
    }
    created_stack = osc.heat().stacks.create(**fields)

    return created_stack


def _update_stack(context, osc, bay):
    template_path, heat_params = _extract_template_definition(context, bay)

    tpl_files, template = template_utils.get_template_contents(template_path)
    fields = {
        'parameters': heat_params,
        'template': template,
        'files': dict(list(tpl_files.items()))
    }

    return osc.heat().stacks.update(bay.stack_id, **fields)


def _update_stack_outputs(context, stack, bay):
    baymodel = _get_baymodel(context, bay)
    cluster_distro = baymodel.cluster_distro
    cluster_coe = baymodel.coe
    definition = TDef.get_template_definition('vm', cluster_distro,
                                              cluster_coe)
    return definition.update_outputs(stack, bay)


class Handler(object):
    def __init__(self):
        super(Handler, self).__init__()

    # Bay Operations

    def bay_create(self, context, bay, bay_create_timeout):
        LOG.debug('bay_heat bay_create')

        osc = clients.OpenStackClients(context)

        try:
            created_stack = _create_stack(context, osc, bay,
                                          bay_create_timeout)
        except Exception as e:
            if isinstance(e, exc.HTTPBadRequest):
                raise exception.InvalidParameterValue(message=str(e))
            else:
                raise
        bay.stack_id = created_stack['stack']['id']
        bay.create()

        self._poll_and_check(osc, bay)

        return bay

    def bay_update(self, context, bay):
        LOG.debug('bay_heat bay_update')

        osc = clients.OpenStackClients(context)
        stack = osc.heat().stacks.get(bay.stack_id)
        if (stack.stack_status != 'CREATE_COMPLETE' and
            stack.stack_status != 'UPDATE_COMPLETE'):
            operation = _('Updating a bay when stack status is '
                          '"%s"') % stack.stack_status
            raise exception.NotSupported(operation=operation)

        delta = set(bay.obj_what_changed())
        if 'node_count' in delta:
            delta.remove('node_count')

            _update_stack(context, osc, bay)
            self._poll_and_check(osc, bay)

        if delta:
            raise exception.InvalidParameterValue(err=(
                "cannot change bay property(ies) %s." % ", ".join(delta)))

        bay.save()
        return bay

    def bay_delete(self, context, uuid):
        LOG.debug('bay_heat bay_delete')
        osc = clients.OpenStackClients(context)
        bay = objects.Bay.get_by_uuid(context, uuid)
        stack_id = bay.stack_id
        # NOTE(sdake): This will execute a stack_delete operation.  This will
        # Ignore HTTPNotFound exceptions (stack wasn't present).  In the case
        # that Heat couldn't find the stack representing the bay, likely a user
        # has deleted the stack outside the context of Magnum.  Therefore the
        # contents of the bay are forever lost.
        #
        # If the exception is unhandled, the original exception will be raised.
        try:
            osc.heat().stacks.delete(stack_id)
        except Exception as e:
            if isinstance(e, exc.HTTPNotFound):
                LOG.info(_LI('The stack %s was not be found during bay'
                             ' deletion.') % stack_id)
                bay.destroy()
                return None
            else:
                raise

        self._poll_and_check(osc, bay)

        return None

    def _poll_and_check(self, osc, bay):
        poller = HeatPoller(osc, bay)
        lc = loopingcall.FixedIntervalLoopingCall(f=poller.poll_and_check)
        lc.start(cfg.CONF.bay_heat.wait_interval, True)


class HeatPoller(object):

    def __init__(self, openstack_client, bay):
        self.openstack_client = openstack_client
        self.context = self.openstack_client.context
        self.bay = bay
        self.attempts = 0

    def poll_and_check(self):
        # TODO(yuanying): temporary implementation to update api_address,
        # node_addresses and bay status
        stack = self.openstack_client.heat().stacks.get(self.bay.stack_id)
        self.attempts += 1
        # poll_and_check is detached and polling long time to check status,
        # so another user/client can call delete bay/stack.
        if stack.stack_status == 'DELETE_COMPLETE':
            LOG.info(_LI('Bay has been deleted, stack_id: %s')
                          % self.bay.stack_id)
            self.bay.destroy()
            raise loopingcall.LoopingCallDone()
        if (stack.stack_status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']):
            _update_stack_outputs(self.context, stack, self.bay)

            self.bay.status = stack.stack_status
            self.bay.save()
            raise loopingcall.LoopingCallDone()
        elif stack.stack_status != self.bay.status:
            self.bay.status = stack.stack_status
            self.bay.save()
        if stack.stack_status == 'CREATE_FAILED':
            LOG.error(_LE('Unable to create bay, stack_id: %(stack_id)s, '
                          'reason: %(reason)s') %
                          {'stack_id': self.bay.stack_id,
                          'reason': stack.stack_status_reason})
            raise loopingcall.LoopingCallDone()
        if stack.stack_status == 'DELETE_FAILED':
            LOG.error(_LE('Unable to delete bay, stack_id: %(stack_id)s, '
                          'reason: %(reason)s') %
                          {'stack_id': self.bay.stack_id,
                          'reason': stack.stack_status_reason})
            raise loopingcall.LoopingCallDone()
        if stack.stack_status == 'UPDATE_FAILED':
            LOG.error(_LE('Unable to update bay, stack_id: %(stack_id)s, '
                          'reason: %(reason)s') %
                         {'stack_id': self.bay.stack_id,
                         'reason': stack.stack_status_reason})
            raise loopingcall.LoopingCallDone()
        # only check max attempts when the stack is being created when
        # the timeout hasn't been set. If the timeout has been set then
        # the loop will end when the stack completes or the timeout occurs
        if stack.stack_status == 'CREATE_IN_PROGRESS':
            if (stack.timeout_mins is None and
               self.attempts > cfg.CONF.bay_heat.max_attempts):
                LOG.error(_LE('Bay check exit after %(attempts)s attempts,'
                              'stack_id: %(id)s, stack_status: %(status)s') %
                              {'attempts': cfg.CONF.bay_heat.max_attempts,
                              'id': self.bay.stack_id,
                              'status': stack.stack_status})
                raise loopingcall.LoopingCallDone()
        else:
            if self.attempts > cfg.CONF.bay_heat.max_attempts:
                LOG.error(_LE('Bay check exit after %(attempts)s attempts,'
                              'stack_id: %(id)s, stack_status: %(status)s') %
                              {'attempts': cfg.CONF.bay_heat.max_attempts,
                              'id': self.bay.stack_id,
                              'status': stack.stack_status})
                raise loopingcall.LoopingCallDone()
