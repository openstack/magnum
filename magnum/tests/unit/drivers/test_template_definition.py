# Copyright 2015 Rackspace Inc. All rights reserved.
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

import abc
from neutronclient.common import exceptions as n_exception
from unittest import mock

import six

from magnum.common import exception
import magnum.conf
from magnum.drivers.common import driver
from magnum.drivers.heat import template_def as cmn_tdef
from magnum.drivers.k8s_coreos_v1 import driver as k8s_coreos_dr
from magnum.drivers.k8s_coreos_v1 import template_def as k8s_coreos_tdef
from magnum.drivers.k8s_fedora_atomic_v1 import driver as k8sa_dr
from magnum.drivers.k8s_fedora_atomic_v1 import template_def as k8sa_tdef
from magnum.drivers.k8s_fedora_ironic_v1 import driver as k8s_i_dr
from magnum.drivers.k8s_fedora_ironic_v1 import template_def as k8si_tdef
from magnum.drivers.mesos_ubuntu_v1 import driver as mesos_dr
from magnum.drivers.mesos_ubuntu_v1 import template_def as mesos_tdef
from magnum.drivers.swarm_fedora_atomic_v1 import driver as swarm_dr
from magnum.drivers.swarm_fedora_atomic_v1 import template_def as swarm_tdef
from magnum.drivers.swarm_fedora_atomic_v2 import driver as swarm_v2_dr
from magnum.drivers.swarm_fedora_atomic_v2 import template_def as swarm_v2_tdef
from magnum.tests import base

from requests import exceptions as req_exceptions

CONF = magnum.conf.CONF


class TemplateDefinitionTestCase(base.TestCase):

    @mock.patch.object(driver, 'iter_entry_points')
    def test_load_entry_points(self, mock_iter_entry_points):
        mock_entry_point = mock.MagicMock()
        mock_entry_points = [mock_entry_point]
        mock_iter_entry_points.return_value = mock_entry_points.__iter__()

        entry_points = driver.Driver.load_entry_points()

        for (expected_entry_point,
             (actual_entry_point, loaded_cls)) in zip(mock_entry_points,
                                                      entry_points):
            self.assertEqual(expected_entry_point, actual_entry_point)
            expected_entry_point.load.assert_called_once_with(require=False)

    @mock.patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_get_vm_atomic_kubernetes_definition(self, mock_driver):
        mock_driver.return_value = k8sa_dr.Driver()
        cluster_driver = driver.Driver.get_driver('vm',
                                                  'fedora-atomic',
                                                  'kubernetes')
        definition = cluster_driver.get_template_definition()

        self.assertIsInstance(definition,
                              k8sa_tdef.AtomicK8sTemplateDefinition)

    @mock.patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_get_bm_fedora_kubernetes_ironic_definition(self, mock_driver):
        mock_driver.return_value = k8s_i_dr.Driver()
        cluster_driver = driver.Driver.get_driver('bm',
                                                  'fedora',
                                                  'kubernetes')
        definition = cluster_driver.get_template_definition()

        self.assertIsInstance(definition,
                              k8si_tdef.FedoraK8sIronicTemplateDefinition)

    @mock.patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_get_vm_coreos_kubernetes_definition(self, mock_driver):
        mock_driver.return_value = k8s_coreos_dr.Driver()
        cluster_driver = driver.Driver.get_driver('vm', 'coreos', 'kubernetes')
        definition = cluster_driver.get_template_definition()

        self.assertIsInstance(definition,
                              k8s_coreos_tdef.CoreOSK8sTemplateDefinition)

    @mock.patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_get_vm_atomic_swarm_definition(self, mock_driver):
        mock_driver.return_value = swarm_dr.Driver()
        cluster_driver = driver.Driver.get_driver('vm',
                                                  'fedora-atomic',
                                                  'swarm')
        definition = cluster_driver.get_template_definition()

        self.assertIsInstance(definition,
                              swarm_tdef.AtomicSwarmTemplateDefinition)

    @mock.patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_get_vm_atomic_swarm_v2_definition(self, mock_driver):
        mock_driver.return_value = swarm_v2_dr.Driver()
        cluster_driver = driver.Driver.get_driver('vm',
                                                  'fedora-atomic',
                                                  'swarm-mode')
        definition = cluster_driver.get_template_definition()

        self.assertIsInstance(definition,
                              swarm_v2_tdef.AtomicSwarmTemplateDefinition)

    @mock.patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_get_vm_ubuntu_mesos_definition(self, mock_driver):
        mock_driver.return_value = mesos_dr.Driver()
        cluster_driver = driver.Driver.get_driver('vm',
                                                  'ubuntu',
                                                  'mesos')
        definition = cluster_driver.get_template_definition()

        self.assertIsInstance(definition,
                              mesos_tdef.UbuntuMesosTemplateDefinition)

    def test_get_driver_not_supported(self):
        self.assertRaises(exception.ClusterTypeNotSupported,
                          driver.Driver.get_driver,
                          'vm', 'not_supported', 'kubernetes')

    def test_required_param_not_set(self):
        param = cmn_tdef.ParameterMapping('test', cluster_template_attr='test',
                                          required=True)
        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.test = None

        self.assertRaises(exception.RequiredParameterNotProvided,
                          param.set_param, {}, mock_cluster_template, None)

    def test_output_mapping(self):
        heat_outputs = [
            {
                "output_value": "value1",
                "description": "No description given",
                "output_key": "key1"
            },
            {
                "output_value": ["value2", "value3"],
                "description": "No description given",
                "output_key": "key2"
            }
        ]

        mock_stack = mock.MagicMock()
        mock_cluster = mock.MagicMock()
        mock_stack.to_dict.return_value = {'outputs': heat_outputs}

        output = cmn_tdef.OutputMapping('key1')
        value = output.get_output_value(mock_stack, mock_cluster)
        self.assertEqual('value1', value)

        output = cmn_tdef.OutputMapping('key2')
        value = output.get_output_value(mock_stack, mock_cluster)
        self.assertEqual(["value2", "value3"], value)

        output = cmn_tdef.OutputMapping('key3')
        value = output.get_output_value(mock_stack, mock_cluster)
        self.assertIsNone(value)

        # verify stack with no 'outputs' attribute
        mock_stack.to_dict.return_value = {}
        output = cmn_tdef.OutputMapping('key1')
        value = output.get_output_value(mock_stack, mock_cluster)
        self.assertIsNone(value)

    def test_add_output_with_mapping_type(self):
        definition = k8sa_dr.Driver().get_template_definition()

        mock_args = [1, 3, 4]
        mock_kwargs = {'cluster_attr': 'test'}
        mock_mapping_type = mock.MagicMock()
        mock_mapping_type.return_value = mock.MagicMock()
        definition.add_output(mapping_type=mock_mapping_type, *mock_args,
                              **mock_kwargs)

        mock_mapping_type.assert_called_once_with(*mock_args, **mock_kwargs)
        self.assertIn(mock_mapping_type.return_value,
                      definition.output_mappings)

    def test_add_fip_env_lb_disabled_with_fp(self):
        mock_cluster = mock.MagicMock(master_lb_enabled=False, labels={})
        env_files = []
        cmn_tdef.add_fip_env_file(env_files, mock_cluster)
        self.assertEqual(
            [
                cmn_tdef.COMMON_ENV_PATH + 'enable_floating_ip.yaml',
                cmn_tdef.COMMON_ENV_PATH + 'disable_lb_floating_ip.yaml'
            ],
            env_files
        )

    def test_add_fip_env_lb_enabled_with_fp(self):
        mock_cluster = mock.MagicMock(floating_ip_enabled=True,
                                      master_lb_enabled=True,
                                      labels={})
        env_files = []
        cmn_tdef.add_fip_env_file(env_files, mock_cluster)
        self.assertEqual(
            [
                cmn_tdef.COMMON_ENV_PATH + 'enable_floating_ip.yaml',
                cmn_tdef.COMMON_ENV_PATH + 'enable_lb_floating_ip.yaml'
            ],
            env_files
        )

    def test_add_fip_env_lb_disabled_without_fp(self):
        mock_cluster = mock.MagicMock(labels={}, floating_ip_enabled=False)
        env_files = []
        cmn_tdef.add_fip_env_file(env_files, mock_cluster)
        self.assertEqual(
            [
                cmn_tdef.COMMON_ENV_PATH + 'disable_floating_ip.yaml',
                cmn_tdef.COMMON_ENV_PATH + 'disable_lb_floating_ip.yaml'
            ],
            env_files
        )

    def test_add_fip_env_lb_enabled_without_fp(self):
        mock_cluster = mock.MagicMock(labels={}, floating_ip_enabled=False,)
        env_files = []
        cmn_tdef.add_fip_env_file(env_files, mock_cluster)
        self.assertEqual(
            [
                cmn_tdef.COMMON_ENV_PATH + 'disable_floating_ip.yaml',
                cmn_tdef.COMMON_ENV_PATH + 'disable_lb_floating_ip.yaml'
            ],
            env_files
        )

    def test_add_fip_env_lb_fip_enabled_without_fp(self):
        mock_cluster = mock.MagicMock(
            labels={"master_lb_floating_ip_enabled": "true"},
            floating_ip_enabled=False,)
        env_files = []
        cmn_tdef.add_fip_env_file(env_files, mock_cluster)
        self.assertEqual(
            [
                cmn_tdef.COMMON_ENV_PATH + 'disable_floating_ip.yaml',
                cmn_tdef.COMMON_ENV_PATH + 'enable_lb_floating_ip.yaml'
            ],
            env_files
        )

    def test_add_fip_env_lb_enable_lbfip_disable(self):
        mock_cluster = mock.MagicMock(
            labels={"master_lb_floating_ip_enabled": "false"},
            floating_ip_enabled=False,)
        env_files = []

        cmn_tdef.add_fip_env_file(env_files, mock_cluster)

        self.assertEqual(
            [
                cmn_tdef.COMMON_ENV_PATH + 'disable_floating_ip.yaml',
                cmn_tdef.COMMON_ENV_PATH + 'disable_lb_floating_ip.yaml'
            ],
            env_files
        )

    def test_add_fip_env_lb_enable_lbfip_template_disable_cluster_enable(self):
        mock_cluster = mock.MagicMock(
            floating_ip_enabled=True,
            labels={})
        env_files = []

        cmn_tdef.add_fip_env_file(env_files, mock_cluster)

        self.assertEqual(
            [
                cmn_tdef.COMMON_ENV_PATH + 'enable_floating_ip.yaml',
                cmn_tdef.COMMON_ENV_PATH + 'enable_lb_floating_ip.yaml'
            ],
            env_files
        )

    def test_add_fip_master_lb_fip_disabled_cluster_fip_enabled(self):
        mock_cluster = mock.MagicMock(
            labels={"master_lb_floating_ip_enabled": "false"},
            floating_ip_enabled=True,)
        env_files = []

        cmn_tdef.add_fip_env_file(env_files, mock_cluster)

        self.assertEqual(
            [
                cmn_tdef.COMMON_ENV_PATH + 'enable_floating_ip.yaml',
                cmn_tdef.COMMON_ENV_PATH + 'enable_lb_floating_ip.yaml'
            ],
            env_files
        )


