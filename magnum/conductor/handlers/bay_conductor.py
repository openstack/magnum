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

import uuid

from heatclient.common import template_utils
from heatclient import exc
from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import loopingcall
import six

from magnum.common import clients
from magnum.common import exception
from magnum.common import short_id
from magnum.conductor.handlers.common import cert_manager
from magnum.conductor import scale_manager
from magnum.conductor.template_definition import TemplateDefinition as TDef
from magnum.conductor import utils as conductor_utils
from magnum.i18n import _
from magnum.i18n import _LE
from magnum.i18n import _LI
from magnum import objects
from magnum.objects.fields import BayStatus as bay_status


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
               help=('The length of time to let bay creation continue.  This '
                     'interval is in minutes.  The default is no timeout.'))
]

docker_registry_opts = [
    cfg.StrOpt('trustee_user_id',
               default=None,
               help='User id of the trustee'),
    cfg.ListOpt('trust_roles',
                default=['registry_user'],
                help='The roles which are delegated to the trustee '
                'by the trustor.')
]

CONF = cfg.CONF
CONF.register_opts(bay_heat_opts, group='bay_heat')
CONF.register_opts(docker_registry_opts, 'docker_registry')

LOG = logging.getLogger(__name__)


def _extract_template_definition(context, bay, scale_manager=None):
    baymodel = conductor_utils.retrieve_baymodel(context, bay)
    cluster_distro = baymodel.cluster_distro
    cluster_coe = baymodel.coe
    cluster_server_type = baymodel.server_type
    definition = TDef.get_template_definition(cluster_server_type,
                                              cluster_distro,
                                              cluster_coe)
    return definition.extract_definition(context, baymodel, bay,
                                         scale_manager=scale_manager)


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


def _update_stack(context, osc, bay, scale_manager=None):
    template_path, heat_params = _extract_template_definition(
        context, bay, scale_manager=scale_manager)

    tpl_files, template = template_utils.get_template_contents(template_path)
    fields = {
        'parameters': heat_params,
        'template': template,
        'files': dict(list(tpl_files.items()))
    }

    return osc.heat().stacks.update(bay.stack_id, **fields)


class Handler(object):

    def __init__(self):
        super(Handler, self).__init__()

    # Bay Operations

    def bay_create(self, context, bay, bay_create_timeout):
        LOG.debug('bay_heat bay_create')

        osc = clients.OpenStackClients(context)

        baymodel = objects.BayModel.get_by_uuid(context,
                                                bay.baymodel_id)
        if baymodel.registry_enabled:
            trust = osc.keystone().create_trust(
                CONF.docker_registry.trustee_user_id,
                CONF.docker_registry.trust_roles)
            bay.registry_trust_id = trust.id

        try:
            # Generate certificate and set the cert reference to bay
            bay.uuid = uuid.uuid4()
            cert_manager.generate_certificates_to_bay(bay)
            created_stack = _create_stack(context, osc, bay,
                                          bay_create_timeout)
        except exc.HTTPBadRequest as e:
            cert_manager.delete_certificates_from_bay(bay)
            raise exception.InvalidParameterValue(message=six.text_type(e))
        except Exception:
            raise

        bay.stack_id = created_stack['stack']['id']
        bay.create()

        self._poll_and_check(osc, bay)

        return bay

    def bay_update(self, context, bay):
        LOG.debug('bay_heat bay_update')

        osc = clients.OpenStackClients(context)
        stack = osc.heat().stacks.get(bay.stack_id)
        allow_update_status = (
            bay_status.CREATE_COMPLETE,
            bay_status.UPDATE_COMPLETE,
            bay_status.RESUME_COMPLETE,
            bay_status.RESTORE_COMPLETE,
            bay_status.ROLLBACK_COMPLETE,
            bay_status.SNAPSHOT_COMPLETE,
            bay_status.CHECK_COMPLETE,
            bay_status.ADOPT_COMPLETE
        )
        if stack.stack_status not in allow_update_status:
            operation = _('Updating a bay when stack status is '
                          '"%s"') % stack.stack_status
            raise exception.NotSupported(operation=operation)

        delta = bay.obj_what_changed()
        if not delta:
            return bay

        manager = scale_manager.ScaleManager(context, osc, bay)

        _update_stack(context, osc, bay, manager)
        self._poll_and_check(osc, bay)

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
        except exc.HTTPNotFound:
            LOG.info(_LI('The stack %s was not be found during bay'
                         ' deletion.'), stack_id)
            try:
                cert_manager.delete_certificates_from_bay(bay)
                bay.destroy()
            except exception.BayNotFound:
                LOG.info(_LI('The bay %s has been deleted by others.'), uuid)
            return None
        except Exception:
            raise

        osc.keystone().delete_trust(bay.registry_trust_id)
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
        self.baymodel = conductor_utils.retrieve_baymodel(self.context, bay)
        self.template_def = TDef.get_template_definition(
            self.baymodel.server_type,
            self.baymodel.cluster_distro, self.baymodel.coe)

    def poll_and_check(self):
        # TODO(yuanying): temporary implementation to update api_address,
        # node_addresses and bay status
        stack = self.openstack_client.heat().stacks.get(self.bay.stack_id)
        self.attempts += 1
        # poll_and_check is detached and polling long time to check status,
        # so another user/client can call delete bay/stack.
        if stack.stack_status == bay_status.DELETE_COMPLETE:
            self._delete_complete()
            raise loopingcall.LoopingCallDone()

        if stack.stack_status in (bay_status.CREATE_COMPLETE,
                                  bay_status.UPDATE_COMPLETE):
            self._sync_bay_and_template_status(stack)
            raise loopingcall.LoopingCallDone()
        elif stack.stack_status != self.bay.status:
            self._sync_bay_status(stack)

        if stack.stack_status in (bay_status.CREATE_FAILED,
                                  bay_status.DELETE_FAILED,
                                  bay_status.UPDATE_FAILED):
            self._sync_bay_and_template_status(stack)
            self._bay_failed(stack)
            raise loopingcall.LoopingCallDone()
        # only check max attempts when the stack is being created when
        # the timeout hasn't been set. If the timeout has been set then
        # the loop will end when the stack completes or the timeout occurs
        if stack.stack_status == bay_status.CREATE_IN_PROGRESS:
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

    def _delete_complete(self):
        LOG.info(_LI('Bay has been deleted, stack_id: %s')
                 % self.bay.stack_id)
        try:
            cert_manager.delete_certificates_from_bay(self.bay)
            self.bay.destroy()
        except exception.BayNotFound:
            LOG.info(_LI('The bay %s has been deleted by others.')
                     % self.bay.uuid)

    def _sync_bay_status(self, stack):
        self.bay.status = stack.stack_status
        self.bay.status_reason = stack.stack_status_reason
        stack_nc_param = self.template_def.get_heat_param(
            bay_attr='node_count')
        self.bay.node_count = stack.parameters[stack_nc_param]
        self.bay.save()

    def _sync_bay_and_template_status(self, stack):
        self.template_def.update_outputs(stack, self.baymodel, self.bay)
        self._sync_bay_status(stack)

    def _bay_failed(self, stack):
        LOG.error(_LE('Bay error, stack status: %(bay_status)s, '
                      'stack_id: %(stack_id)s, '
                      'reason: %(reason)s') %
                  {'bay_status': stack.stack_status,
                   'stack_id': self.bay.stack_id,
                   'reason': self.bay.status_reason})
