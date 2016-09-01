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

from neutronclient.common import exceptions as n_exception
from neutronclient.neutron import v2_0 as neutronV20
import os
from oslo_log import log as logging

from magnum.common import exception
from magnum.drivers.common import template_def
from oslo_config import cfg

CONF = cfg.CONF
KUBE_SECURE_PORT = '6443'
KUBE_INSECURE_PORT = '8080'

LOG = logging.getLogger(__name__)


class K8sApiAddressOutputMapping(template_def.OutputMapping):

    def set_output(self, stack, cluster_template, bay):
        if self.bay_attr is None:
            return

        output_value = self.get_output_value(stack)
        if output_value is not None:
            # TODO(yuanying): port number is hardcoded, this will be fix
            protocol = 'https'
            port = KUBE_SECURE_PORT
            if cluster_template.tls_disabled:
                protocol = 'http'
                port = KUBE_INSECURE_PORT

            params = {
                'protocol': protocol,
                'address': output_value,
                'port': port,
            }
            value = "%(protocol)s://%(address)s:%(port)s" % params
            setattr(bay, self.bay_attr, value)


class ServerAddressOutputMapping(template_def.OutputMapping):

    public_ip_output_key = None
    private_ip_output_key = None

    def __init__(self, dummy_arg, bay_attr=None):
        self.bay_attr = bay_attr
        self.heat_output = self.public_ip_output_key

    def set_output(self, stack, cluster_template, bay):
        if not cluster_template.floating_ip_enabled:
            self.heat_output = self.private_ip_output_key

        LOG.debug("Using heat_output: %s", self.heat_output)
        super(ServerAddressOutputMapping,
              self).set_output(stack, cluster_template, bay)


class MasterAddressOutputMapping(ServerAddressOutputMapping):
    public_ip_output_key = 'kube_masters'
    private_ip_output_key = 'kube_masters_private'


class NodeAddressOutputMapping(ServerAddressOutputMapping):
    public_ip_output_key = 'kube_minions'
    private_ip_output_key = 'kube_minions_private'