@six.add_metaclass(abc.ABCMeta)
class BaseK8sTemplateDefinitionTestCase(base.TestCase):

    def setUp(self):
        super(BaseK8sTemplateDefinitionTestCase, self).setUp()
        self.master_ng = mock.MagicMock(uuid='master_ng', role='master')
        self.worker_ng = mock.MagicMock(uuid='worker_ng', role='worker')
        self.nodegroups = [self.master_ng, self.worker_ng]
        self.mock_cluster = mock.MagicMock(nodegroups=self.nodegroups,
                                           default_ng_worker=self.worker_ng,
                                           default_ng_master=self.master_ng)

    @abc.abstractmethod
    def get_definition(self):
        """Returns the template definition."""
        pass

    def _test_update_outputs_server_address(
        self,
        floating_ip_enabled=True,
        public_ip_output_key='kube_masters',
        private_ip_output_key='kube_masters_private',
        cluster_attr=None,
        nodegroup_attr=None,
        is_master=False
    ):
        definition = self.get_definition()

        expected_address = expected_public_address = ['public']
        expected_private_address = ['private']
        if not floating_ip_enabled:
            expected_address = expected_private_address

        outputs = [
            {"output_value": expected_public_address,
             "description": "No description given",
             "output_key": public_ip_output_key},
            {"output_value": expected_private_address,
             "description": "No description given",
             "output_key": private_ip_output_key},
        ]
        mock_stack = mock.MagicMock()
        mock_stack.to_dict.return_value = {'outputs': outputs}
        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.floating_ip_enabled = floating_ip_enabled
        self.mock_cluster.floating_ip_enabled = floating_ip_enabled

        definition.update_outputs(mock_stack, mock_cluster_template,
                                  self.mock_cluster)

        actual = None
        if cluster_attr:
            actual = getattr(self.mock_cluster, cluster_attr)
        elif is_master:
            actual = getattr(
                self.mock_cluster.default_ng_master, nodegroup_attr)
        else:
            actual = getattr(
                self.mock_cluster.default_ng_worker, nodegroup_attr)

        self.assertEqual(expected_address, actual)


