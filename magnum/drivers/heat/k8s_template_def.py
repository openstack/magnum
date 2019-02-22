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
from oslo_utils import uuidutils

from magnum.common import exception
from magnum.common import keystone
from magnum.common import neutron
from magnum.drivers.heat import template_def

CONF = cfg.CONF


"""kubernetes ports """
KUBE_SECURE_PORT = '6443'
KUBE_INSECURE_PORT = '8080'


class K8sApiAddressOutputMapping(template_def.OutputMapping):

    def set_output(self, stack, cluster_template, cluster):
        if self.cluster_attr is None:
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
            setattr(cluster, self.cluster_attr, value)


class K8sTemplateDefinition(template_def.BaseTemplateDefinition):
    """Base Kubernetes template."""

    def __init__(self):
        super(K8sTemplateDefinition, self).__init__()
        self.add_parameter('master_flavor',
                           cluster_attr='master_flavor_id')
        self.add_parameter('minion_flavor',
                           cluster_attr='flavor_id')
        self.add_parameter('number_of_minions',
                           cluster_attr='node_count')
        self.add_parameter('external_network',
                           cluster_template_attr='external_network_id',
                           required=True)
        self.add_parameter('fixed_network',
                           cluster_template_attr='fixed_network')
        self.add_parameter('fixed_subnet',
                           cluster_template_attr='fixed_subnet')
        self.add_parameter('network_driver',
                           cluster_template_attr='network_driver')
        self.add_parameter('volume_driver',
                           cluster_template_attr='volume_driver')
        self.add_parameter('tls_disabled',
                           cluster_template_attr='tls_disabled',
                           required=True)
        self.add_parameter('registry_enabled',
                           cluster_template_attr='registry_enabled')
        self.add_parameter('cluster_uuid',
                           cluster_attr='uuid',
                           param_type=str)
        self.add_parameter('insecure_registry_url',
                           cluster_template_attr='insecure_registry')
        self.add_parameter('kube_version',
                           cluster_attr='coe_version')

        self.add_output('api_address',
                        cluster_attr='api_address',
                        mapping_type=K8sApiAddressOutputMapping)
        self.add_output('kube_minions_private',
                        cluster_attr=None)
        self.add_output('kube_masters_private',
                        cluster_attr=None)

    def get_params(self, context, cluster_template, cluster, **kwargs):
        extra_params = kwargs.pop('extra_params', {})

        extra_params['discovery_url'] = \
            self.get_discovery_url(cluster, cluster_template=cluster_template)
        osc = self.get_osc(context)
        extra_params['magnum_url'] = osc.magnum_url()

        if cluster_template.tls_disabled:
            extra_params['loadbalancing_protocol'] = 'HTTP'
            extra_params['kubernetes_port'] = 8080

        extra_params['octavia_enabled'] = keystone.is_octavia_enabled()

        # NOTE(lxkong): Convert external network name to UUID, the template
        # field name is confused. If external_network_id is not specified in
        # cluster template use 'public' as the default value, which is the same
        # with the heat template default value as before.
        ext_net = cluster_template.external_network_id or "public"
        if not uuidutils.is_uuid_like(ext_net):
            ext_net_id = neutron.get_network_id(context, ext_net)
            extra_params['external_network'] = ext_net_id
        else:
            extra_params['external_network'] = ext_net

        label_list = ['flannel_network_cidr', 'flannel_backend',
                      'flannel_network_subnetlen',
                      'system_pods_initial_delay',
                      'system_pods_timeout',
                      'admission_control_list',
                      'prometheus_monitoring',
                      'grafana_admin_passwd',
                      'kube_dashboard_enabled',
                      'etcd_volume_size',
                      'cert_manager_api',
                      'ingress_controller_role',
                      'octavia_ingress_controller_tag',
                      'kubelet_options',
                      'kubeapi_options',
                      'kubeproxy_options',
                      'kubecontroller_options',
                      'kubescheduler_options',
                      'influx_grafana_dashboard_enabled']

        for label in label_list:
            extra_params[label] = cluster.labels.get(label)

        ingress_controller = cluster.labels.get('ingress_controller',
                                                '').lower()
        if (ingress_controller == 'octavia'
                and not extra_params['octavia_enabled']):
            raise exception.InvalidParameterValue(
                'Octavia service needs to be deployed for octavia ingress '
                'controller.')
        extra_params["ingress_controller"] = ingress_controller

        cluser_ip_range = cluster.labels.get('service_cluster_ip_range')
        if cluser_ip_range:
            extra_params['portal_network_cidr'] = cluser_ip_range

        if cluster_template.registry_enabled:
            extra_params['swift_region'] = CONF.docker_registry.swift_region
            extra_params['registry_container'] = (
                CONF.docker_registry.swift_registry_container)

        return super(K8sTemplateDefinition,
                     self).get_params(context, cluster_template, cluster,
                                      extra_params=extra_params,
                                      **kwargs)

    def get_scale_params(self, context, cluster, scale_manager=None,
                         nodes_to_remove=None):
        scale_params = dict()
        if nodes_to_remove:
            scale_params['minions_to_remove'] = nodes_to_remove
        if scale_manager:
            hosts = self.get_output('kube_minions_private')
            scale_params['minions_to_remove'] = (
                scale_manager.get_removal_nodes(hosts))
        return scale_params
