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

from oslo.config import cfg

from magnum.common import heat
from magnum import objects
from magnum.openstack.common._i18n import _
from magnum.openstack.common import log as logging


k8s_heat_opts = [
    cfg.StrOpt('template_path',
               default='/etc/magnum/templates/kubecluster.yaml',
               help=_(
                   'Location of template to build a k8s cluster. '))]

cfg.CONF.register_opts(k8s_heat_opts, group='k8s_heat')


LOG = logging.getLogger(__name__)


# These are the backend operations.  They are executed by the backend
# service.  API calls via AMQP (within the ReST API) trigger the handlers to
# be called.

class Handler(object):
    def __init__(self):
        super(Handler, self).__init__()

    # Bay Operations

    def bay_create(self, ctxt, bay):
        if bay.type is not 'k8s_heat':
            return

        LOG.debug('k8s_heat bay_create')
        # 'definition' and 'properties' field are needed.

        # stack_name is unique on each tenant.
        stack_name = bay.name
        # bay_definition is used for heat parameter
        # larsks/heat-kubernetes requires
        # 'ssh_key_name' and 'external_network_id'
        bay_definition = bay.definition

        heat_client = heat.get_client(ctxt)
        created_stack = heat_client.stacks.create(stack_name=stack_name,
                                    template=cfg.CONF.k8s_heat.template_path,
                                    parameters=bay_definition)
        stack_id = created_stack['stack']['id']
        bay.properties['stack_id'] = stack_id

        bay.create()

        # TODO(yuanying): create "node" object
        # using bay_definition['number_of_minions']

        return bay

    def bay_list(self, ctxt):
        LOG.debug('k8s_heat bay_list')
        return objects.Bay.list(ctxt)

    def bay_delete(self, ctxt, uuid):
        # if bay.type is not 'k8s_heat':
        #     return

        LOG.debug('k8s_heat bay_delete')
        bay = objects.Bay.get_by_uuid(ctxt, uuid)
        stack_id = bay.properties['stack_id']
        heat.stacks.delete(stack_id)
        bay.destroy()

        return None

    def bay_show(self, ctxt, uuid):
        # if bay.type is not 'k8s_heat':
        #     return

        LOG.debug('k8s_heat bay_show')
        bay = objects.Bay.get_by_uuid(ctxt, uuid)
        stack_id = bay.properties['stack_id']
        stack = heat.stacks.get(stack_id)

        if stack.status == 'COMPLETE':
            master_address = stack['outputs'][0]['output_value']
            minion_addresses = stack['outputs'][2]['output_value']
            bay.properties['master_address'] = master_address
            bay.properties['minion_addresses'] = minion_addresses
            bay.save()

        return bay