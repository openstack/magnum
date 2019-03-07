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
from oslo_serialization import jsonutils

from magnum.drivers.heat import template_def

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
    public_ip_output_key = 'dcos_master'
    private_ip_output_key = 'dcos_master_private'


class NodeAddressOutputMapping(ServerAddressOutputMapping):
    public_ip_output_key = 'dcos_slaves'
    private_ip_output_key = 'dcos_slaves_private'


class DcosCentosTemplateDefinition(template_def.BaseTemplateDefinition):
    """DC/OS template for Centos."""

    def __init__(self):
        super(DcosCentosTemplateDefinition, self).__init__()
        self.add_parameter('external_network',
                           cluster_template_attr='external_network_id',
                           required=True)
        self.add_parameter('number_of_slaves',
                           cluster_attr='node_count')
        self.add_parameter('master_flavor',
                           cluster_template_attr='master_flavor_id')
        self.add_parameter('slave_flavor',
                           cluster_template_attr='flavor_id')
        self.add_parameter('cluster_name',
                           cluster_attr='name')
        self.add_parameter('volume_driver',
                           cluster_template_attr='volume_driver')

        self.add_output('api_address',
                        cluster_attr='api_address')
        self.add_output('dcos_master_private',
                        cluster_attr=None)
        self.add_output('dcos_slaves_private',
                        cluster_attr=None)
        self.add_output('dcos_slaves',
                        cluster_attr='node_addresses',
                        mapping_type=NodeAddressOutputMapping)
        self.add_output('dcos_master',
                        cluster_attr='master_addresses',
                        mapping_type=MasterAddressOutputMapping)

    def get_params(self, context, cluster_template, cluster, **kwargs):
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

        # Mesos related label parameters are deleted
        # Because they are not optional in DC/OS configuration
        label_list = ['rexray_preempt',
                      'exhibitor_storage_backend',
                      'exhibitor_zk_hosts',
                      'exhibitor_zk_path',
                      'aws_access_key_id',
                      'aws_region',
                      'aws_secret_access_key',
                      'exhibitor_explicit_keys',
                      's3_bucket',
                      's3_prefix',
                      'exhibitor_azure_account_name',
                      'exhibitor_azure_account_key',
                      'exhibitor_azure_prefix',
                      'dcos_overlay_enable',
                      'dcos_overlay_config_attempts',
                      'dcos_overlay_mtu',
                      'dcos_overlay_network',
                      'dns_search',
                      'check_time',
                      'docker_remove_delay',
                      'gc_delay',
                      'log_directory',
                      'process_timeout',
                      'oauth_enabled',
                      'telemetry_enabled']

        for label in label_list:
            extra_params[label] = cluster.labels.get(label)

        # By default, master_discovery is set to 'static'
        # If --master-lb-enabled is specified,
        # master_discovery will be set to 'master_http_loadbalancer'
        if cluster_template.master_lb_enabled:
            extra_params['master_discovery'] = 'master_http_loadbalancer'

        if 'true' == extra_params['dcos_overlay_enable']:
            overlay_obj = jsonutils.loads(extra_params['dcos_overlay_network'])
            extra_params['dcos_overlay_network'] = '''  vtep_subnet: %s
  vtep_mac_oui: %s
  overlays:''' % (overlay_obj['vtep_subnet'],
                  overlay_obj['vtep_mac_oui'])

            for item in overlay_obj['overlays']:
                extra_params['dcos_overlay_network'] += '''
    - name: %s
      subnet: %s
      prefix: %s''' % (item['name'],
                       item['subnet'],
                       item['prefix'])

        scale_mgr = kwargs.pop('scale_manager', None)
        if scale_mgr:
            hosts = self.get_output('dcos_slaves_private')
            extra_params['slaves_to_remove'] = (
                scale_mgr.get_removal_nodes(hosts))

        return super(DcosCentosTemplateDefinition,
                     self).get_params(context, cluster_template, cluster,
                                      extra_params=extra_params,
                                      **kwargs)

    def get_env_files(self, cluster_template, cluster):
        env_files = []

        template_def.add_priv_net_env_file(env_files, cluster_template)
        template_def.add_lb_env_file(env_files, cluster_template)
        template_def.add_fip_env_file(env_files, cluster_template, cluster)

        return env_files
