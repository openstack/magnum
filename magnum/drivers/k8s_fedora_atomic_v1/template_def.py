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
from magnum.drivers.common import k8s_template_def
from magnum.drivers.common import template_def
from oslo_config import cfg

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


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


class AtomicK8sTemplateDefinition(k8s_template_def.K8sTemplateDefinition):
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
        self.add_output('kube_minions',
                        bay_attr='node_addresses',
                        mapping_type=NodeAddressOutputMapping)
        self.add_output('kube_masters',
                        bay_attr='master_addresses',
                        mapping_type=MasterAddressOutputMapping)

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