class AtomicK8sTemplateDefinitionTestCase(BaseK8sTemplateDefinitionTestCase):

    def get_definition(self):
        return k8sa_dr.Driver().get_template_definition()

    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch('magnum.drivers.heat.template_def.TemplateDefinition'
                '.get_output')
    def test_k8s_get_scale_params(self, mock_get_output,
                                  mock_osc_class):
        mock_context = mock.MagicMock()
        mock_cluster = mock.MagicMock()

        removal_nodes = ['node1', 'node2']
        node_count = 5
        mock_scale_manager = mock.MagicMock()
        mock_scale_manager.get_removal_nodes.return_value = removal_nodes

        definition = k8sa_tdef.AtomicK8sTemplateDefinition()

        scale_params = definition.get_scale_params(mock_context, mock_cluster,
                                                   node_count,
                                                   mock_scale_manager)
        expected_scale_params = {
            'minions_to_remove': ['node1', 'node2'],
            'number_of_minions': 5
        }
        self.assertEqual(scale_params, expected_scale_params)

    @mock.patch('magnum.common.neutron.get_subnet')
    @mock.patch('magnum.drivers.heat.k8s_template_def.K8sTemplateDefinition'
                '._set_master_lb_allowed_cidrs')
    @mock.patch('magnum.common.neutron.get_fixed_network_name')
    @mock.patch('magnum.common.keystone.is_octavia_enabled')
    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch('magnum.drivers.k8s_fedora_atomic_v1.template_def'
                '.AtomicK8sTemplateDefinition.get_discovery_url')
    @mock.patch('magnum.drivers.heat.template_def.BaseTemplateDefinition'
                '.get_params')
    @mock.patch('magnum.drivers.heat.template_def.TemplateDefinition'
                '.get_output')
    @mock.patch('magnum.conductor.handlers.common.cert_manager'
                '.sign_node_certificate')
    @mock.patch('magnum.common.x509.operations.generate_csr_and_key')
    def test_k8s_get_params(self, mock_generate_csr_and_key,
                            mock_sign_node_certificate,
                            mock_get_output, mock_get_params,
                            mock_get_discovery_url, mock_osc_class,
                            mock_enable_octavia,
                            mock_get_fixed_network_name,
                            mock_set_master_lb_allowed_cidrs,
                            mock_get_subnet):
        mock_generate_csr_and_key.return_value = {'csr': 'csr',
                                                  'private_key': 'private_key',
                                                  'public_key': 'public_key'}
        mock_sign_node_certificate.return_value = 'signed_cert'
        mock_enable_octavia.return_value = False
        mock_context = mock.MagicMock()
        mock_context.auth_token = 'AUTH_TOKEN'
        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.tls_disabled = False
        mock_cluster_template.registry_enabled = False
        mock_cluster_template.network_driver = 'flannel'
        external_network_id = '17e4e301-b7f3-4996-b3dd-97b3a700174b'
        mock_cluster_template.external_network_id = external_network_id
        mock_cluster_template.no_proxy = ""
        mock_cluster = mock.MagicMock()
        fixed_network_name = 'fixed_network'
        mock_get_fixed_network_name.return_value = fixed_network_name
        fixed_network = '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'
        mock_cluster.fixed_network = fixed_network
        mock_cluster.uuid = '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'
        fixed_subnet = 'f2a6c8b0-a3c2-42a3-b3f4-1f639a523a53'
        mock_cluster.fixed_subnet = fixed_subnet
        del mock_cluster.stack_id
        mock_osc = mock.MagicMock()
        mock_osc.magnum_url.return_value = 'http://127.0.0.1:9511/v1'
        mock_osc.cinder_region_name.return_value = 'RegionOne'
        mock_osc_class.return_value = mock_osc

        mock_get_discovery_url.return_value = 'fake_discovery_url'

        mock_context.auth_url = 'http://192.168.10.10:5000/v3'
        mock_context.user_name = 'fake_user'
        mock_get_subnet.return_value = '20.200.0.0/16'

        flannel_cidr = mock_cluster.labels.get('flannel_network_cidr')
        flannel_subnet = mock_cluster.labels.get(
            'flannel_network_subnetlen')
        flannel_backend = mock_cluster.labels.get('flannel_backend')
        heapster_enabled = mock_cluster.labels.get(
            'heapster_enabled')
        metrics_server_enabled = mock_cluster.labels.get(
            'metrics_server_enabled')
        metrics_server_chart_tag = mock_cluster.labels.get(
            'metrics_server_chart_tag')
        system_pods_initial_delay = mock_cluster.labels.get(
            'system_pods_initial_delay')
        system_pods_timeout = mock_cluster.labels.get(
            'system_pods_timeout')
        admission_control_list = mock_cluster.labels.get(
            'admission_control_list')
        prometheus_monitoring = mock_cluster.labels.get(
            'prometheus_monitoring')
        grafana_admin_passwd = mock_cluster.labels.get(
            'grafana_admin_passwd')
        kube_dashboard_enabled = mock_cluster.labels.get(
            'kube_dashboard_enabled')
        influx_grafana_dashboard_enabled = mock_cluster.labels.get(
            'influx_grafana_dashboard_enabled')
        docker_volume_type = mock_cluster.labels.get(
            'docker_volume_type')
        boot_volume_size = mock_cluster.labels.get(
            'boot_volume_size')
        etcd_volume_size = mock_cluster.labels.get(
            'etcd_volume_size')
        kube_tag = mock_cluster.labels.get('kube_tag')
        etcd_tag = mock_cluster.labels.get('etcd_tag')
        coredns_tag = mock_cluster.labels.get('coredns_tag')
        flannel_tag = mock_cluster.labels.get('flannel_tag')
        flannel_cni_tag = mock_cluster.labels.get('flannel_cni_tag')
        container_infra_prefix = mock_cluster.labels.get(
            'container_infra_prefix')
        availability_zone = mock_cluster.labels.get(
            'availability_zone')
        cert_manager_api = mock_cluster.labels.get('cert_manager_api')
        calico_tag = mock_cluster.labels.get(
            'calico_tag')
        calico_kube_controllers_tag = mock_cluster.labels.get(
            'calico_kube_controllers_tag')
        calico_ipv4pool = mock_cluster.labels.get(
            'calico_ipv4pool')
        calico_ipv4pool_ipip = mock_cluster.labels.get(
            'calico_ipv4pool_ipip')
        if mock_cluster_template.network_driver == 'flannel':
            pods_network_cidr = flannel_cidr
        elif mock_cluster_template.network_driver == 'calico':
            pods_network_cidr = calico_ipv4pool
        cgroup_driver = mock_cluster.labels.get(
            'cgroup_driver')
        ingress_controller = mock_cluster.labels.get(
            'ingress_controller').lower()
        ingress_controller_role = mock_cluster.labels.get(
            'ingress_controller_role')
        octavia_ingress_controller_tag = mock_cluster.labels.get(
            'octavia_ingress_controller_tag')
        nginx_ingress_controller_tag = mock_cluster.labels.get(
            'nginx_ingress_controller_tag')
        nginx_ingress_controller_chart_tag = mock_cluster.labels.get(
            'nginx_ingress_controller_chart_tag')
        kubelet_options = mock_cluster.labels.get(
            'kubelet_options')
        kubeapi_options = mock_cluster.labels.get(
            'kubeapi_options')
        kubecontroller_options = mock_cluster.labels.get(
            'kubecontroller_options')
        kubescheduler_options = mock_cluster.labels.get(
            'kubescheduler_options')
        kubeproxy_options = mock_cluster.labels.get(
            'kubeproxy_options')
        cloud_provider_enabled = mock_cluster.labels.get(
            'cloud_provider_enabled')
        cloud_provider_tag = mock_cluster.labels.get(
            'cloud_provider_tag')
        service_cluster_ip_range = mock_cluster.labels.get(
            'service_cluster_ip_range')
        prometheus_tag = mock_cluster.labels.get(
            'prometheus_tag')
        grafana_tag = mock_cluster.labels.get(
            'grafana_tag')
        heat_container_agent_tag = mock_cluster.labels.get(
            'heat_container_agent_tag')
        keystone_auth_enabled = mock_cluster.labels.get(
            'keystone_auth_enabled')
        k8s_keystone_auth_tag = mock_cluster.labels.get(
            'k8s_keystone_auth_tag')
        monitoring_enabled = mock_cluster.labels.get(
            'monitoring_enabled')
        prometheus_operator_chart_tag = mock_cluster.labels.get(
            'prometheus_operator_chart_tag')
        prometheus_adapter_enabled = mock_cluster.labels.get(
            'prometheus_adapter_enabled')
        prometheus_adapter_chart_tag = mock_cluster.labels.get(
            'prometheus_adapter_chart_tag')
        prometheus_adapter_configmap = mock_cluster.labels.get(
            'prometheus_adapter_configmap')
        project_id = mock_cluster.project_id
        tiller_enabled = mock_cluster.labels.get(
            'tiller_enabled')
        tiller_tag = mock_cluster.labels.get(
            'tiller_tag')
        tiller_namespace = mock_cluster.labels.get(
            'tiller_namespace')
        helm_client_url = mock_cluster.labels.get(
            'helm_client_url')
        helm_client_sha256 = mock_cluster.labels.get(
            'helm_client_sha256')
        helm_client_tag = mock_cluster.labels.get(
            'helm_client_tag')
        npd_tag = mock_cluster.labels.get('node_problem_detector_tag')
        traefik_ingress_controller_tag = mock_cluster.labels.get(
            'traefik_ingress_controller_tag')
        auto_healing_enabled = mock_cluster.labels.get(
            'auto_healing_enabled')
        auto_healing_controller = mock_cluster.labels.get(
            'auto_healing_controller')
        magnum_auto_healer_tag = mock_cluster.labels.get(
            'magnum_auto_healer_tag')
        auto_scaling_enabled = mock_cluster.labels.get(
            'auto_scaling_enabled')
        cinder_csi_enabled = mock_cluster.labels.get(
            'cinder_csi_enabled')
        cinder_csi_plugin_tag = mock_cluster.labels.get(
            'cinder_csi_plugin_tag')
        csi_attacher_tag = mock_cluster.labels.get(
            'csi_attacher_tag')
        csi_provisioner_tag = mock_cluster.labels.get(
            'csi_provisioner_tag')
        csi_snapshotter_tag = mock_cluster.labels.get(
            'csi_snapshotter_tag')
        csi_resizer_tag = mock_cluster.labels.get(
            'csi_resizer_tag')
        csi_node_driver_registrar_tag = mock_cluster.labels.get(
            'csi_node_driver_registrar_tag')
        draino_tag = mock_cluster.labels.get('draino_tag')
        autoscaler_tag = mock_cluster.labels.get('autoscaler_tag')
        min_node_count = mock_cluster.labels.get('min_node_count')
        max_node_count = mock_cluster.labels.get('max_node_count')
        npd_enabled = mock_cluster.labels.get('npd_enabled')
        boot_volume_size = mock_cluster.labels.get('boot_volume_size')
        boot_volume_type = mock_cluster.labels.get('boot_volume_type')
        etcd_volume_type = mock_cluster.labels.get('etcd_volume_type')
        ostree_remote = mock_cluster.labels.get('ostree_remote')
        ostree_commit = mock_cluster.labels.get('ostree_commit')
        use_podman = mock_cluster.labels.get('use_podman')
        selinux_mode = mock_cluster.labels.get('selinux_mode')
        container_runtime = mock_cluster.labels.get('container_runtime')
        containerd_version = mock_cluster.labels.get('containerd_version')
        containerd_tarball_url = mock_cluster.labels.get(
            'containerd_tarball_url')
        containerd_tarball_sha256 = mock_cluster.labels.get(
            'containerd_tarball_sha256')
        kube_image_digest = mock_cluster.labels.get('kube_image_digest')
        metrics_scraper_tag = mock_cluster.labels.get('metrics_scraper_tag')
        master_lb_allowed_cidrs = mock_cluster.labels.get(
            'master_lb_allowed_cidrs')

        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()

        k8s_def.get_params(mock_context, mock_cluster_template, mock_cluster)

        expected_kwargs = {'extra_params': {
            'discovery_url': 'fake_discovery_url',
            'flannel_network_cidr': flannel_cidr,
            'flannel_network_subnetlen': flannel_subnet,
            'flannel_backend': flannel_backend,
            'heapster_enabled': heapster_enabled,
            'metrics_server_enabled': metrics_server_enabled,
            'metrics_server_chart_tag': metrics_server_chart_tag,
            'system_pods_initial_delay': system_pods_initial_delay,
            'system_pods_timeout': system_pods_timeout,
            'admission_control_list': admission_control_list,
            'prometheus_monitoring': prometheus_monitoring,
            'grafana_admin_passwd': grafana_admin_passwd,
            'kube_dashboard_enabled': kube_dashboard_enabled,
            'influx_grafana_dashboard_enabled':
                influx_grafana_dashboard_enabled,
            'docker_volume_type': docker_volume_type,
            'boot_volume_size': boot_volume_size,
            'etcd_volume_size': etcd_volume_size,
            'kubelet_options': kubelet_options,
            'kubeapi_options': kubeapi_options,
            'kubecontroller_options': kubecontroller_options,
            'kubescheduler_options': kubescheduler_options,
            'kubeproxy_options': kubeproxy_options,
            'cloud_provider_enabled': cloud_provider_enabled,
            'cloud_provider_tag': cloud_provider_tag,
            'username': 'fake_user',
            'magnum_url': mock_osc.magnum_url.return_value,
            'region_name': mock_osc.cinder_region_name.return_value,
            'kube_tag': kube_tag,
            'etcd_tag': etcd_tag,
            'coredns_tag': coredns_tag,
            'fixed_network_name': fixed_network_name,
            'fixed_subnet': fixed_subnet,
            'flannel_tag': flannel_tag,
            'flannel_cni_tag': flannel_cni_tag,
            'container_infra_prefix': container_infra_prefix,
            'nodes_affinity_policy': 'soft-anti-affinity',
            'availability_zone': availability_zone,
            'cert_manager_api': cert_manager_api,
            'calico_tag': calico_tag,
            'calico_kube_controllers_tag': calico_kube_controllers_tag,
            'calico_ipv4pool': calico_ipv4pool,
            'calico_ipv4pool_ipip': calico_ipv4pool_ipip,
            'cgroup_driver': cgroup_driver,
            'pods_network_cidr': pods_network_cidr,
            'ingress_controller': ingress_controller,
            'ingress_controller_role': ingress_controller_role,
            'octavia_ingress_controller_tag': octavia_ingress_controller_tag,
            'nginx_ingress_controller_tag': nginx_ingress_controller_tag,
            'nginx_ingress_controller_chart_tag':
                nginx_ingress_controller_chart_tag,
            'octavia_enabled': False,
            'kube_service_account_key': 'public_key',
            'kube_service_account_private_key': 'private_key',
            'portal_network_cidr': service_cluster_ip_range,
            'prometheus_tag': prometheus_tag,
            'grafana_tag': grafana_tag,
            'heat_container_agent_tag': heat_container_agent_tag,
            'keystone_auth_enabled': keystone_auth_enabled,
            'k8s_keystone_auth_tag': k8s_keystone_auth_tag,
            'monitoring_enabled': monitoring_enabled,
            'prometheus_operator_chart_tag': prometheus_operator_chart_tag,
            'prometheus_adapter_enabled': prometheus_adapter_enabled,
            'prometheus_adapter_chart_tag': prometheus_adapter_chart_tag,
            'prometheus_adapter_configmap': prometheus_adapter_configmap,
            'project_id': project_id,
            'external_network': external_network_id,
            'tiller_enabled': tiller_enabled,
            'tiller_tag': tiller_tag,
            'tiller_namespace': tiller_namespace,
            'helm_client_url': helm_client_url,
            'helm_client_sha256': helm_client_sha256,
            'helm_client_tag': helm_client_tag,
            'node_problem_detector_tag': npd_tag,
            'auto_healing_enabled': auto_healing_enabled,
            'auto_healing_controller': auto_healing_controller,
            'magnum_auto_healer_tag': magnum_auto_healer_tag,
            'auto_scaling_enabled': auto_scaling_enabled,
            'cinder_csi_enabled': cinder_csi_enabled,
            'cinder_csi_plugin_tag': cinder_csi_plugin_tag,
            'csi_attacher_tag': csi_attacher_tag,
            'csi_provisioner_tag': csi_provisioner_tag,
            'csi_snapshotter_tag': csi_snapshotter_tag,
            'csi_resizer_tag': csi_resizer_tag,
            'csi_node_driver_registrar_tag': csi_node_driver_registrar_tag,
            'draino_tag': draino_tag,
            'autoscaler_tag': autoscaler_tag,
            'min_node_count': min_node_count,
            'max_node_count': max_node_count,
            'traefik_ingress_controller_tag': traefik_ingress_controller_tag,
            'npd_enabled': npd_enabled,
            'kube_version': kube_tag,
            'master_kube_tag': kube_tag,
            'minion_kube_tag': kube_tag,
            'boot_volume_size': boot_volume_size,
            'boot_volume_type': boot_volume_type,
            'etcd_volume_type': etcd_volume_type,
            'ostree_remote': ostree_remote,
            'ostree_commit': ostree_commit,
            'use_podman': use_podman,
            'selinux_mode': selinux_mode,
            'kube_image_digest': kube_image_digest,
            'container_runtime': container_runtime,
            'containerd_version': containerd_version,
            'containerd_tarball_url': containerd_tarball_url,
            'containerd_tarball_sha256': containerd_tarball_sha256,
            'post_install_manifest_url': '',
            'metrics_scraper_tag': metrics_scraper_tag,
            'master_lb_allowed_cidrs': master_lb_allowed_cidrs,
            'fixed_subnet_cidr': '20.200.0.0/16',
        }}
        mock_get_params.assert_called_once_with(mock_context,
                                                mock_cluster_template,
                                                mock_cluster,
                                                **expected_kwargs)

        mock_cluster_template.volume_driver = 'cinder'
        mock_cluster.labels = {'cloud_provider_enabled': 'false'}
        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()
        self.assertRaises(
            exception.InvalidParameterValue,
            k8s_def.get_params,
            mock_context,
            mock_cluster_template,
            mock_cluster,
        )
        actual_params = mock_get_params.call_args[1]["extra_params"]
        self.assertEqual(
            fixed_network_name,
            actual_params.get("fixed_network_name")
        )
        mock_get_fixed_network_name.assert_called_once_with(
            mock_context,
            mock_cluster.fixed_network
        )

    @mock.patch('magnum.common.neutron.get_subnet')
    @mock.patch('magnum.common.neutron.get_external_network_id')
    @mock.patch('magnum.common.keystone.is_octavia_enabled')
    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch('magnum.drivers.k8s_fedora_atomic_v1.template_def'
                '.AtomicK8sTemplateDefinition.get_discovery_url')
    @mock.patch('magnum.drivers.heat.template_def.BaseTemplateDefinition'
                '.get_params')
    @mock.patch('magnum.drivers.heat.template_def.TemplateDefinition'
                '.get_output')
    @mock.patch('magnum.common.x509.operations.generate_csr_and_key')
    def test_k8s_get_params_external_network_id(self,
                                                mock_generate_csr_and_key,
                                                mock_get_output,
                                                mock_get_params,
                                                mock_get_discovery_url,
                                                mock_osc_class,
                                                mock_enable_octavia,
                                                mock_get_external_network_id,
                                                mock_get_subnet):
        mock_generate_csr_and_key.return_value = {'csr': 'csr',
                                                  'private_key': 'private_key',
                                                  'public_key': 'public_key'}
        mock_enable_octavia.return_value = False
        mock_get_discovery_url.return_value = 'fake_discovery_url'
        external_network_id = 'e2a6c8b0-a3c2-42a3-b3f4-01400a30896e'
        mock_get_external_network_id.return_value = external_network_id

        mock_context = mock.MagicMock()
        mock_context.auth_token = 'AUTH_TOKEN'
        mock_context.auth_url = 'http://192.168.10.10:5000/v3'
        mock_context.user_name = 'fake_user'

        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.tls_disabled = False
        mock_cluster_template.registry_enabled = False
        mock_cluster_template.network_driver = 'calico'
        mock_cluster_template.external_network_id = 'public'

        mock_cluster = mock.MagicMock()
        mock_cluster.labels = {}
        mock_cluster.uuid = '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'
        mock_cluster.project_id = 'e2a6c8b0-a3c2-42a3-b3f4-1f639a523a52'
        mock_cluster.fixed_subnet = 'f2a6c8b0-a3c2-42a3-b3f4-1f639a523a53'

        mock_osc = mock.MagicMock()
        mock_osc.magnum_url.return_value = 'http://127.0.0.1:9511/v1'
        mock_osc.cinder_region_name.return_value = 'RegionOne'
        mock_osc_class.return_value = mock_osc

        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()
        k8s_def.get_params(mock_context, mock_cluster_template, mock_cluster)

        actual_params = mock_get_params.call_args[1]["extra_params"]
        self.assertEqual(
            external_network_id,
            actual_params.get("external_network")
        )
        mock_get_external_network_id.assert_called_once_with(
            mock_context,
            mock_cluster_template.external_network_id
        )

    @mock.patch('magnum.common.neutron.get_subnet')
    @mock.patch('magnum.common.keystone.is_octavia_enabled')
    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch('magnum.drivers.k8s_fedora_atomic_v1.template_def'
                '.AtomicK8sTemplateDefinition.get_discovery_url')
    @mock.patch('magnum.drivers.heat.template_def.BaseTemplateDefinition'
                '.get_params')
    @mock.patch('magnum.drivers.heat.template_def.TemplateDefinition'
                '.get_output')
    @mock.patch('magnum.common.x509.operations.generate_csr_and_key')
    def test_k8s_get_params_octavia_disabled(self,
                                             mock_generate_csr_and_key,
                                             mock_get_output,
                                             mock_get_params,
                                             mock_get_discovery_url,
                                             mock_osc_class,
                                             mock_enable_octavia,
                                             mock_get_subnet):
        mock_generate_csr_and_key.return_value = {'csr': 'csr',
                                                  'private_key': 'private_key',
                                                  'public_key': 'public_key'}
        mock_enable_octavia.return_value = False
        mock_get_discovery_url.return_value = 'fake_discovery_url'

        mock_context = mock.MagicMock()
        mock_context.auth_token = 'AUTH_TOKEN'
        mock_context.auth_url = 'http://192.168.10.10:5000/v3'
        mock_context.user_name = 'fake_user'

        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.tls_disabled = False
        mock_cluster_template.registry_enabled = False
        mock_cluster_template.network_driver = 'calico'
        external_network_id = 'e2a6c8b0-a3c2-42a3-b3f4-01400a30896e'
        mock_cluster_template.external_network_id = external_network_id

        mock_cluster = mock.MagicMock()
        mock_cluster.labels = {"ingress_controller": "octavia"}
        mock_cluster.uuid = '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'
        mock_cluster.project_id = 'e2a6c8b0-a3c2-42a3-b3f4-1f639a523a52'
        mock_cluster.fixed_subnet = 'f2a6c8b0-a3c2-42a3-b3f4-1f639a523a53'

        mock_osc = mock.MagicMock()
        mock_osc.magnum_url.return_value = 'http://127.0.0.1:9511/v1'
        mock_osc.cinder_region_name.return_value = 'RegionOne'
        mock_osc_class.return_value = mock_osc

        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()

        self.assertRaises(
            exception.InvalidParameterValue,
            k8s_def.get_params,
            mock_context,
            mock_cluster_template,
            mock_cluster,
        )

    @mock.patch('magnum.common.neutron.get_subnet')
    @mock.patch('magnum.common.keystone.is_octavia_enabled')
    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch('magnum.drivers.k8s_fedora_atomic_v1.template_def'
                '.AtomicK8sTemplateDefinition.get_discovery_url')
    @mock.patch('magnum.drivers.heat.template_def.BaseTemplateDefinition'
                '.get_params')
    @mock.patch('magnum.drivers.heat.template_def.TemplateDefinition'
                '.get_output')
    @mock.patch('magnum.common.x509.operations.generate_csr_and_key')
    def test_k8s_get_params_octavia_enabled(self,
                                            mock_generate_csr_and_key,
                                            mock_get_output,
                                            mock_get_params,
                                            mock_get_discovery_url,
                                            mock_osc_class,
                                            mock_enable_octavia,
                                            mock_get_subnet):
        mock_generate_csr_and_key.return_value = {'csr': 'csr',
                                                  'private_key': 'private_key',
                                                  'public_key': 'public_key'}
        mock_enable_octavia.return_value = True
        mock_get_discovery_url.return_value = 'fake_discovery_url'

        mock_context = mock.MagicMock()
        mock_context.auth_token = 'AUTH_TOKEN'
        mock_context.auth_url = 'http://192.168.10.10:5000/v3'
        mock_context.user_name = 'fake_user'

        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.tls_disabled = False
        mock_cluster_template.registry_enabled = False
        mock_cluster_template.network_driver = 'calico'
        external_network_id = 'e2a6c8b0-a3c2-42a3-b3f4-01400a30896e'
        mock_cluster_template.external_network_id = external_network_id

        mock_cluster = mock.MagicMock()
        mock_cluster.labels = {"ingress_controller": "octavia"}
        mock_cluster.uuid = '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'
        mock_cluster.project_id = 'e2a6c8b0-a3c2-42a3-b3f4-1f639a523a52'
        mock_cluster.fixed_subnet = 'f2a6c8b0-a3c2-42a3-b3f4-1f639a523a53'

        mock_osc = mock.MagicMock()
        mock_osc.magnum_url.return_value = 'http://127.0.0.1:9511/v1'
        mock_osc.cinder_region_name.return_value = 'RegionOne'
        mock_osc_class.return_value = mock_osc

        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()
        k8s_def.get_params(mock_context, mock_cluster_template, mock_cluster)

        actual_params = mock_get_params.call_args[1]["extra_params"]
        self.assertEqual(
            "octavia",
            actual_params.get("ingress_controller")
        )

    @mock.patch('magnum.common.neutron.get_subnet')
    @mock.patch('magnum.drivers.heat.k8s_template_def.K8sTemplateDefinition'
                '._set_master_lb_allowed_cidrs')
    @mock.patch('magnum.common.keystone.is_octavia_enabled')
    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch('magnum.drivers.heat.template_def'
                '.BaseTemplateDefinition.get_discovery_url')
    @mock.patch('magnum.drivers.heat.template_def.BaseTemplateDefinition'
                '.get_params')
    @mock.patch('magnum.drivers.heat.template_def.TemplateDefinition'
                '.get_output')
    @mock.patch('magnum.conductor.handlers.common.cert_manager'
                '.sign_node_certificate')
    @mock.patch('magnum.common.x509.operations.generate_csr_and_key')
    def test_k8s_get_params_insecure(self, mock_generate_csr_and_key,
                                     mock_sign_node_certificate,
                                     mock_get_output, mock_get_params,
                                     mock_get_discovery_url, mock_osc_class,
                                     mock_enable_octavia,
                                     mock_set_master_lb_allowed_cidrs,
                                     mock_get_subnet):
        mock_generate_csr_and_key.return_value = {'csr': 'csr',
                                                  'private_key': 'private_key',
                                                  'public_key': 'public_key'}
        mock_sign_node_certificate.return_value = 'signed_cert'
        mock_enable_octavia.return_value = False
        mock_context = mock.MagicMock()
        mock_context.auth_token = 'AUTH_TOKEN'
        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.tls_disabled = True
        mock_cluster_template.registry_enabled = False
        mock_cluster_template.network_driver = 'calico'
        external_network_id = '17e4e301-b7f3-4996-b3dd-97b3a700174b'
        mock_cluster_template.external_network_id = external_network_id
        mock_cluster_template.no_proxy = ""
        mock_cluster = mock.MagicMock()
        fixed_network_name = 'fixed_network'
        mock_cluster.fixed_network = fixed_network_name
        mock_cluster.uuid = '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'
        fixed_subnet = 'f2a6c8b0-a3c2-42a3-b3f4-1f639a523a53'
        mock_cluster.fixed_subnet = fixed_subnet
        del mock_cluster.stack_id
        mock_osc = mock.MagicMock()
        mock_osc.magnum_url.return_value = 'http://127.0.0.1:9511/v1'
        mock_osc.cinder_region_name.return_value
        mock_osc_class.return_value = mock_osc

        mock_get_discovery_url.return_value = 'fake_discovery_url'

        mock_context.auth_url = 'http://192.168.10.10:5000/v3'
        mock_context.user_name = 'fake_user'
        mock_get_subnet.return_value = "20.200.0.0/16"

        flannel_cidr = mock_cluster.labels.get('flannel_network_cidr')
        flannel_subnet = mock_cluster.labels.get(
            'flannel_network_subnetlen')
        flannel_backend = mock_cluster.labels.get('flannel_backend')
        heapster_enabled = mock_cluster.labels.get(
            'heapster_enabled')
        metrics_server_enabled = mock_cluster.labels.get(
            'metrics_server_enabled')
        metrics_server_chart_tag = mock_cluster.labels.get(
            'metrics_server_chart_tag')
        system_pods_initial_delay = mock_cluster.labels.get(
            'system_pods_initial_delay')
        system_pods_timeout = mock_cluster.labels.get(
            'system_pods_timeout')
        admission_control_list = mock_cluster.labels.get(
            'admission_control_list')
        prometheus_monitoring = mock_cluster.labels.get(
            'prometheus_monitoring')
        grafana_admin_passwd = mock_cluster.labels.get(
            'grafana_admin_passwd')
        kube_dashboard_enabled = mock_cluster.labels.get(
            'kube_dashboard_enabled')
        influx_grafana_dashboard_enabled = mock_cluster.labels.get(
            'influx_grafana_dashboard_enabled')
        docker_volume_type = mock_cluster.labels.get(
            'docker_volume_type')
        boot_volume_size = mock_cluster.labels.get(
            'boot_volume_size')
        etcd_volume_size = mock_cluster.labels.get(
            'etcd_volume_size')
        kube_tag = mock_cluster.labels.get('kube_tag')
        etcd_tag = mock_cluster.labels.get('etcd_tag')
        coredns_tag = mock_cluster.labels.get('coredns_tag')
        flannel_tag = mock_cluster.labels.get('flannel_tag')
        flannel_cni_tag = mock_cluster.labels.get('flannel_cni_tag')
        container_infra_prefix = mock_cluster.labels.get(
            'container_infra_prefix')
        availability_zone = mock_cluster.labels.get(
            'availability_zone')
        cert_manager_api = mock_cluster.labels.get('cert_manager_api')
        calico_tag = mock_cluster.labels.get(
            'calico_tag')
        calico_kube_controllers_tag = mock_cluster.labels.get(
            'calico_kube_controllers_tag')
        calico_ipv4pool = mock_cluster.labels.get(
            'calico_ipv4pool')
        calico_ipv4pool_ipip = mock_cluster.labels.get(
            'calico_ipv4pool_ipip')
        if mock_cluster_template.network_driver == 'flannel':
            pods_network_cidr = flannel_cidr
        elif mock_cluster_template.network_driver == 'calico':
            pods_network_cidr = calico_ipv4pool
        cgroup_driver = mock_cluster.labels.get(
            'cgroup_driver')
        ingress_controller = mock_cluster.labels.get(
            'ingress_controller').lower()
        ingress_controller_role = mock_cluster.labels.get(
            'ingress_controller_role')
        octavia_ingress_controller_tag = mock_cluster.labels.get(
            'octavia_ingress_controller_tag')
        nginx_ingress_controller_tag = mock_cluster.labels.get(
            'nginx_ingress_controller_tag')
        nginx_ingress_controller_chart_tag = mock_cluster.labels.get(
            'nginx_ingress_controller_chart_tag')
        kubelet_options = mock_cluster.labels.get(
            'kubelet_options')
        kubeapi_options = mock_cluster.labels.get(
            'kubeapi_options')
        kubecontroller_options = mock_cluster.labels.get(
            'kubecontroller_options')
        kubescheduler_options = mock_cluster.labels.get(
            'kubescheduler_options')
        kubeproxy_options = mock_cluster.labels.get(
            'kubeproxy_options')
        cloud_provider_enabled = mock_cluster.labels.get(
            'cloud_provider_enabled')
        cloud_provider_tag = mock_cluster.labels.get(
            'cloud_provider_tag')
        service_cluster_ip_range = mock_cluster.labels.get(
            'service_cluster_ip_range')
        prometheus_tag = mock_cluster.labels.get(
            'prometheus_tag')
        grafana_tag = mock_cluster.labels.get(
            'grafana_tag')
        heat_container_agent_tag = mock_cluster.labels.get(
            'heat_container_agent_tag')
        keystone_auth_enabled = mock_cluster.labels.get(
            'keystone_auth_enabled')
        k8s_keystone_auth_tag = mock_cluster.labels.get(
            'k8s_keystone_auth_tag')
        monitoring_enabled = mock_cluster.labels.get(
            'monitoring_enabled')
        prometheus_operator_chart_tag = mock_cluster.labels.get(
            'prometheus_operator_chart_tag')
        prometheus_adapter_enabled = mock_cluster.labels.get(
            'prometheus_adapter_enabled')
        prometheus_adapter_chart_tag = mock_cluster.labels.get(
            'prometheus_adapter_chart_tag')
        prometheus_adapter_configmap = mock_cluster.labels.get(
            'prometheus_adapter_configmap')
        project_id = mock_cluster.project_id
        tiller_enabled = mock_cluster.labels.get(
            'tiller_enabled')
        tiller_tag = mock_cluster.labels.get(
            'tiller_tag')
        tiller_namespace = mock_cluster.labels.get(
            'tiller_namespace')
        helm_client_url = mock_cluster.labels.get(
            'helm_client_url')
        helm_client_sha256 = mock_cluster.labels.get(
            'helm_client_sha256')
        helm_client_tag = mock_cluster.labels.get(
            'helm_client_tag')
        npd_tag = mock_cluster.labels.get('node_problem_detector_tag')
        traefik_ingress_controller_tag = mock_cluster.labels.get(
            'traefik_ingress_controller_tag')
        auto_healing_enabled = mock_cluster.labels.get(
            'auto_healing_enabled')
        auto_healing_controller = mock_cluster.labels.get(
            'auto_healing_controller')
        magnum_auto_healer_tag = mock_cluster.labels.get(
            'magnum_auto_healer_tag')
        auto_scaling_enabled = mock_cluster.labels.get(
            'auto_scaling_enabled')
        cinder_csi_enabled = mock_cluster.labels.get(
            'cinder_csi_enabled')
        cinder_csi_plugin_tag = mock_cluster.labels.get(
            'cinder_csi_plugin_tag')
        csi_attacher_tag = mock_cluster.labels.get(
            'csi_attacher_tag')
        csi_provisioner_tag = mock_cluster.labels.get(
            'csi_provisioner_tag')
        csi_snapshotter_tag = mock_cluster.labels.get(
            'csi_snapshotter_tag')
        csi_resizer_tag = mock_cluster.labels.get(
            'csi_resizer_tag')
        csi_node_driver_registrar_tag = mock_cluster.labels.get(
            'csi_node_driver_registrar_tag')
        draino_tag = mock_cluster.labels.get('draino_tag')
        autoscaler_tag = mock_cluster.labels.get('autoscaler_tag')
        min_node_count = mock_cluster.labels.get('min_node_count')
        max_node_count = mock_cluster.labels.get('max_node_count')
        npd_enabled = mock_cluster.labels.get('npd_enabled')
        boot_volume_size = mock_cluster.labels.get('boot_volume_size')
        boot_volume_type = mock_cluster.labels.get('boot_volume_type')
        etcd_volume_type = mock_cluster.labels.get('etcd_volume_type')
        ostree_remote = mock_cluster.labels.get('ostree_remote')
        ostree_commit = mock_cluster.labels.get('ostree_commit')
        use_podman = mock_cluster.labels.get('use_podman')
        selinux_mode = mock_cluster.labels.get('selinux_mode')
        container_runtime = mock_cluster.labels.get('container_runtime')
        containerd_version = mock_cluster.labels.get('containerd_version')
        containerd_tarball_url = mock_cluster.labels.get(
            'containerd_tarball_url')
        containerd_tarball_sha256 = mock_cluster.labels.get(
            'containerd_tarball_sha256')
        kube_image_digest = mock_cluster.labels.get('kube_image_digest')
        metrics_scraper_tag = mock_cluster.labels.get('metrics_scraper_tag')

        master_lb_allowed_cidrs = mock_cluster.labels.get(
            'master_lb_allowed_cidrs')

        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()

        k8s_def.get_params(mock_context, mock_cluster_template, mock_cluster)

        expected_kwargs = {'extra_params': {
            'discovery_url': 'fake_discovery_url',
            'flannel_network_cidr': flannel_cidr,
            'flannel_network_subnetlen': flannel_subnet,
            'flannel_backend': flannel_backend,
            'heapster_enabled': heapster_enabled,
            'metrics_server_enabled': metrics_server_enabled,
            'metrics_server_chart_tag': metrics_server_chart_tag,
            'system_pods_initial_delay': system_pods_initial_delay,
            'system_pods_timeout': system_pods_timeout,
            'fixed_network_name': fixed_network_name,
            'fixed_subnet': fixed_subnet,
            'admission_control_list': admission_control_list,
            'prometheus_monitoring': prometheus_monitoring,
            'grafana_admin_passwd': grafana_admin_passwd,
            'kube_dashboard_enabled': kube_dashboard_enabled,
            'influx_grafana_dashboard_enabled':
                influx_grafana_dashboard_enabled,
            'docker_volume_type': docker_volume_type,
            'boot_volume_size': boot_volume_size,
            'etcd_volume_size': etcd_volume_size,
            'kubelet_options': kubelet_options,
            'kubeapi_options': kubeapi_options,
            'kubecontroller_options': kubecontroller_options,
            'kubescheduler_options': kubescheduler_options,
            'kubeproxy_options': kubeproxy_options,
            'cloud_provider_enabled': cloud_provider_enabled,
            'cloud_provider_tag': cloud_provider_tag,
            'username': 'fake_user',
            'magnum_url': mock_osc.magnum_url.return_value,
            'region_name': mock_osc.cinder_region_name.return_value,
            'loadbalancing_protocol': 'HTTP',
            'kubernetes_port': 8080,
            'kube_tag': kube_tag,
            'etcd_tag': etcd_tag,
            'coredns_tag': coredns_tag,
            'flannel_tag': flannel_tag,
            'flannel_cni_tag': flannel_cni_tag,
            'container_infra_prefix': container_infra_prefix,
            'nodes_affinity_policy': 'soft-anti-affinity',
            'availability_zone': availability_zone,
            'cert_manager_api': cert_manager_api,
            'calico_tag': calico_tag,
            'calico_kube_controllers_tag': calico_kube_controllers_tag,
            'calico_ipv4pool': calico_ipv4pool,
            'calico_ipv4pool_ipip': calico_ipv4pool_ipip,
            'cgroup_driver': cgroup_driver,
            'pods_network_cidr': pods_network_cidr,
            'ingress_controller': ingress_controller,
            'ingress_controller_role': ingress_controller_role,
            'octavia_ingress_controller_tag': octavia_ingress_controller_tag,
            'nginx_ingress_controller_tag': nginx_ingress_controller_tag,
            'nginx_ingress_controller_chart_tag':
                nginx_ingress_controller_chart_tag,
            'octavia_enabled': False,
            'kube_service_account_key': 'public_key',
            'kube_service_account_private_key': 'private_key',
            'portal_network_cidr': service_cluster_ip_range,
            'prometheus_tag': prometheus_tag,
            'grafana_tag': grafana_tag,
            'heat_container_agent_tag': heat_container_agent_tag,
            'keystone_auth_enabled': keystone_auth_enabled,
            'k8s_keystone_auth_tag': k8s_keystone_auth_tag,
            'monitoring_enabled': monitoring_enabled,
            'prometheus_operator_chart_tag': prometheus_operator_chart_tag,
            'prometheus_adapter_enabled': prometheus_adapter_enabled,
            'prometheus_adapter_chart_tag': prometheus_adapter_chart_tag,
            'prometheus_adapter_configmap': prometheus_adapter_configmap,
            'project_id': project_id,
            'external_network': external_network_id,
            'tiller_enabled': tiller_enabled,
            'tiller_tag': tiller_tag,
            'tiller_namespace': tiller_namespace,
            'helm_client_url': helm_client_url,
            'helm_client_sha256': helm_client_sha256,
            'helm_client_tag': helm_client_tag,
            'node_problem_detector_tag': npd_tag,
            'auto_healing_enabled': auto_healing_enabled,
            'auto_healing_controller': auto_healing_controller,
            'magnum_auto_healer_tag': magnum_auto_healer_tag,
            'auto_scaling_enabled': auto_scaling_enabled,
            'cinder_csi_enabled': cinder_csi_enabled,
            'cinder_csi_plugin_tag': cinder_csi_plugin_tag,
            'csi_attacher_tag': csi_attacher_tag,
            'csi_provisioner_tag': csi_provisioner_tag,
            'csi_snapshotter_tag': csi_snapshotter_tag,
            'csi_resizer_tag': csi_resizer_tag,
            'csi_node_driver_registrar_tag': csi_node_driver_registrar_tag,
            'draino_tag': draino_tag,
            'autoscaler_tag': autoscaler_tag,
            'min_node_count': min_node_count,
            'max_node_count': max_node_count,
            'traefik_ingress_controller_tag': traefik_ingress_controller_tag,
            'npd_enabled': npd_enabled,
            'kube_version': kube_tag,
            'master_kube_tag': kube_tag,
            'minion_kube_tag': kube_tag,
            'boot_volume_size': boot_volume_size,
            'boot_volume_type': boot_volume_type,
            'etcd_volume_type': etcd_volume_type,
            'ostree_remote': ostree_remote,
            'ostree_commit': ostree_commit,
            'use_podman': use_podman,
            'selinux_mode': selinux_mode,
            'kube_image_digest': kube_image_digest,
            'container_runtime': container_runtime,
            'containerd_version': containerd_version,
            'containerd_tarball_url': containerd_tarball_url,
            'containerd_tarball_sha256': containerd_tarball_sha256,
            'post_install_manifest_url': '',
            'metrics_scraper_tag': metrics_scraper_tag,
            'master_lb_allowed_cidrs': master_lb_allowed_cidrs,
            'fixed_subnet_cidr': '20.200.0.0/16',
        }}
        mock_get_params.assert_called_once_with(mock_context,
                                                mock_cluster_template,
                                                mock_cluster,
                                                **expected_kwargs)

    @mock.patch('requests.get')
    def test_k8s_validate_discovery_url(self, mock_get):
        expected_result = str('{"action":"get","node":{"key":"test","value":'
                              '"1","modifiedIndex":10,"createdIndex":10}}')
        mock_resp = mock.MagicMock()
        mock_resp.text = expected_result
        mock_get.return_value = mock_resp

        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()
        k8s_def.validate_discovery_url('http://etcd/test', 1)

    @mock.patch('requests.get')
    def test_k8s_validate_discovery_url_fail(self, mock_get):
        mock_get.side_effect = req_exceptions.RequestException()

        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()
        self.assertRaises(exception.GetClusterSizeFailed,
                          k8s_def.validate_discovery_url,
                          'http://etcd/test', 1)

    @mock.patch('requests.get')
    def test_k8s_validate_discovery_url_invalid(self, mock_get):
        mock_resp = mock.MagicMock()
        mock_resp.text = str('{"action":"get"}')
        mock_get.return_value = mock_resp

        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()
        self.assertRaises(exception.InvalidClusterDiscoveryURL,
                          k8s_def.validate_discovery_url,
                          'http://etcd/test', 1)

    @mock.patch('requests.get')
    def test_k8s_validate_discovery_url_unexpect_size(self, mock_get):
        expected_result = str('{"action":"get","node":{"key":"test","value":'
                              '"1","modifiedIndex":10,"createdIndex":10}}')
        mock_resp = mock.MagicMock()
        mock_resp.text = expected_result
        mock_get.return_value = mock_resp

        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()
        self.assertRaises(exception.InvalidClusterSize,
                          k8s_def.validate_discovery_url,
                          'http://etcd/test', 5)

    @mock.patch('requests.get')
    def test_k8s_get_discovery_url(self, mock_get):
        CONF.set_override('etcd_discovery_service_endpoint_format',
                          'http://etcd/test?size=%(size)d',
                          group='cluster')
        expected_discovery_url = 'http://etcd/token'
        mock_resp = mock.MagicMock()
        mock_resp.text = expected_discovery_url
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        mock_cluster = mock.MagicMock()
        mock_cluster.master_count = 10
        mock_cluster.discovery_url = None

        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()
        discovery_url = k8s_def.get_discovery_url(mock_cluster)

        mock_get.assert_called_once_with('http://etcd/test?size=10')
        self.assertEqual(expected_discovery_url, mock_cluster.discovery_url)
        self.assertEqual(expected_discovery_url, discovery_url)

    @mock.patch('requests.get')
    def test_k8s_get_discovery_url_fail(self, mock_get):
        CONF.set_override('etcd_discovery_service_endpoint_format',
                          'http://etcd/test?size=%(size)d',
                          group='cluster')
        mock_get.side_effect = req_exceptions.RequestException()
        mock_cluster = mock.MagicMock()
        mock_cluster.master_count = 10
        mock_cluster.discovery_url = None

        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()

        self.assertRaises(exception.GetDiscoveryUrlFailed,
                          k8s_def.get_discovery_url, mock_cluster)

    def test_k8s_get_heat_param(self):
        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()

        k8s_def.add_nodegroup_params(self.mock_cluster)
        heat_param = k8s_def.get_heat_param(nodegroup_attr='node_count',
                                            nodegroup_uuid='worker_ng')
        self.assertEqual('number_of_minions', heat_param)
        heat_param = k8s_def.get_heat_param(nodegroup_attr='node_count',
                                            nodegroup_uuid='master_ng')
        self.assertEqual('number_of_masters', heat_param)

    @mock.patch('requests.get')
    def test_k8s_get_discovery_url_not_found(self, mock_get):
        mock_resp = mock.MagicMock()
        mock_resp.text = ''
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        fake_cluster = mock.MagicMock()
        fake_cluster.discovery_url = None

        self.assertRaises(
            exception.InvalidDiscoveryURL,
            k8sa_tdef.AtomicK8sTemplateDefinition().get_discovery_url,
            fake_cluster)

    def _test_update_outputs_api_address(self, template_definition,
                                         params, tls=True):

        expected_api_address = '%(protocol)s://%(address)s:%(port)s' % params

        outputs = [
            {"output_value": params['address'],
             "description": "No description given",
             "output_key": 'api_address'},
        ]
        mock_stack = mock.MagicMock()
        mock_stack.to_dict.return_value = {'outputs': outputs}
        mock_cluster = mock.MagicMock()
        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.tls_disabled = tls

        template_definition.update_outputs(mock_stack, mock_cluster_template,
                                           mock_cluster)

        self.assertEqual(expected_api_address, mock_cluster.api_address)

    def test_update_k8s_outputs_api_address(self):
        address = 'updated_address'
        protocol = 'http'
        port = '8080'
        params = {
            'protocol': protocol,
            'address': address,
            'port': port,
        }

        template_definition = k8sa_tdef.AtomicK8sTemplateDefinition()
        self._test_update_outputs_api_address(template_definition, params)

    def test_update_swarm_outputs_api_address(self):
        address = 'updated_address'
        protocol = 'tcp'
        port = '2376'
        params = {
            'protocol': protocol,
            'address': address,
            'port': port,
        }

        template_definition = swarm_tdef.AtomicSwarmTemplateDefinition()
        self._test_update_outputs_api_address(template_definition, params)

    def test_update_k8s_outputs_if_cluster_template_is_secure(self):
        address = 'updated_address'
        protocol = 'https'
        port = '6443'
        params = {
            'protocol': protocol,
            'address': address,
            'port': port,
        }
        template_definition = k8sa_tdef.AtomicK8sTemplateDefinition()
        self._test_update_outputs_api_address(template_definition, params,
                                              tls=False)

    def test_update_swarm_outputs_if_cluster_template_is_secure(self):
        address = 'updated_address'
        protocol = 'tcp'
        port = '2376'
        params = {
            'protocol': protocol,
            'address': address,
            'port': port,
        }

        template_definition = swarm_tdef.AtomicSwarmTemplateDefinition()
        self._test_update_outputs_api_address(template_definition, params,
                                              tls=False)

    def _test_update_outputs_none_api_address(self, template_definition,
                                              params, tls=True):

        outputs = [
            {"output_value": params['address'],
             "description": "No description given",
             "output_key": 'api_address'},
        ]
        mock_stack = mock.MagicMock()
        mock_stack.to_dict.return_value = {'outputs': outputs}
        mock_cluster = mock.MagicMock()
        mock_cluster.api_address = 'none_api_address'
        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.tls_disabled = tls

        template_definition.update_outputs(mock_stack, mock_cluster_template,
                                           mock_cluster)

        self.assertEqual('none_api_address', mock_cluster.api_address)

    def test_update_k8s_outputs_none_api_address(self):
        protocol = 'http'
        port = '8080'
        params = {
            'protocol': protocol,
            'address': None,
            'port': port,
        }

        template_definition = k8sa_tdef.AtomicK8sTemplateDefinition()
        self._test_update_outputs_none_api_address(template_definition, params)

    def test_update_swarm_outputs_none_api_address(self):
        protocol = 'tcp'
        port = '2376'
        params = {
            'protocol': protocol,
            'address': None,
            'port': port,
        }
        template_definition = swarm_tdef.AtomicSwarmTemplateDefinition()
        self._test_update_outputs_none_api_address(template_definition, params)

    def test_update_outputs_master_address(self):
        self._test_update_outputs_server_address(
            public_ip_output_key='kube_masters',
            private_ip_output_key='kube_masters_private',
            nodegroup_attr='node_addresses',
            is_master=True
        )

    def test_update_outputs_node_address(self):
        self._test_update_outputs_server_address(
            public_ip_output_key='kube_minions',
            private_ip_output_key='kube_minions_private',
            nodegroup_attr='node_addresses',
            is_master=False
        )

    def test_update_outputs_master_address_fip_disabled(self):
        self._test_update_outputs_server_address(
            floating_ip_enabled=False,
            public_ip_output_key='kube_masters',
            private_ip_output_key='kube_masters_private',
            nodegroup_attr='node_addresses',
            is_master=True
        )

    def test_update_outputs_node_address_fip_disabled(self):
        self._test_update_outputs_server_address(
            floating_ip_enabled=False,
            public_ip_output_key='kube_minions',
            private_ip_output_key='kube_minions_private',
            nodegroup_attr='node_addresses',
            is_master=False
        )

    def test_set_master_lb_allowed_cidrs(self):
        definition = self.get_definition()
        extra_params = {"master_lb_allowed_cidrs": "192.168.0.0/16"}
        mock_cluster = mock.MagicMock()
        mock_context = mock.MagicMock()
        mock_cluster.labels = {}

        definition._set_master_lb_allowed_cidrs(mock_context,
                                                mock_cluster, extra_params)

        self.assertEqual(extra_params["master_lb_allowed_cidrs"],
                         "192.168.0.0/16,10.0.0.0/24")

    def test_set_master_lb_allowed_cidrs_fixed_subnet_cidr(self):
        definition = self.get_definition()
        extra_params = {"master_lb_allowed_cidrs": "192.168.0.0/16"}
        mock_cluster = mock.MagicMock()
        mock_context = mock.MagicMock()
        mock_cluster.labels = {"fixed_subnet_cidr": "100.0.0.0/24"}

        definition._set_master_lb_allowed_cidrs(mock_context,
                                                mock_cluster, extra_params)

        self.assertEqual(extra_params["master_lb_allowed_cidrs"],
                         "192.168.0.0/16,100.0.0.0/24")

    @mock.patch('magnum.common.neutron.get_subnet')
    def test_set_master_lb_allowed_cidrs_find_subnet_cidr(self,
                                                          mock_get_subnet):
        definition = self.get_definition()
        extra_params = {"master_lb_allowed_cidrs": "192.168.0.0/16",
                        "fixed_subnet": "fake_subnet_id"}
        mock_cluster = mock.MagicMock()
        mock_context = mock.MagicMock()
        mock_cluster.labels = {}
        mock_get_subnet.return_value = "172.24.0.0/16"

        definition._set_master_lb_allowed_cidrs(mock_context,
                                                mock_cluster, extra_params)

        self.assertEqual(extra_params["master_lb_allowed_cidrs"],
                         "192.168.0.0/16,172.24.0.0/16")


