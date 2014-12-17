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


k8s_heat_opts = [
    cfg.StrOpt('template_path',
               default=
                   '/etc/magnum/templates/heat-kubernetes/kubecluster.yaml',
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
        LOG.debug('k8s_heat bay_create')

        osc = clients.OpenStackClients(ctxt)

        # stack_name is unique on each tenant.
        stack_name = bay.name
        bay_model = objects.BayModel.get_by_uuid(ctxt, bay.baymodel_id)
        bay_definition = {
            'ssh_key_name': bay_model.keypair_id,
            'external_network_id': bay_model.external_network_id,
            'server_image': bay_model.image_id,
            'server_flavor': bay_model.flavor_id
        }
        tpl_files, template = template_utils.get_template_contents(
                                            cfg.CONF.k8s_heat.template_path)

        fields = {
            'stack_name': stack_name,
            'parameters': bay_definition,
            'template': template,
            'files': dict(list(tpl_files.items()))
        }
        created_stack = osc.heat().stacks.create(**fields)
        bay.stack_id = created_stack['stack']['id']

        bay.create()

        # TODO(yuanying): create "node" object
        # using bay_definition['number_of_minions']

        return bay

    def bay_delete(self, ctxt, uuid):
        LOG.debug('k8s_heat bay_delete')
        bay = objects.Bay.get_by_uuid(ctxt, uuid)
        bay.destroy()

        return None

    def bay_show(self, ctxt, uuid):
        LOG.debug('k8s_heat bay_show')
        bay = objects.Bay.get_by_uuid(ctxt, uuid)

        return bay
