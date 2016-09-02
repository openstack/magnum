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
from oslo_config import cfg

CONF = cfg.CONF
DOCKER_PORT = '2376'


class SwarmApiAddressOutputMapping(template_def.OutputMapping):

    def set_output(self, stack, cluster_template, bay):
        if self.bay_attr is None:
            return

        output_value = self.get_output_value(stack)
        if output_value is not None:
            # Note(rocha): protocol should always be tcp as the docker
            # command client does not handle https (see bug #1604812).
            params = {
                'protocol': 'tcp',
                'address': output_value,
                'port': DOCKER_PORT,
            }
            value = "%(protocol)s://%(address)s:%(port)s" % params
            setattr(bay, self.bay_attr, value)


class AtomicSwarmTemplateDefinition(template_def.BaseTemplateDefinition):
    """Docker swarm template for a Fedora Atomic VM."""

    provides = [
        {'server_type': 'vm', 'os': 'fedora-atomic', 'coe': 'swarm'},
    ]

    def __init__(self):
        super(AtomicSwarmTemplateDefinition, self).__init__()
        self.add_parameter('bay_uuid',
                           bay_attr='uuid',
                           param_type=str)
        self.add_parameter('number_of_nodes',
                           bay_attr='node_count')
        self.add_parameter('master_flavor',
                           cluster_template_attr='master_flavor_id')
        self.add_parameter('node_flavor',
                           cluster_template_attr='flavor_id')
        self.add_parameter('docker_volume_size',
                           cluster_template_attr='docker_volume_size')
        self.add_parameter('external_network',
                           cluster_template_attr='external_network_id',
                           required=True)
        self.add_parameter('network_driver',
                           cluster_template_attr='network_driver')
        self.add_parameter('tls_disabled',
                           cluster_template_attr='tls_disabled',
                           required=True)
        self.add_parameter('registry_enabled',
                           cluster_template_attr='registry_enabled')
        self.add_parameter('docker_storage_driver',
                           cluster_template_attr='docker_storage_driver')
        self.add_parameter('swarm_version',
                           bay_attr='coe_version')

        self.add_output('api_address',
                        bay_attr='api_address',
                        mapping_type=SwarmApiAddressOutputMapping)
        self.add_output('swarm_master_private',
                        bay_attr=None)
        self.add_output('swarm_masters',
                        bay_attr='master_addresses')
        self.add_output('swarm_nodes_private',
                        bay_attr=None)
        self.add_output('swarm_nodes',
                        bay_attr='node_addresses')
        self.add_output('discovery_url',
                        bay_attr='discovery_url')

    def get_params(self, context, cluster_template, bay, **kwargs):
        extra_params = kwargs.pop('extra_params', {})
        extra_params['discovery_url'] = self.get_discovery_url(bay)
        # HACK(apmelton) - This uses the user's bearer token, ideally
        # it should be replaced with an actual trust token with only
        # access to do what the template needs it to do.
        osc = self.get_osc(context)
        extra_params['magnum_url'] = osc.magnum_url()

        label_list = ['flannel_network_cidr', 'flannel_backend',
                      'flannel_network_subnetlen']

        for label in label_list:
            extra_params[label] = cluster_template.labels.get(label)

        if cluster_template.registry_enabled:
            extra_params['swift_region'] = CONF.docker_registry.swift_region
            extra_params['registry_container'] = (
                CONF.docker_registry.swift_registry_container)

        return super(AtomicSwarmTemplateDefinition,
                     self).get_params(context, cluster_template, bay,
                                      extra_params=extra_params,
                                      **kwargs)

    def get_env_files(self, cluster_template):
        if cluster_template.master_lb_enabled:
            return [template_def.COMMON_ENV_PATH + 'with_master_lb.yaml']
        else:
            return [template_def.COMMON_ENV_PATH + 'no_master_lb.yaml']

    @property
    def driver_module_path(self):
        return __name__[:__name__.rindex('.')]

    @property
    def template_path(self):
        return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'templates/cluster.yaml')