class K8sTemplateDefinition(template_def.BaseTemplateDefinition):
    """Base Kubernetes template."""

    def __init__(self):
        super(K8sTemplateDefinition, self).__init__()
        self.add_parameter('master_flavor',
                           cluster_template_attr='master_flavor_id')
        self.add_parameter('minion_flavor',
                           cluster_template_attr='flavor_id')
        self.add_parameter('number_of_minions',
                           bay_attr='node_count')
        self.add_parameter('external_network',
                           cluster_template_attr='external_network_id',
                           required=True)
        self.add_parameter('network_driver',
                           cluster_template_attr='network_driver')
        self.add_parameter('volume_driver',
                           cluster_template_attr='volume_driver')
        self.add_parameter('tls_disabled',
                           cluster_template_attr='tls_disabled',
                           required=True)
        self.add_parameter('registry_enabled',
                           cluster_template_attr='registry_enabled')
        self.add_parameter('bay_uuid',
                           bay_attr='uuid',
                           param_type=str)
        self.add_parameter('insecure_registry_url',
                           cluster_template_attr='insecure_registry')
        self.add_parameter('kube_version',
                           bay_attr='coe_version')

        self.add_output('api_address',
                        bay_attr='api_address',
                        mapping_type=K8sApiAddressOutputMapping)
        self.add_output('kube_minions_private',
                        bay_attr=None)
        self.add_output('kube_minions',
                        bay_attr='node_addresses',
                        mapping_type=NodeAddressOutputMapping)
        self.add_output('kube_masters_private',
                        bay_attr=None)
        self.add_output('kube_masters',
                        bay_attr='master_addresses',
                        mapping_type=MasterAddressOutputMapping)

    def get_params(self, context, cluster_template, bay, **kwargs):
        extra_params = kwargs.pop('extra_params', {})
        scale_mgr = kwargs.pop('scale_manager', None)
        if scale_mgr:
            hosts = self.get_output('kube_minions_private')
            extra_params['minions_to_remove'] = (
                scale_mgr.get_removal_nodes(hosts))

        extra_params['discovery_url'] = self.get_discovery_url(bay)
        osc = self.get_osc(context)
        extra_params['magnum_url'] = osc.magnum_url()

        if cluster_template.tls_disabled:
            extra_params['loadbalancing_protocol'] = 'HTTP'
            extra_params['kubernetes_port'] = 8080

        label_list = ['flannel_network_cidr', 'flannel_backend',
                      'flannel_network_subnetlen']
        for label in label_list:
            extra_params[label] = cluster_template.labels.get(label)

        if cluster_template.registry_enabled:
            extra_params['swift_region'] = CONF.docker_registry.swift_region
            extra_params['registry_container'] = (
                CONF.docker_registry.swift_registry_container)

        return super(K8sTemplateDefinition,
                     self).get_params(context, cluster_template, bay,
                                      extra_params=extra_params,
                                      **kwargs)


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
                           cluster_template_attr='docker_volume_size')
        self.add_parameter('docker_storage_driver',
                           cluster_template_attr='docker_storage_driver')

    def get_params(self, context, cluster_template, bay, **kwargs):
        extra_params = kwargs.pop('extra_params', {})

        extra_params['username'] = context.user_name
        extra_params['tenant_name'] = context.tenant
        osc = self.get_osc(context)
        extra_params['region_name'] = osc.cinder_region_name()

        return super(AtomicK8sTemplateDefinition,
                     self).get_params(context, cluster_template, bay,
                                      extra_params=extra_params,
                                      **kwargs)

    def get_env_files(self, cluster_template):
        env_files = []
        if cluster_template.master_lb_enabled:
            env_files.append(
                template_def.COMMON_ENV_PATH + 'with_master_lb.yaml')
        else:
            env_files.append(
                template_def.COMMON_ENV_PATH + 'no_master_lb.yaml')
        if cluster_template.floating_ip_enabled:
            env_files.append(
                template_def.COMMON_ENV_PATH + 'enable_floating_ip.yaml')
        else:
            env_files.append(
                template_def.COMMON_ENV_PATH + 'disable_floating_ip.yaml')

        return env_files

    @property
    def driver_module_path(self):
        return __name__[:__name__.rindex('.')]

    @property
    def template_path(self):
        return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'templates/kubecluster.yaml')


class FedoraK8sIronicTemplateDefinition(AtomicK8sTemplateDefinition):
    """Kubernetes template for a Fedora Baremetal."""

    provides = [
        {'server_type': 'bm',
         'os': 'fedora',
         'coe': 'kubernetes'},
    ]

    def __init__(self):
        super(FedoraK8sIronicTemplateDefinition, self).__init__()
        self.add_parameter('fixed_subnet',
                           cluster_template_attr='fixed_subnet',
                           param_type=str,
                           required=True)

    def get_fixed_network_id(self, osc, cluster_template):
        try:
            subnet = neutronV20.find_resource_by_name_or_id(
                osc.neutron(),
                'subnet',
                cluster_template.fixed_subnet
            )
        except n_exception.NeutronException as e:
            # NOTE(yuanying): NeutronCLIError doesn't have status_code
            # if subnet name is duplicated, NeutronClientNoUniqueMatch
            # (which is kind of NeutronCLIError) will be raised.
            if getattr(e, 'status_code', 400) < 500:
                raise exception.InvalidSubnet(message=("%s" % e))
            else:
                raise e

        if subnet['ip_version'] != 4:
            raise exception.InvalidSubnet(
                message="Subnet IP version should be 4"
            )

        return subnet['network_id']

    def get_params(self, context, cluster_template, bay, **kwargs):
        ep = kwargs.pop('extra_params', {})

        osc = self.get_osc(context)
        ep['fixed_network'] = self.get_fixed_network_id(osc, cluster_template)

        return super(FedoraK8sIronicTemplateDefinition,
                     self).get_params(context, cluster_template, bay,
                                      extra_params=ep,
                                      **kwargs)

    @property
    def driver_module_path(self):
        return __name__[:__name__.rindex('.')]

    @property
    def template_path(self):
        return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'templates/kubecluster-fedora-ironic.yaml')
