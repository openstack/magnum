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

import magnum.conf
from magnum.drivers.heat import template_def

CONF = magnum.conf.CONF


class UbuntuMesosTemplateDefinition(template_def.BaseTemplateDefinition):
    """Mesos template for Ubuntu VM."""

    def __init__(self):
        super(UbuntuMesosTemplateDefinition, self).__init__()
        self.add_parameter('external_network',
                           cluster_template_attr='external_network_id',
                           required=True)
        self.add_parameter('fixed_network',
                           cluster_template_attr='fixed_network')
        self.add_parameter('fixed_subnet',
                           cluster_template_attr='fixed_subnet')
        self.add_parameter('cluster_name',
                           cluster_attr='name')
        self.add_parameter('volume_driver',
                           cluster_template_attr='volume_driver')

        self.add_output('api_address',
                        cluster_attr='api_address')
        self.add_output('mesos_master_private',
                        cluster_attr=None)
        self.add_output('mesos_slaves_private',
                        cluster_attr=None)

    def get_nodegroup_param_maps(self, master_params=None, worker_params=None):
        master_params = master_params or dict()
        worker_params = worker_params or dict()
        master_params.update({
            'master_flavor': 'flavor_id',
            'master_image': 'image_id',
        })
        worker_params.update({
            'number_of_slaves': 'node_count',
            'slave_flavor': 'flavor_id',
            'slave_image': 'image_id',
        })
        return super(
            UbuntuMesosTemplateDefinition, self).get_nodegroup_param_maps(
                master_params=master_params, worker_params=worker_params)

    def update_outputs(self, stack, cluster_template, cluster,
                       nodegroups=None):
        nodegroups = nodegroups or [cluster.default_ng_worker,
                                    cluster.default_ng_master]
        for nodegroup in nodegroups:
            if nodegroup.role == 'master':
                self.add_output(
                    'mesos_master', nodegroup_attr='node_addresses',
                    nodegroup_uuid=nodegroup.uuid,
                    mapping_type=template_def.NodeGroupOutputMapping)
            else:
                self.add_output(
                    'mesos_slaves', nodegroup_attr='node_addresses',
                    nodegroup_uuid=nodegroup.uuid,
                    mapping_type=template_def.NodeGroupOutputMapping)
                self.add_output(
                    'number_of_slaves', nodegroup_attr='node_count',
                    nodegroup_uuid=nodegroup.uuid, is_stack_param=True,
                    mapping_type=template_def.NodeGroupOutputMapping)
        super(UbuntuMesosTemplateDefinition,
              self).update_outputs(stack, cluster_template, cluster,
                                   nodegroups=nodegroups)

    def get_params(self, context, cluster_template, cluster, **kwargs):
        extra_params = kwargs.pop('extra_params', {})
        # HACK(apmelton) - This uses the user's bearer token, ideally
        # it should be replaced with an actual trust token with only
        # access to do what the template needs it to do.
        osc = self.get_osc(context)
        extra_params['auth_url'] = context.auth_url
        extra_params['username'] = context.user_name
        extra_params['tenant_name'] = context.project_id
        extra_params['domain_name'] = context.domain_name
        extra_params['region_name'] = osc.cinder_region_name()
        extra_params['nodes_affinity_policy'] = \
            CONF.cluster.nodes_affinity_policy

        label_list = ['rexray_preempt', 'mesos_slave_isolation',
                      'mesos_slave_image_providers',
                      'mesos_slave_work_dir',
                      'mesos_slave_executor_env_variables']

        labels = self._get_relevant_labels(cluster, kwargs)

        for label in label_list:
            extra_params[label] = labels.get(label)

        return super(UbuntuMesosTemplateDefinition,
                     self).get_params(context, cluster_template, cluster,
                                      extra_params=extra_params,
                                      **kwargs)

    def get_scale_params(self, context, cluster, node_count,
                         scale_manager=None, nodes_to_remove=None):
        scale_params = dict()
        if nodes_to_remove:
            scale_params['slaves_to_remove'] = nodes_to_remove
        if scale_manager:
            hosts = self.get_output('mesos_slaves_private')
            scale_params['slaves_to_remove'] = (
                scale_manager.get_removal_nodes(hosts))
        scale_params['number_of_slaves'] = node_count
        return scale_params

    def get_env_files(self, cluster_template, cluster, nodegroup=None):
        env_files = []

        template_def.add_priv_net_env_file(env_files, cluster_template,
                                           cluster)
        template_def.add_lb_env_file(env_files, cluster)

        return env_files

    @property
    def driver_module_path(self):
        return __name__[:__name__.rindex('.')]

    @property
    def template_path(self):
        return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'templates/mesoscluster.yaml')
