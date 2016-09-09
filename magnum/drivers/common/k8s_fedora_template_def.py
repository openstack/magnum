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

from oslo_log import log as logging

from magnum.drivers.common import k8s_template_def
from magnum.drivers.common import template_def
from oslo_config import cfg

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class ServerAddressOutputMapping(template_def.OutputMapping):

    public_ip_output_key = None
    private_ip_output_key = None

    def __init__(self, dummy_arg, cluster_attr=None):
        self.cluster_attr = cluster_attr
        self.heat_output = self.public_ip_output_key

    def set_output(self, stack, cluster_template, cluster):
        if not cluster_template.floating_ip_enabled:
            self.heat_output = self.private_ip_output_key

        LOG.debug("Using heat_output: %s", self.heat_output)
        super(ServerAddressOutputMapping,
              self).set_output(stack, cluster_template, cluster)


class MasterAddressOutputMapping(ServerAddressOutputMapping):
    public_ip_output_key = 'kube_masters'
    private_ip_output_key = 'kube_masters_private'


class NodeAddressOutputMapping(ServerAddressOutputMapping):
    public_ip_output_key = 'kube_minions'
    private_ip_output_key = 'kube_minions_private'


class K8sFedoraTemplateDefinition(k8s_template_def.K8sTemplateDefinition):
    """Kubernetes template for a Fedora."""

    def __init__(self):
        super(K8sFedoraTemplateDefinition, self).__init__()
        self.add_parameter('docker_volume_size',
                           cluster_template_attr='docker_volume_size')
        self.add_parameter('docker_storage_driver',
                           cluster_template_attr='docker_storage_driver')
        self.add_output('kube_minions',
                        cluster_attr='node_addresses',
                        mapping_type=NodeAddressOutputMapping)
        self.add_output('kube_masters',
                        cluster_attr='master_addresses',
                        mapping_type=MasterAddressOutputMapping)

    def get_params(self, context, cluster_template, cluster, **kwargs):
        extra_params = kwargs.pop('extra_params', {})

        extra_params['username'] = context.user_name
        extra_params['tenant_name'] = context.tenant
        osc = self.get_osc(context)
        extra_params['region_name'] = osc.cinder_region_name()

        return super(K8sFedoraTemplateDefinition,
                     self).get_params(context, cluster_template, cluster,
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