class FedoraK8sIronicTemplateDefinitionTestCase(base.TestCase):

    def get_definition(self):
        return k8s_i_dr.Driver().get_template_definition()

    def assert_neutron_find(self, mock_neutron_v20_find,
                            osc, cluster_template):
        mock_neutron_v20_find.assert_called_once_with(
            osc.neutron(),
            'subnet',
            cluster_template.fixed_subnet
        )

    def assert_raises_from_get_fixed_network_id(
        self,
        mock_neutron_v20_find,
        exeption_from_neutron_client,
        expected_exception_class
    ):
        definition = self.get_definition()
        osc = mock.MagicMock()
        cluster_template = mock.MagicMock()
        mock_neutron_v20_find.side_effect = exeption_from_neutron_client

        self.assertRaises(
            expected_exception_class,
            definition.get_fixed_network_id,
            osc,
            cluster_template
        )

    @mock.patch('neutronclient.neutron.v2_0.find_resource_by_name_or_id')
    def test_get_fixed_network_id(self, mock_neutron_v20_find):
        expected_network_id = 'expected_network_id'

        osc = mock.MagicMock()
        cluster_template = mock.MagicMock()
        definition = self.get_definition()
        mock_neutron_v20_find.return_value = {
            'ip_version': 4,
            'network_id': expected_network_id,
        }

        self.assertEqual(
            expected_network_id,
            definition.get_fixed_network_id(osc, cluster_template)
        )
        self.assert_neutron_find(mock_neutron_v20_find, osc, cluster_template)

    @mock.patch('neutronclient.neutron.v2_0.find_resource_by_name_or_id')
    def test_get_fixed_network_id_with_invalid_ip_ver(self,
                                                      mock_neutron_v20_find):
        osc = mock.MagicMock()
        cluster_template = mock.MagicMock()
        definition = self.get_definition()
        mock_neutron_v20_find.return_value = {
            'ip_version': 6,
            'network_id': 'expected_network_id',
        }

        self.assertRaises(
            exception.InvalidSubnet,
            definition.get_fixed_network_id,
            osc,
            cluster_template
        )

    @mock.patch('neutronclient.neutron.v2_0.find_resource_by_name_or_id')
    def test_get_fixed_network_id_with_duplicated_name(self,
                                                       mock_neutron_v20_find):
        ex = n_exception.NeutronClientNoUniqueMatch(
            resource='subnet',
            name='duplicated-name'
        )

        self.assert_raises_from_get_fixed_network_id(
            mock_neutron_v20_find,
            ex,
            exception.InvalidSubnet,
        )

    @mock.patch('neutronclient.neutron.v2_0.find_resource_by_name_or_id')
    def test_get_fixed_network_id_with_client_error(self,
                                                    mock_neutron_v20_find):
        ex = n_exception.BadRequest()

        self.assert_raises_from_get_fixed_network_id(
            mock_neutron_v20_find,
            ex,
            exception.InvalidSubnet,
        )

    @mock.patch('neutronclient.neutron.v2_0.find_resource_by_name_or_id')
    def test_get_fixed_network_id_with_server_error(self,
                                                    mock_neutron_v20_find):
        ex = n_exception.ServiceUnavailable()

        self.assert_raises_from_get_fixed_network_id(
            mock_neutron_v20_find,
            ex,
            n_exception.ServiceUnavailable,
        )


