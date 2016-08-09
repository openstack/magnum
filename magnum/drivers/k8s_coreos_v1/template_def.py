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
KUBE_SECURE_PORT = '6443'
KUBE_INSECURE_PORT = '8080'


class K8sApiAddressOutputMapping(template_def.OutputMapping):

    def set_output(self, stack, baymodel, bay):
        if self.bay_attr is None:
            return

        output_value = self.get_output_value(stack)
        if output_value is not None:
            # TODO(yuanying): port number is hardcoded, this will be fix
            protocol = 'https'
            port = KUBE_SECURE_PORT
            if baymodel.tls_disabled:
                protocol = 'http'
                port = KUBE_INSECURE_PORT

            params = {
                'protocol': protocol,
                'address': output_value,
                'port': port,
            }
            value = "%(protocol)s://%(address)s:%(port)s" % params
            setattr(bay, self.bay_attr, value)


class K8sTemplateDefinition(template_def.BaseTemplateDefinition):
    """Base Kubernetes template."""

    def __init__(self):
        super(K8sTemplateDefinition, self).__init__()
        self.add_parameter('master_flavor',
                           baymodel_attr='master_flavor_id')
        self.add_parameter('minion_flavor',
                           baymodel_attr='flavor_id')
        self.add_parameter('number_of_minions',
                           bay_attr='node_count')
        self.add_parameter('external_network',
                           baymodel_attr='external_network_id',
                           required=True)
        self.add_parameter('network_driver',
                           baymodel_attr='network_driver')
        self.add_parameter('volume_driver',
                           baymodel_attr='volume_driver')
        self.add_parameter('tls_disabled',
                           baymodel_attr='tls_disabled',
                           required=True)
        self.add_parameter('registry_enabled',
                           baymodel_attr='registry_enabled')
        self.add_parameter('bay_uuid',
                           bay_attr='uuid',
                           param_type=str)
        self.add_parameter('insecure_registry_url',
                           baymodel_attr='insecure_registry')

        self.add_output('api_address',
                        bay_attr='api_address',
                        mapping_type=K8sApiAddressOutputMapping)
        self.add_output('kube_minions_private',
                        bay_attr=None)
        self.add_output('kube_minions',
                        bay_attr='node_addresses')
        self.add_output('kube_masters_private',
                        bay_attr=None)
        self.add_output('kube_masters',
                        bay_attr='master_addresses')

    def get_params(self, context, baymodel, bay, **kwargs):
        extra_params = kwargs.pop('extra_params', {})
        scale_mgr = kwargs.pop('scale_manager', None)
        if scale_mgr:
            hosts = self.get_output('kube_minions_private')
            extra_params['minions_to_remove'] = (
                scale_mgr.get_removal_nodes(hosts))

        extra_params['discovery_url'] = self.get_discovery_url(bay)
        osc = self.get_osc(context)
        extra_params['magnum_url'] = osc.magnum_url()

        if baymodel.tls_disabled:
            extra_params['loadbalancing_protocol'] = 'HTTP'
            extra_params['kubernetes_port'] = 8080

        label_list = ['flannel_network_cidr', 'flannel_backend',
                      'flannel_network_subnetlen']
        for label in label_list:
            extra_params[label] = baymodel.labels.get(label)

        if baymodel.registry_enabled:
            extra_params['swift_region'] = CONF.docker_registry.swift_region
            extra_params['registry_container'] = (
                CONF.docker_registry.swift_registry_container)

        return super(K8sTemplateDefinition,
                     self).get_params(context, baymodel, bay,
                                      extra_params=extra_params,
                                      **kwargs)


class CoreOSK8sTemplateDefinition(K8sTemplateDefinition):
    """Kubernetes template for CoreOS VM."""

    provides = [
        {'server_type': 'vm',
         'os': 'coreos',
         'coe': 'kubernetes'},
    ]

    def get_env_files(self, baymodel):
        if baymodel.master_lb_enabled:
            return ['../../common/templates/environments/with_master_lb.yaml']
        else:
            return ['../../common/templates/environments/no_master_lb.yaml']

    @property
    def template_path(self):
        return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'templates/kubecluster.yaml')
