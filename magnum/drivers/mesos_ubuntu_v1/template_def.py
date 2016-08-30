# Copyright 2016 Rackspace Inc. All rights reserved.
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
import os

from magnum.drivers.common import template_def


class UbuntuMesosTemplateDefinition(template_def.BaseTemplateDefinition):
    """Mesos template for Ubuntu VM."""

    provides = [
        {'server_type': 'vm', 'os': 'ubuntu', 'coe': 'mesos'},
    ]

    def __init__(self):
        super(UbuntuMesosTemplateDefinition, self).__init__()
        self.add_parameter('external_network',
                           baymodel_attr='external_network_id',
                           required=True)
        self.add_parameter('number_of_agents',
                           bay_attr='node_count')
        self.add_parameter('master_flavor',
                           baymodel_attr='master_flavor_id')
        self.add_parameter('agent_flavor',
                           baymodel_attr='flavor_id')
        self.add_parameter('cluster_name',
                           bay_attr='name')
        self.add_parameter('volume_driver',
                           baymodel_attr='volume_driver')

        self.add_output('api_address',
                        bay_attr='api_address')
        self.add_output('mesos_master_private',
                        bay_attr=None)
        self.add_output('mesos_master',
                        bay_attr='master_addresses')
        self.add_output('mesos_agents_private',
                        bay_attr=None)
        self.add_output('mesos_agents',
                        bay_attr='node_addresses')

    def get_params(self, context, baymodel, bay, **kwargs):
        extra_params = kwargs.pop('extra_params', {})
        # HACK(apmelton) - This uses the user's bearer token, ideally
        # it should be replaced with an actual trust token with only
        # access to do what the template needs it to do.
        osc = self.get_osc(context)
        extra_params['auth_url'] = context.auth_url
        extra_params['username'] = context.user_name
        extra_params['tenant_name'] = context.tenant
        extra_params['domain_name'] = context.domain_name
        extra_params['region_name'] = osc.cinder_region_name()

        label_list = ['rexray_preempt', 'mesos_agent_isolation',
                      'mesos_agent_image_providers',
                      'mesos_agent_work_dir',
                      'mesos_agent_executor_env_variables']

        for label in label_list:
            extra_params[label] = baymodel.labels.get(label)

        scale_mgr = kwargs.pop('scale_manager', None)
        if scale_mgr:
            hosts = self.get_output('mesos_agents_private')
            extra_params['agents_to_remove'] = (
                scale_mgr.get_removal_nodes(hosts))

        return super(UbuntuMesosTemplateDefinition,
                     self).get_params(context, baymodel, bay,
                                      extra_params=extra_params,
                                      **kwargs)

    def get_env_files(self, baymodel):
        if baymodel.master_lb_enabled:
            return [template_def.COMMON_ENV_PATH + 'with_master_lb.yaml']
        else:
            return [template_def.COMMON_ENV_PATH + 'no_master_lb.yaml']

    @property
    def template_path(self):
        return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'templates/mesoscluster.yaml')