class AtomicSwarmModeTemplateDefinitionTestCase(base.TestCase):

    def setUp(self):
        super(AtomicSwarmModeTemplateDefinitionTestCase, self).setUp()
        self.master_ng = mock.MagicMock(uuid='master_ng', role='master')
        self.worker_ng = mock.MagicMock(uuid='worker_ng', role='worker')
        self.nodegroups = [self.master_ng, self.worker_ng]
        self.mock_cluster = mock.MagicMock(nodegroups=self.nodegroups,
                                           default_ng_worker=self.worker_ng,
                                           default_ng_master=self.master_ng)

    def get_definition(self):
        return swarm_v2_dr.Driver().get_template_definition()

    def _test_update_outputs_server_address(
        self,
        floating_ip_enabled=True,
        public_ip_output_key='swarm_nodes',
        private_ip_output_key='swarm_nodes_private',
        cluster_attr=None,
        nodegroup_attr=None,
        is_master=False
    ):

        definition = self.get_definition()

        expected_address = expected_public_address = ['public']
        expected_private_address = ['private']
        if not floating_ip_enabled:
            expected_address = expected_private_address

        outputs = [
            {"output_value": expected_public_address,
             "description": "No description given",
             "output_key": public_ip_output_key},
            {"output_value": expected_private_address,
             "description": "No description given",
             "output_key": private_ip_output_key},
        ]
        mock_stack = mock.MagicMock()
        mock_stack.to_dict.return_value = {'outputs': outputs}
        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.floating_ip_enabled = floating_ip_enabled
        self.mock_cluster.floating_ip_enabled = floating_ip_enabled

        definition.update_outputs(mock_stack, mock_cluster_template,
                                  self.mock_cluster)

        actual = None
        if cluster_attr:
            actual = getattr(self.mock_cluster, cluster_attr)
        elif is_master:
            actual = getattr(self.master_ng, nodegroup_attr)
        else:
            actual = getattr(self.worker_ng, nodegroup_attr)
        self.assertEqual(expected_address, actual)

    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch('magnum.drivers.swarm_fedora_atomic_v2.template_def'
                '.AtomicSwarmTemplateDefinition.get_discovery_url')
    @mock.patch('magnum.drivers.heat.template_def.BaseTemplateDefinition'
                '.get_params')
    @mock.patch('magnum.drivers.heat.template_def.TemplateDefinition'
                '.get_output')
    def test_swarm_get_params(self, mock_get_output, mock_get_params,
                              mock_get_discovery_url, mock_osc_class):
        mock_context = mock.MagicMock()
        mock_context.auth_token = 'AUTH_TOKEN'
        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.tls_disabled = False
        mock_cluster_template.registry_enabled = False
        mock_cluster = mock.MagicMock()
        mock_cluster.uuid = '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'
        del mock_cluster.stack_id
        mock_osc = mock.MagicMock()
        mock_osc.magnum_url.return_value = 'http://127.0.0.1:9511/v1'
        mock_osc_class.return_value = mock_osc

        discovery_url = 'fake_discovery_url'
        mock_get_discovery_url.return_value = discovery_url

        mock_context.auth_url = 'http://192.168.10.10:5000/v3'
        mock_context.user_name = 'fake_user'
        mock_context.tenant = 'fake_tenant'

        docker_volume_type = mock_cluster.labels.get(
            'docker_volume_type')
        rexray_preempt = mock_cluster.labels.get('rexray_preempt')
        availability_zone = mock_cluster.labels.get(
            'availability_zone')

        number_of_secondary_masters = mock_cluster.master_count - 1

        swarm_def = swarm_v2_tdef.AtomicSwarmTemplateDefinition()

        swarm_def.get_params(mock_context, mock_cluster_template, mock_cluster)

        expected_kwargs = {'extra_params': {
            'magnum_url': mock_osc.magnum_url.return_value,
            'auth_url': 'http://192.168.10.10:5000/v3',
            'rexray_preempt': rexray_preempt,
            'docker_volume_type': docker_volume_type,
            'number_of_secondary_masters': number_of_secondary_masters,
            'availability_zone': availability_zone,
            'nodes_affinity_policy': 'soft-anti-affinity'}}
        mock_get_params.assert_called_once_with(mock_context,
                                                mock_cluster_template,
                                                mock_cluster,
                                                **expected_kwargs)

    def test_swarm_get_heat_param(self):
        swarm_def = swarm_v2_tdef.AtomicSwarmTemplateDefinition()

        swarm_def.add_nodegroup_params(self.mock_cluster)
        heat_param = swarm_def.get_heat_param(nodegroup_attr='node_count',
                                              nodegroup_uuid='worker_ng')
        self.assertEqual('number_of_nodes', heat_param)
        heat_param = swarm_def.get_heat_param(cluster_attr='uuid')
        self.assertEqual('cluster_uuid', heat_param)

    def test_swarm_get_scale_params(self):
        mock_context = mock.MagicMock()
        swarm_def = swarm_v2_tdef.AtomicSwarmTemplateDefinition()
        self.assertEqual(
            swarm_def.get_scale_params(mock_context, self.mock_cluster, 7),
            {'number_of_nodes': 7})

    def test_update_outputs(self):
        swarm_def = swarm_v2_tdef.AtomicSwarmTemplateDefinition()

        expected_api_address = 'updated_address'
        expected_node_addresses = ['ex_minion', 'address']

        outputs = [
            {"output_value": expected_api_address,
             "description": "No description given",
             "output_key": "api_address"},
            {"output_value": ['any', 'output'],
             "description": "No description given",
             "output_key": "swarm_master_private"},
            {"output_value": ['any', 'output'],
             "description": "No description given",
             "output_key": "swarm_master"},
            {"output_value": ['any', 'output'],
             "description": "No description given",
             "output_key": "swarm_nodes_private"},
            {"output_value": expected_node_addresses,
             "description": "No description given",
             "output_key": "swarm_nodes"},
        ]
        mock_stack = mock.MagicMock()
        mock_stack.to_dict.return_value = {'outputs': outputs}
        mock_cluster_template = mock.MagicMock()

        swarm_def.update_outputs(mock_stack, mock_cluster_template,
                                 self.mock_cluster)
        expected_api_address = "tcp://%s:2375" % expected_api_address
        self.assertEqual(expected_api_address, self.mock_cluster.api_address)
        self.assertEqual(expected_node_addresses,
                         self.mock_cluster.default_ng_worker.node_addresses)

    def test_update_outputs_master_address(self):
        self._test_update_outputs_server_address(
            public_ip_output_key='swarm_primary_master',
            private_ip_output_key='swarm_primary_master_private',
            nodegroup_attr='node_addresses',
            is_master=True
        )

    def test_update_outputs_node_address(self):
        self._test_update_outputs_server_address(
            public_ip_output_key='swarm_nodes',
            private_ip_output_key='swarm_nodes_private',
            nodegroup_attr='node_addresses',
            is_master=False
        )

    def test_update_outputs_master_address_fip_disabled(self):
        self._test_update_outputs_server_address(
            floating_ip_enabled=False,
            public_ip_output_key='swarm_primary_master',
            private_ip_output_key='swarm_primary_master_private',
            nodegroup_attr='node_addresses',
            is_master=True
        )

    def test_update_outputs_node_address_fip_disabled(self):
        self._test_update_outputs_server_address(
            floating_ip_enabled=False,
            public_ip_output_key='swarm_nodes',
            private_ip_output_key='swarm_nodes_private',
            nodegroup_attr='node_addresses',
            is_master=False
        )


