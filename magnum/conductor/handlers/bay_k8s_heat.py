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
from oslo.config import cfg

from magnum.common import clients
from magnum import objects
from magnum.openstack.common._i18n import _
from magnum.openstack.common import log as logging
from magnum.openstack.common import loopingcall


k8s_heat_opts = [
    cfg.StrOpt('template_path',
               default=
                   '/etc/magnum/templates/heat-kubernetes/kubecluster.yaml',
               help=_(
                   'Location of template to build a k8s cluster. ')),
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


def _extract_bay_definition(baymodel):
    bay_definition = {
        'ssh_key_name': baymodel.keypair_id,
        'external_network_id': baymodel.external_network_id,
        'apiserver_port': 8080
    }
    if baymodel.dns_nameserver:
        bay_definition['dns_nameserver'] = baymodel.dns_nameserver
    if baymodel.image_id:
        bay_definition['server_image'] = baymodel.image_id
    if baymodel.flavor_id:
        bay_definition['server_flavor'] = baymodel.flavor_id
    if baymodel.apiserver_port:
        bay_definition['apiserver_port'] = baymodel.apiserver_port

    return bay_definition


def _create_stack(ctxt, osc, bay):
    baymodel = objects.BayModel.get_by_uuid(ctxt, bay.baymodel_id)
    bay_definition = _extract_bay_definition(baymodel)

    if bay.node_count:
        bay_definition['number_of_minions'] = str(bay.node_count)

    tpl_files, template = template_utils.get_template_contents(
                                        cfg.CONF.k8s_heat.template_path)
    fields = {
        'stack_name': bay.name,
        'parameters': bay_definition,
        'template': template,
        'files': dict(list(tpl_files.items()))
    }
    created_stack = osc.heat().stacks.create(**fields)

    return created_stack


class Handler(object):
    def __init__(self):
        super(Handler, self).__init__()

    # Bay Operations

    def bay_create(self, ctxt, bay):
        LOG.debug('k8s_heat bay_create')

        osc = clients.OpenStackClients(ctxt)

        created_stack = _create_stack(ctxt, osc, bay)
        bay.stack_id = created_stack['stack']['id']
        bay.create()

        attempts_count = 0

        # TODO(yuanying): temporary implementation of updating master_address
        def poll_and_check():
            stack = osc.heat().stacks.get(bay.stack_id)
            if stack.stack_status == 'CREATE_COMPLETE':
                master_address = stack.outputs[0]['output_value']
                minion_addresses = stack.outputs[2]['output_value']
                bay.master_address = master_address
                bay.minions_address = minion_addresses
                bay.save()
                raise loopingcall.LoopingCallDone()
            # poll_and_check is detached and polling long time to check status,
            # so another user/client can call delete bay/stack.
            if stack.stack_status == 'DELETE_COMPLETE':
                LOG.info('Bay has been deleted, stack_id: %s' % bay.stack_id)
                raise loopingcall.LoopingCallDone()
            if ((stack.status == 'FAILED') or
                (attempts_count > cfg.CONF.k8s_heat.max_attempts)):
                # TODO(yuanying): update status to failed
                LOG.error('Unable to create bay, stack_id: %s' % bay.stack_id)
                osc.heat().stacks.delete(bay.stack_id)
                raise loopingcall.LoopingCallDone()

        lc = loopingcall.FixedIntervalLoopingCall(f=poll_and_check)
        lc.start(cfg.CONF.k8s_heat.wait_interval, True)

        return bay

    def bay_delete(self, ctxt, uuid):
        LOG.debug('k8s_heat bay_delete')
        osc = clients.OpenStackClients(ctxt)
        bay = objects.Bay.get_by_uuid(ctxt, uuid)
        stack_id = bay.stack_id
        osc.heat().stacks.delete(stack_id)
        bay.destroy()

        return None
