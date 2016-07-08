# Copyright 2014 Rackspace Inc. All rights reserved.
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
from oslo_config import cfg
from oslo_log import log as logging

from magnum.common import paths
from magnum.drivers.common import template_def
from magnum.i18n import _


LOG = logging.getLogger(__name__)

KUBE_SECURE_PORT = '6443'
KUBE_INSECURE_PORT = '8080'

template_def_opts = [
    cfg.StrOpt('k8s_atomic_template_path',
               default=paths.basedir_def('templates/kubernetes/'
                                         'kubecluster.yaml'),
               deprecated_name='template_path',
               deprecated_group='bay_heat',
               help=_(
                   'Location of template to build a k8s cluster on atomic.')),
    cfg.StrOpt('k8s_coreos_template_path',
               default=paths.basedir_def('templates/kubernetes/'
                                         'kubecluster-coreos.yaml'),
               help=_(
                   'Location of template to build a k8s cluster on CoreOS.')),
    cfg.StrOpt('etcd_discovery_service_endpoint_format',
               default='https://discovery.etcd.io/new?size=%(size)d',
               help=_('Url for etcd public discovery endpoint.')),
    cfg.ListOpt('enabled_definitions',
                default=['magnum_vm_atomic_k8s', 'magnum_vm_coreos_k8s',
                         'magnum_vm_atomic_swarm', 'magnum_vm_ubuntu_mesos'],
                help=_('Enabled bay definition entry points.')),
]

docker_registry_opts = [
    cfg.StrOpt('swift_region',
               help=_('Region name of Swift')),
    cfg.StrOpt('swift_registry_container',
               default='docker_registry',
               help=_('Name of the container in Swift which docker registry '
                      'stores images in'))
]

CONF = cfg.CONF
CONF.register_opts(template_def_opts, group='bay')
CONF.register_opts(docker_registry_opts, group='docker_registry')


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
            hosts = self.get_output('kube_minions')
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

    def get_env_files(self, baymodel):
        if baymodel.master_lb_enabled:
            return ['environments/with_master_lb.yaml']
        else:
            return ['environments/no_master_lb.yaml']


class AtomicK8sTemplateDefinition(K8sTemplateDefinition):
    """Kubernetes template for a Fedora Atomic VM."""

    provides = [
        {'server_type': 'vm',
         'os': 'fedora-atomic',
         'coe': 'kubernetes'},
    ]

    def __init__(self):
        super(AtomicK8sTemplateDefinition, self).__init__()
        self.add_parameter('docker_volume_size',
                           baymodel_attr='docker_volume_size')
        self.add_parameter('docker_storage_driver',
                           baymodel_attr='docker_storage_driver')

    def get_params(self, context, baymodel, bay, **kwargs):
        extra_params = kwargs.pop('extra_params', {})

        extra_params['username'] = context.user_name
        extra_params['tenant_name'] = context.tenant
        osc = self.get_osc(context)
        extra_params['region_name'] = osc.cinder_region_name()

        return super(AtomicK8sTemplateDefinition,
                     self).get_params(context, baymodel, bay,
                                      extra_params=extra_params,
                                      **kwargs)

    @property
    def template_path(self):
        return cfg.CONF.bay.k8s_atomic_template_path


class CoreOSK8sTemplateDefinition(K8sTemplateDefinition):
    """Kubernetes template for CoreOS VM."""

    provides = [
        {'server_type': 'vm', 'os': 'coreos', 'coe': 'kubernetes'},
    ]

    @property
    def template_path(self):
        return cfg.CONF.bay.k8s_coreos_template_path