class AtomicSwarmTemplateDefinitionTestCase(base.TestCase):

    def setUp(self):
        super(AtomicSwarmTemplateDefinitionTestCase, self).setUp()
        self.master_ng = mock.MagicMock(uuid='master_ng', role='master')
        self.worker_ng = mock.MagicMock(uuid='worker_ng', role='worker')
        self.nodegroups = [self.master_ng, self.worker_ng]
        self.mock_cluster = mock.MagicMock(nodegroups=self.nodegroups,
                                           default_ng_worker=self.worker_ng,
                                           default_ng_master=self.master_ng)

    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch('magnum.drivers.swarm_fedora_atomic_v1.template_def'
                '.AtomicSwarmTemplateDefinition.get_discovery_url')
    @mock.patch('magnum.drivers.heat.template_def.BaseTemplateDefinition'
                '.get_params')
    @mock.patch('magnum.drivers.heat.template_def.TemplateDefinition'
                '.get_output')
    def test_swarm_get_params(self, mock_get_output, mock_get_params,
                              mock_get_discovery_url, mock_osc_class):
        mock_context = mock.MagicMock()
        mock_context.auth_token = 'AUTH_TOKEN'
        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.tls_disabled = False
        mock_cluster_template.registry_enabled = False
        mock_cluster = mock.MagicMock()
        mock_cluster.uuid = '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'
        del mock_cluster.stack_id
        mock_osc = mock.MagicMock()
        mock_osc.magnum_url.return_value = 'http://127.0.0.1:9511/v1'
        mock_osc_class.return_value = mock_osc

        mock_get_discovery_url.return_value = 'fake_discovery_url'

        mock_context.auth_url = 'http://192.168.10.10:5000/v3'
        mock_context.user_name = 'fake_user'
        mock_context.tenant = 'fake_tenant'

        docker_volume_type = mock_cluster.labels.get(
            'docker_volume_type')
        flannel_cidr = mock_cluster.labels.get('flannel_network_cidr')
        flannel_subnet = mock_cluster.labels.get(
            'flannel_network_subnetlen')
        flannel_backend = mock_cluster.labels.get('flannel_backend')
        rexray_preempt = mock_cluster.labels.get('rexray_preempt')
        swarm_strategy = mock_cluster.labels.get('swarm_strategy')

        swarm_def = swarm_tdef.AtomicSwarmTemplateDefinition()

        swarm_def.get_params(mock_context, mock_cluster_template, mock_cluster)

        expected_kwargs = {'extra_params': {
            'discovery_url': 'fake_discovery_url',
            'magnum_url': mock_osc.magnum_url.return_value,
            'flannel_network_cidr': flannel_cidr,
            'flannel_backend': flannel_backend,
            'flannel_network_subnetlen': flannel_subnet,
            'auth_url': 'http://192.168.10.10:5000/v3',
            'rexray_preempt': rexray_preempt,
            'swarm_strategy': swarm_strategy,
            'docker_volume_type': docker_volume_type,
            'nodes_affinity_policy': 'soft-anti-affinity'}}
        mock_get_params.assert_called_once_with(mock_context,
                                                mock_cluster_template,
                                                mock_cluster,
                                                **expected_kwargs)

    @mock.patch('requests.get')
    def test_swarm_validate_discovery_url(self, mock_get):
        expected_result = str('{"action":"get","node":{"key":"test","value":'
                              '"1","modifiedIndex":10,"createdIndex":10}}')
        mock_resp = mock.MagicMock()
        mock_resp.text = expected_result
        mock_get.return_value = mock_resp

        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()
        k8s_def.validate_discovery_url('http://etcd/test', 1)

    @mock.patch('requests.get')
    def test_swarm_validate_discovery_url_fail(self, mock_get):
        mock_get.side_effect = req_exceptions.RequestException()

        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()
        self.assertRaises(exception.GetClusterSizeFailed,
                          k8s_def.validate_discovery_url,
                          'http://etcd/test', 1)

    @mock.patch('requests.get')
    def test_swarm_validate_discovery_url_invalid(self, mock_get):
        mock_resp = mock.MagicMock()
        mock_resp.text = str('{"action":"get"}')
        mock_get.return_value = mock_resp

        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()
        self.assertRaises(exception.InvalidClusterDiscoveryURL,
                          k8s_def.validate_discovery_url,
                          'http://etcd/test', 1)

    @mock.patch('requests.get')
    def test_swarm_validate_discovery_url_unexpect_size(self, mock_get):
        expected_result = str('{"action":"get","node":{"key":"test","value":'
                              '"1","modifiedIndex":10,"createdIndex":10}}')
        mock_resp = mock.MagicMock()
        mock_resp.text = expected_result
        mock_get.return_value = mock_resp

        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()
        self.assertRaises(exception.InvalidClusterSize,
                          k8s_def.validate_discovery_url,
                          'http://etcd/test', 5)

    @mock.patch('requests.get')
    def test_swarm_get_discovery_url(self, mock_get):
        CONF.set_override('etcd_discovery_service_endpoint_format',
                          'http://etcd/test?size=%(size)d',
                          group='cluster')
        expected_discovery_url = 'http://etcd/token'
        mock_resp = mock.MagicMock()
        mock_resp.text = expected_discovery_url
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        mock_cluster = mock.MagicMock()
        mock_cluster.discovery_url = None

        swarm_def = swarm_tdef.AtomicSwarmTemplateDefinition()
        discovery_url = swarm_def.get_discovery_url(mock_cluster)

        mock_get.assert_called_once_with('http://etcd/test?size=1')
        self.assertEqual(mock_cluster.discovery_url, expected_discovery_url)
        self.assertEqual(discovery_url, expected_discovery_url)

    @mock.patch('requests.get')
    def test_swarm_get_discovery_url_not_found(self, mock_get):
        mock_resp = mock.MagicMock()
        mock_resp.text = ''
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        fake_cluster = mock.MagicMock()
        fake_cluster.discovery_url = None

        self.assertRaises(
            exception.InvalidDiscoveryURL,
            k8sa_tdef.AtomicK8sTemplateDefinition().get_discovery_url,
            fake_cluster)

    def test_swarm_get_heat_param(self):
        swarm_def = swarm_tdef.AtomicSwarmTemplateDefinition()

        swarm_def.add_nodegroup_params(self.mock_cluster)
        heat_param = swarm_def.get_heat_param(nodegroup_attr='node_count',
                                              nodegroup_uuid='worker_ng')
        self.assertEqual('number_of_nodes', heat_param)

    def test_update_outputs(self):
        swarm_def = swarm_tdef.AtomicSwarmTemplateDefinition()

        expected_api_address = 'updated_address'
        expected_node_addresses = ['ex_minion', 'address']

        outputs = [
            {"output_value": expected_api_address,
             "description": "No description given",
             "output_key": "api_address"},
            {"output_value": ['any', 'output'],
             "description": "No description given",
             "output_key": "swarm_master_private"},
            {"output_value": ['any', 'output'],
             "description": "No description given",
             "output_key": "swarm_master"},
            {"output_value": ['any', 'output'],
             "description": "No description given",
             "output_key": "swarm_nodes_private"},
            {"output_value": expected_node_addresses,
             "description": "No description given",
             "output_key": "swarm_nodes"},
        ]
        mock_stack = mock.MagicMock()
        mock_stack.to_dict.return_value = {'outputs': outputs}
        mock_cluster_template = mock.MagicMock()

        swarm_def.update_outputs(mock_stack, mock_cluster_template,
                                 self.mock_cluster)
        expected_api_address = "tcp://%s:2376" % expected_api_address
        self.assertEqual(expected_api_address, self.mock_cluster.api_address)
        self.assertEqual(expected_node_addresses,
                         self.worker_ng.node_addresses)


