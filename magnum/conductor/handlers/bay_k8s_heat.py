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

import requests
import uuid

from heatclient.common import template_utils
from heatclient import exc
from oslo_config import cfg

from magnum.common import clients
from magnum.common import exception
from magnum.common import paths
from magnum.common import short_id
from magnum import objects
from magnum.openstack.common._i18n import _
from magnum.openstack.common._i18n import _LE
from magnum.openstack.common._i18n import _LI
from magnum.openstack.common import log as logging
from magnum.openstack.common import loopingcall


k8s_heat_opts = [
    cfg.StrOpt('template_path',
               default=paths.basedir_def('templates/heat-kubernetes/'
                                         'kubecluster.yaml'),
               help=_(
                   'Location of template to build a k8s cluster. ')),
    cfg.StrOpt('cluster_type',
               default=None,
               help=_('Cluster types are fedora-atomic, coreos, ironic.')),
    cfg.StrOpt('discovery_token_url',
               default=None,
               help=_('coreos discovery token url.')),
    cfg.IntOpt('max_attempts',
               default=2000,
               help=('Number of attempts to query the Heat stack for '
                     'finding out the status of the created stack and '
                     'getting url of the DU created in the stack')),
    cfg.IntOpt('wait_interval',
               default=1,
               help=('Sleep time interval between two attempts of querying '
                     'the Heat stack. This interval is in seconds.')),
]

cfg.CONF.register_opts(k8s_heat_opts, group='k8s_heat')


LOG = logging.getLogger(__name__)


def _get_coreos_token(context):
    if cfg.CONF.k8s_heat.cluster_type == 'coreos':
        token = ""
        discovery_url = cfg.CONF.k8s_heat.discovery_token_url
        if discovery_url:
            coreos_token_url = requests.get(discovery_url)
            token = str(coreos_token_url.text.split('/')[3])
        else:
            token = uuid.uuid4().hex
        return token
    else:
        return None


def _extract_bay_definition(context, bay):
    baymodel = objects.BayModel.get_by_uuid(context, bay.baymodel_id)
    token = _get_coreos_token(context)
    bay_definition = {
        'ssh_key_name': baymodel.keypair_id,
        'external_network_id': baymodel.external_network_id,
    }
    if token is not None:
        bay_definition['token'] = token
    if baymodel.dns_nameserver:
        bay_definition['dns_nameserver'] = baymodel.dns_nameserver
    if baymodel.image_id:
        bay_definition['server_image'] = baymodel.image_id
    if baymodel.flavor_id:
        bay_definition['server_flavor'] = baymodel.flavor_id
    if baymodel.master_flavor_id:
        bay_definition['master_flavor'] = baymodel.master_flavor_id
    # TODO(yuanying): Add below lines if apiserver_port parameter is supported
    # if baymodel.apiserver_port:
    #     bay_definition['apiserver_port'] = baymodel.apiserver_port
    if bay.node_count is not None:
        bay_definition['number_of_minions'] = str(bay.node_count)
    if baymodel.docker_volume_size:
        bay_definition['docker_volume_size'] = baymodel.docker_volume_size
    if baymodel.fixed_network:
        bay_definition['fixed_network'] = baymodel.fixed_network
    if baymodel.ssh_authorized_key:
        bay_definition['ssh_authorized_key'] = baymodel.ssh_authorized_key

    return bay_definition


def _create_stack(context, osc, bay):
    bay_definition = _extract_bay_definition(context, bay)

    tpl_files, template = template_utils.get_template_contents(
                                        cfg.CONF.k8s_heat.template_path)
    # Make sure no duplicate stack name
    stack_name = '%s-%s' % (bay.name, short_id.generate_id())
    fields = {
        'stack_name': stack_name,
        'parameters': bay_definition,
        'template': template,
        'files': dict(list(tpl_files.items()))
    }
    created_stack = osc.heat().stacks.create(**fields)

    return created_stack


def _update_stack(context, osc, bay):
    bay_definition = _extract_bay_definition(context, bay)

    tpl_files, template = template_utils.get_template_contents(
                                        cfg.CONF.k8s_heat.template_path)
    fields = {
        'parameters': bay_definition,
        'template': template,
        'files': dict(list(tpl_files.items()))
    }

    return osc.heat().stacks.update(bay.stack_id, **fields)


def _parse_stack_outputs(outputs):
    parsed_outputs = {}

    for output in outputs:
        output_key = output["output_key"]
        output_value = output["output_value"]
        if output_key == "kube_minions_external":
            parsed_outputs["kube_minions_external"] = output_value
        if output_key == "kube_minions":
            parsed_outputs["kube_minions"] = output_value
        if output_key == "kube_master":
            parsed_outputs["kube_master"] = output_value

    return parsed_outputs


class Handler(object):
    def __init__(self):
        super(Handler, self).__init__()

    # Bay Operations

    def bay_create(self, context, bay):
        LOG.debug('k8s_heat bay_create')

        osc = clients.OpenStackClients(context)

        created_stack = _create_stack(context, osc, bay)
        bay.stack_id = created_stack['stack']['id']
        bay.create()

        self._poll_and_check(osc, bay)

        return bay

    def bay_update(self, context, bay):
        LOG.debug('k8s_heat bay_update')

        osc = clients.OpenStackClients(context)
        stack = osc.heat().stacks.get(bay.stack_id)
        if (stack.stack_status != 'CREATE_COMPLETE' and
            stack.stack_status != 'UPDATE_COMPLETE'):
            raise exception.MagnumException(_(
                "Cannot update stack with status: %s") % stack.stack_status)

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
        LOG.debug('k8s_heat bay_delete')
        osc = clients.OpenStackClients(context)
        bay = objects.Bay.get_by_uuid(context, uuid)
        stack_id = bay.stack_id
        # TODO(yuanying): handle stack status DELETE_IN_PROGRESS
        #
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
            else:
                raise
        # TODO(yuanying): bay.destroy will be triggered by stack status change.
        bay.destroy()

        return None

    def _poll_and_check(self, osc, bay):
        poller = HeatPoller(osc, bay)
        lc = loopingcall.FixedIntervalLoopingCall(f=poller.poll_and_check)
        lc.start(cfg.CONF.k8s_heat.wait_interval, True)


class HeatPoller(object):

    def __init__(self, openstack_client, bay):
        self.openstack_client = openstack_client
        self.bay = bay
        self.attempts = 0

    def poll_and_check(self):
        # TODO(yuanying): temporary implementation to update master_address,
        # minions_address and bay status
        stack = self.openstack_client.heat().stacks.get(self.bay.stack_id)
        self.attempts += 1
        if (stack.stack_status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']):
            parsed_outputs = _parse_stack_outputs(stack.outputs)
            self.bay.master_address = parsed_outputs["kube_master"]
            self.bay.minions_address = parsed_outputs["kube_minions_external"]
            self.bay.status = stack.stack_status
            self.bay.save()
            raise loopingcall.LoopingCallDone()
        elif stack.stack_status != self.bay.status:
            self.bay.status = stack.stack_status
            self.bay.save()
        # poll_and_check is detached and polling long time to check status,
        # so another user/client can call delete bay/stack.
        if stack.stack_status == 'DELETE_COMPLETE':
            LOG.info(_LI('Bay has been deleted, stack_id: %s')
                          % self.bay.stack_id)
            raise loopingcall.LoopingCallDone()
        if (stack.stack_status == 'FAILED' or
                self.attempts > cfg.CONF.k8s_heat.max_attempts):
            LOG.error(_LE('Unable to create bay, stack_id: %s')
                           % self.bay.stack_id)
            raise loopingcall.LoopingCallDone()