class UbuntuMesosTemplateDefinitionTestCase(base.TestCase):

    def setUp(self):
        super(UbuntuMesosTemplateDefinitionTestCase, self).setUp()
        self.master_ng = mock.MagicMock(uuid='master_ng', role='master')
        self.worker_ng = mock.MagicMock(uuid='worker_ng', role='worker')
        self.nodegroups = [self.master_ng, self.worker_ng]
        self.mock_cluster = mock.MagicMock(nodegroups=self.nodegroups,
                                           default_ng_worker=self.worker_ng,
                                           default_ng_master=self.master_ng)

    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch('magnum.drivers.heat.template_def.BaseTemplateDefinition'
                '.get_params')
    def test_mesos_get_params(self,
                              mock_get_params,
                              mock_osc_class):
        mock_context = mock.MagicMock()
        mock_context.auth_url = 'http://192.168.10.10:5000/v3'
        mock_context.user_name = 'mesos_user'
        mock_context.project_id = 'admin'
        mock_context.domain_name = 'domainname'
        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.tls_disabled = False
        mock_cluster = mock.MagicMock()
        mock_cluster.uuid = '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'
        del mock_cluster.stack_id
        rexray_preempt = mock_cluster.labels.get('rexray_preempt')
        mesos_slave_isolation = mock_cluster.labels.get(
            'mesos_slave_isolation')
        mesos_slave_work_dir = mock_cluster.labels.get(
            'mesos_slave_work_dir')
        mesos_slave_image_providers = mock_cluster.labels.get(
            'image_providers')
        mesos_slave_executor_env_variables = mock_cluster.labels.get(
            'mesos_slave_executor_env_variables')
        mock_osc = mock.MagicMock()
        mock_osc.cinder_region_name.return_value = 'RegionOne'
        mock_osc_class.return_value = mock_osc

        mesos_def = mesos_tdef.UbuntuMesosTemplateDefinition()

        CONF.set_override('nodes_affinity_policy',
                          'anti-affinity',
                          group='cluster')

        mesos_def.get_params(mock_context, mock_cluster_template, mock_cluster)

        expected_kwargs = {'extra_params': {
            'region_name': mock_osc.cinder_region_name.return_value,
            'nodes_affinity_policy': 'anti-affinity',
            'auth_url': 'http://192.168.10.10:5000/v3',
            'username': 'mesos_user',
            'tenant_name': 'admin',
            'domain_name': 'domainname',
            'rexray_preempt': rexray_preempt,
            'mesos_slave_isolation': mesos_slave_isolation,
            'mesos_slave_work_dir': mesos_slave_work_dir,
            'mesos_slave_executor_env_variables':
                mesos_slave_executor_env_variables,
            'mesos_slave_image_providers': mesos_slave_image_providers}}
        mock_get_params.assert_called_once_with(mock_context,
                                                mock_cluster_template,
                                                mock_cluster,
                                                **expected_kwargs)

    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch('magnum.drivers.heat.template_def.TemplateDefinition'
                '.get_output')
    def test_mesos_get_scale_params(self, mock_get_output,
                                    mock_osc_class):
        mock_context = mock.MagicMock()
        mock_cluster = mock.MagicMock()
        mock_cluster.uuid = '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'

        removal_nodes = ['node1', 'node2']
        node_count = 7
        mock_scale_manager = mock.MagicMock()
        mock_scale_manager.get_removal_nodes.return_value = removal_nodes

        mesos_def = mesos_tdef.UbuntuMesosTemplateDefinition()

        scale_params = mesos_def.get_scale_params(
            mock_context,
            mock_cluster,
            node_count,
            mock_scale_manager)
        expected_scale_params = {'slaves_to_remove': ['node1', 'node2'],
                                 'number_of_slaves': 7}
        self.assertEqual(scale_params, expected_scale_params)

    def test_mesos_get_heat_param(self):
        mesos_def = mesos_tdef.UbuntuMesosTemplateDefinition()

        mesos_def.add_nodegroup_params(self.mock_cluster)

        heat_param = mesos_def.get_heat_param(nodegroup_attr='node_count',
                                              nodegroup_uuid='worker_ng')
        self.assertEqual('number_of_slaves', heat_param)

        heat_param = mesos_def.get_heat_param(nodegroup_attr='node_count',
                                              nodegroup_uuid='master_ng')
        self.assertEqual('number_of_masters', heat_param)

    def test_update_outputs(self):
        mesos_def = mesos_tdef.UbuntuMesosTemplateDefinition()

        expected_api_address = 'updated_address'
        expected_node_addresses = ['ex_slave', 'address']
        expected_master_addresses = ['ex_master', 'address']

        outputs = [
            {"output_value": expected_api_address,
             "description": "No description given",
             "output_key": "api_address"},
            {"output_value": ['any', 'output'],
             "description": "No description given",
             "output_key": "mesos_master_private"},
            {"output_value": expected_master_addresses,
             "description": "No description given",
             "output_key": "mesos_master"},
            {"output_value": ['any', 'output'],
             "description": "No description given",
             "output_key": "mesos_slaves_private"},
            {"output_value": expected_node_addresses,
             "description": "No description given",
             "output_key": "mesos_slaves"},
        ]
        mock_stack = mock.MagicMock()
        mock_stack.to_dict.return_value = {'outputs': outputs}
        mock_cluster_template = mock.MagicMock()

        mesos_def.update_outputs(mock_stack, mock_cluster_template,
                                 self.mock_cluster)

        self.assertEqual(expected_api_address, self.mock_cluster.api_address)
        self.assertEqual(expected_node_addresses,
                         self.mock_cluster.default_ng_worker.node_addresses)
        self.assertEqual(expected_master_addresses,
                         self.mock_cluster.default_ng_master.node_addresses)
