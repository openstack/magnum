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
import mock
from neutronclient.common import exceptions as n_exception
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
        mock_stack.to_dict.return_value = {'outputs': heat_outputs}

        output = cmn_tdef.OutputMapping('key1')
        value = output.get_output_value(mock_stack)
        self.assertEqual('value1', value)

        output = cmn_tdef.OutputMapping('key2')
        value = output.get_output_value(mock_stack)
        self.assertEqual(["value2", "value3"], value)

        output = cmn_tdef.OutputMapping('key3')
        value = output.get_output_value(mock_stack)
        self.assertIsNone(value)

        # verify stack with no 'outputs' attribute
        mock_stack.to_dict.return_value = {}
        output = cmn_tdef.OutputMapping('key1')
        value = output.get_output_value(mock_stack)
        self.assertIsNone(value)

    def test_add_output_with_mapping_type(self):
        definition = k8sa_dr.Driver().get_template_definition()

        mock_args = [1, 3, 4]
        mock_kwargs = {'test': 'test'}
        mock_mapping_type = mock.MagicMock()
        mock_mapping_type.return_value = mock.MagicMock()
        definition.add_output(mapping_type=mock_mapping_type, *mock_args,
                              **mock_kwargs)

        mock_mapping_type.assert_called_once_with(*mock_args, **mock_kwargs)
        self.assertIn(mock_mapping_type.return_value,
                      definition.output_mappings)


@six.add_metaclass(abc.ABCMeta)
class BaseTemplateDefinitionTestCase(base.TestCase):

    @abc.abstractmethod
    def get_definition(self):
        """Returns the template definition."""
        pass

    def _test_update_outputs_server_addrtess(
        self,
        floating_ip_enabled=True,
        public_ip_output_key='kube_masters',
        private_ip_output_key='kube_masters_private',
        cluster_attr='master_addresses',
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
        mock_cluster = mock.MagicMock()
        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.floating_ip_enabled = floating_ip_enabled

        definition.update_outputs(mock_stack, mock_cluster_template,
                                  mock_cluster)

        self.assertEqual(expected_address, getattr(mock_cluster, cluster_attr))


class AtomicK8sTemplateDefinitionTestCase(BaseTemplateDefinitionTestCase):

    def get_definition(self):
        return k8sa_dr.Driver().get_template_definition()

    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch('magnum.drivers.k8s_fedora_atomic_v1.template_def'
                '.AtomicK8sTemplateDefinition.get_discovery_url')
    @mock.patch('magnum.drivers.heat.template_def.BaseTemplateDefinition'
                '.get_params')
    @mock.patch('magnum.drivers.heat.template_def.TemplateDefinition'
                '.get_output')
    def test_k8s_get_params(self, mock_get_output, mock_get_params,
                            mock_get_discovery_url, mock_osc_class):
        mock_context = mock.MagicMock()
        mock_context.auth_token = 'AUTH_TOKEN'
        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.tls_disabled = False
        mock_cluster_template.registry_enabled = False
        mock_cluster = mock.MagicMock()
        mock_cluster.uuid = '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'
        del mock_cluster.stack_id
        mock_scale_manager = mock.MagicMock()
        mock_osc = mock.MagicMock()
        mock_osc.magnum_url.return_value = 'http://127.0.0.1:9511/v1'
        mock_osc.cinder_region_name.return_value = 'RegionOne'
        mock_osc_class.return_value = mock_osc

        removal_nodes = ['node1', 'node2']
        mock_scale_manager.get_removal_nodes.return_value = removal_nodes
        mock_get_discovery_url.return_value = 'fake_discovery_url'

        mock_context.auth_url = 'http://192.168.10.10:5000/v3'
        mock_context.user_name = 'fake_user'

        flannel_cidr = mock_cluster_template.labels.get('flannel_network_cidr')
        flannel_subnet = mock_cluster_template.labels.get(
            'flannel_network_subnetlen')
        flannel_backend = mock_cluster_template.labels.get('flannel_backend')
        system_pods_initial_delay = mock_cluster_template.labels.get(
            'system_pods_initial_delay')
        system_pods_timeout = mock_cluster_template.labels.get(
            'system_pods_timeout')
        admission_control_list = mock_cluster_template.labels.get(
            'admission_control_list')
        prometheus_monitoring = mock_cluster_template.labels.get(
            'prometheus_monitoring')
        grafana_admin_passwd = mock_cluster_template.labels.get(
            'grafana_admin_passwd')
        kube_dashboard_enabled = mock_cluster_template.labels.get(
            'kube_dashboard_enabled')
        docker_volume_type = mock_cluster_template.labels.get(
            'docker_volume_type')
        etcd_volume_size = mock_cluster_template.labels.get(
            'etcd_volume_size')
        kube_tag = mock_cluster_template.labels.get('kube_tag')

        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()

        k8s_def.get_params(mock_context, mock_cluster_template, mock_cluster,
                           scale_manager=mock_scale_manager)

        expected_kwargs = {'extra_params': {
            'minions_to_remove': removal_nodes,
            'discovery_url': 'fake_discovery_url',
            'flannel_network_cidr': flannel_cidr,
            'flannel_network_subnetlen': flannel_subnet,
            'flannel_backend': flannel_backend,
            'system_pods_initial_delay': system_pods_initial_delay,
            'system_pods_timeout': system_pods_timeout,
            'admission_control_list': admission_control_list,
            'prometheus_monitoring': prometheus_monitoring,
            'grafana_admin_passwd': grafana_admin_passwd,
            'kube_dashboard_enabled': kube_dashboard_enabled,
            'docker_volume_type': docker_volume_type,
            'etcd_volume_size': etcd_volume_size,
            'username': 'fake_user',
            'magnum_url': mock_osc.magnum_url.return_value,
            'region_name': mock_osc.cinder_region_name.return_value,
            'kube_tag': kube_tag}}
        mock_get_params.assert_called_once_with(mock_context,
                                                mock_cluster_template,
                                                mock_cluster,
                                                **expected_kwargs)

    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch('magnum.drivers.heat.template_def'
                '.BaseTemplateDefinition.get_discovery_url')
    @mock.patch('magnum.drivers.heat.template_def.BaseTemplateDefinition'
                '.get_params')
    @mock.patch('magnum.drivers.heat.template_def.TemplateDefinition'
                '.get_output')
    def test_k8s_get_params_insecure(self, mock_get_output, mock_get_params,
                                     mock_get_discovery_url, mock_osc_class):
        mock_context = mock.MagicMock()
        mock_context.auth_token = 'AUTH_TOKEN'
        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.tls_disabled = True
        mock_cluster_template.registry_enabled = False
        mock_cluster = mock.MagicMock()
        mock_cluster.uuid = '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'
        del mock_cluster.stack_id
        mock_scale_manager = mock.MagicMock()
        mock_osc = mock.MagicMock()
        mock_osc.magnum_url.return_value = 'http://127.0.0.1:9511/v1'
        mock_osc.cinder_region_name.return_value
        mock_osc_class.return_value = mock_osc

        removal_nodes = ['node1', 'node2']
        mock_scale_manager.get_removal_nodes.return_value = removal_nodes
        mock_get_discovery_url.return_value = 'fake_discovery_url'

        mock_context.auth_url = 'http://192.168.10.10:5000/v3'
        mock_context.user_name = 'fake_user'

        flannel_cidr = mock_cluster_template.labels.get('flannel_network_cidr')
        flannel_subnet = mock_cluster_template.labels.get(
            'flannel_network_subnetlen')
        flannel_backend = mock_cluster_template.labels.get('flannel_backend')
        system_pods_initial_delay = mock_cluster_template.labels.get(
            'system_pods_initial_delay')
        system_pods_timeout = mock_cluster_template.labels.get(
            'system_pods_timeout')
        admission_control_list = mock_cluster_template.labels.get(
            'admission_control_list')
        prometheus_monitoring = mock_cluster_template.labels.get(
            'prometheus_monitoring')
        grafana_admin_passwd = mock_cluster_template.labels.get(
            'grafana_admin_passwd')
        kube_dashboard_enabled = mock_cluster_template.labels.get(
            'kube_dashboard_enabled')
        docker_volume_type = mock_cluster_template.labels.get(
            'docker_volume_type')
        etcd_volume_size = mock_cluster_template.labels.get(
            'etcd_volume_size')
        kube_tag = mock_cluster_template.labels.get('kube_tag')

        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()

        k8s_def.get_params(mock_context, mock_cluster_template, mock_cluster,
                           scale_manager=mock_scale_manager)

        expected_kwargs = {'extra_params': {
            'minions_to_remove': removal_nodes,
            'discovery_url': 'fake_discovery_url',
            'flannel_network_cidr': flannel_cidr,
            'flannel_network_subnetlen': flannel_subnet,
            'flannel_backend': flannel_backend,
            'system_pods_initial_delay': system_pods_initial_delay,
            'system_pods_timeout': system_pods_timeout,
            'admission_control_list': admission_control_list,
            'prometheus_monitoring': prometheus_monitoring,
            'grafana_admin_passwd': grafana_admin_passwd,
            'kube_dashboard_enabled': kube_dashboard_enabled,
            'docker_volume_type': docker_volume_type,
            'etcd_volume_size': etcd_volume_size,
            'username': 'fake_user',
            'magnum_url': mock_osc.magnum_url.return_value,
            'region_name': mock_osc.cinder_region_name.return_value,
            'loadbalancing_protocol': 'HTTP',
            'kubernetes_port': 8080,
            'kube_tag': kube_tag}}
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

        mock_get.assert_called_once_with('http://etcd/test?size=10',
                                         proxies={})
        self.assertEqual(expected_discovery_url, mock_cluster.discovery_url)
        self.assertEqual(expected_discovery_url, discovery_url)

    @mock.patch('requests.get')
    def test_k8s_get_discovery_url_proxy(self, mock_get):
        CONF.set_override('etcd_discovery_service_endpoint_format',
                          'http://etcd/test?size=%(size)d',
                          group='cluster')
        expected_discovery_url = 'http://etcd/token'
        mock_resp = mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = expected_discovery_url
        mock_get.return_value = mock_resp
        mock_cluster = mock.MagicMock()
        mock_cluster.master_count = 10
        mock_cluster.discovery_url = None

        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.http_proxy = 'http_proxy'
        mock_cluster_template.https_proxy = 'https_proxy'
        mock_cluster_template.no_proxy = 'localhost,127.0.0.1'

        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()
        discovery_url = k8s_def.get_discovery_url(mock_cluster,
                                                  mock_cluster_template)

        mock_get.assert_called_once_with('http://etcd/test?size=10', proxies={
            'http': 'http_proxy', 'https': 'https_proxy'})
        self.assertEqual(expected_discovery_url, mock_cluster.discovery_url)
        self.assertEqual(expected_discovery_url, discovery_url)

    @mock.patch('requests.get')
    def test_k8s_get_discovery_url_no_proxy(self, mock_get):
        CONF.set_override('etcd_discovery_service_endpoint_format',
                          'http://etcd/test?size=%(size)d',
                          group='cluster')
        expected_discovery_url = 'http://etcd/token'
        mock_resp = mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = expected_discovery_url
        mock_get.return_value = mock_resp
        mock_cluster = mock.MagicMock()
        mock_cluster.master_count = 10
        mock_cluster.discovery_url = None

        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.http_proxy = 'http_proxy'
        mock_cluster_template.https_proxy = 'https_proxy'
        mock_cluster_template.no_proxy = 'localhost,127.0.0.1,etcd'

        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()
        discovery_url = k8s_def.get_discovery_url(mock_cluster,
                                                  mock_cluster_template)

        mock_get.assert_called_once_with('http://etcd/test?size=10',
                                         proxies={})
        self.assertEqual(expected_discovery_url, mock_cluster.discovery_url)
        self.assertEqual(expected_discovery_url, discovery_url)

    @mock.patch('requests.get')
    def test_k8s_get_discovery_url_no_proxy_wildcard(self, mock_get):
        CONF.set_override('etcd_discovery_service_endpoint_format',
                          'http://etcd/test?size=%(size)d',
                          group='cluster')
        expected_discovery_url = 'http://etcd/token'
        mock_resp = mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = expected_discovery_url
        mock_get.return_value = mock_resp
        mock_cluster = mock.MagicMock()
        mock_cluster.master_count = 10
        mock_cluster.discovery_url = None

        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.http_proxy = 'http_proxy'
        mock_cluster_template.https_proxy = 'https_proxy'
        mock_cluster_template.no_proxy = '*'

        k8s_def = k8sa_tdef.AtomicK8sTemplateDefinition()
        discovery_url = k8s_def.get_discovery_url(mock_cluster,
                                                  mock_cluster_template)

        mock_get.assert_called_once_with('http://etcd/test?size=10',
                                         proxies={})
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

        heat_param = k8s_def.get_heat_param(cluster_attr='node_count')
        self.assertEqual('number_of_minions', heat_param)

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
        self._test_update_outputs_server_addrtess(
            public_ip_output_key='kube_masters',
            private_ip_output_key='kube_masters_private',
            cluster_attr='master_addresses',
        )

    def test_update_outputs_node_address(self):
        self._test_update_outputs_server_addrtess(
            public_ip_output_key='kube_minions',
            private_ip_output_key='kube_minions_private',
            cluster_attr='node_addresses',
        )

    def test_update_outputs_master_address_fip_disabled(self):
        self._test_update_outputs_server_addrtess(
            floating_ip_enabled=False,
            public_ip_output_key='kube_masters',
            private_ip_output_key='kube_masters_private',
            cluster_attr='master_addresses',
        )

    def test_update_outputs_node_address_fip_disabled(self):
        self._test_update_outputs_server_addrtess(
            floating_ip_enabled=False,
            public_ip_output_key='kube_minions',
            private_ip_output_key='kube_minions_private',
            cluster_attr='node_addresses',
        )


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


class AtomicSwarmTemplateDefinitionTestCase(base.TestCase):

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

        docker_volume_type = mock_cluster_template.labels.get(
            'docker_volume_type')
        flannel_cidr = mock_cluster_template.labels.get('flannel_network_cidr')
        flannel_subnet = mock_cluster_template.labels.get(
            'flannel_network_subnetlen')
        flannel_backend = mock_cluster_template.labels.get('flannel_backend')
        rexray_preempt = mock_cluster_template.labels.get('rexray_preempt')
        swarm_strategy = mock_cluster_template.labels.get('swarm_strategy')

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
            'docker_volume_type': docker_volume_type}}
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

        mock_get.assert_called_once_with('http://etcd/test?size=1', proxies={})
        self.assertEqual(mock_cluster.discovery_url, expected_discovery_url)
        self.assertEqual(discovery_url, expected_discovery_url)

    @mock.patch('requests.get')
    def test_swarm_get_discovery_url_proxy(self, mock_get):
        CONF.set_override('etcd_discovery_service_endpoint_format',
                          'http://etcd/test?size=%(size)d',
                          group='cluster')
        expected_discovery_url = 'http://etcd/token'
        mock_resp = mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = expected_discovery_url
        mock_get.return_value = mock_resp
        mock_cluster = mock.MagicMock()
        mock_cluster.discovery_url = None

        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.http_proxy = 'http_proxy'
        mock_cluster_template.https_proxy = 'https_proxy'
        mock_cluster_template.no_proxy = 'localhost,127.0.0.1'

        swarm_def = swarm_tdef.AtomicSwarmTemplateDefinition()
        discovery_url = swarm_def.get_discovery_url(mock_cluster,
                                                    mock_cluster_template)

        mock_get.assert_called_once_with('http://etcd/test?size=1', proxies={
            'http': 'http_proxy', 'https': 'https_proxy'})
        self.assertEqual(mock_cluster.discovery_url, expected_discovery_url)
        self.assertEqual(discovery_url, expected_discovery_url)

    @mock.patch('requests.get')
    def test_swarm_get_discovery_url_no_proxy(self, mock_get):
        CONF.set_override('etcd_discovery_service_endpoint_format',
                          'http://etcd/test?size=%(size)d',
                          group='cluster')
        expected_discovery_url = 'http://etcd/token'
        mock_resp = mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = expected_discovery_url
        mock_get.return_value = mock_resp
        mock_cluster = mock.MagicMock()
        mock_cluster.discovery_url = None

        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.http_proxy = 'http_proxy'
        mock_cluster_template.https_proxy = 'https_proxy'
        mock_cluster_template.no_proxy = 'etcd,localhost,127.0.0.1'

        swarm_def = swarm_tdef.AtomicSwarmTemplateDefinition()
        discovery_url = swarm_def.get_discovery_url(mock_cluster)

        mock_get.assert_called_once_with('http://etcd/test?size=1', proxies={})
        self.assertEqual(mock_cluster.discovery_url, expected_discovery_url)
        self.assertEqual(discovery_url, expected_discovery_url)

    @mock.patch('requests.get')
    def test_swarm_get_discovery_url_no_proxy_wildcard(self, mock_get):
        CONF.set_override('etcd_discovery_service_endpoint_format',
                          'http://etcd/test?size=%(size)d',
                          group='cluster')
        expected_discovery_url = 'http://etcd/token'
        mock_resp = mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = expected_discovery_url
        mock_get.return_value = mock_resp
        mock_cluster = mock.MagicMock()
        mock_cluster.discovery_url = None

        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.http_proxy = 'http_proxy'
        mock_cluster_template.https_proxy = 'https_proxy'
        mock_cluster_template.no_proxy = '*'

        swarm_def = swarm_tdef.AtomicSwarmTemplateDefinition()
        discovery_url = swarm_def.get_discovery_url(mock_cluster)

        mock_get.assert_called_once_with('http://etcd/test?size=1', proxies={})
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

        heat_param = swarm_def.get_heat_param(cluster_attr='node_count')
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
        mock_cluster = mock.MagicMock()
        mock_cluster_template = mock.MagicMock()

        swarm_def.update_outputs(mock_stack, mock_cluster_template,
                                 mock_cluster)
        expected_api_address = "tcp://%s:2376" % expected_api_address
        self.assertEqual(expected_api_address, mock_cluster.api_address)
        self.assertEqual(expected_node_addresses, mock_cluster.node_addresses)


class UbuntuMesosTemplateDefinitionTestCase(base.TestCase):

    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch('magnum.drivers.heat.template_def.BaseTemplateDefinition'
                '.get_params')
    @mock.patch('magnum.drivers.heat.template_def.TemplateDefinition'
                '.get_output')
    def test_mesos_get_params(self, mock_get_output, mock_get_params,
                              mock_osc_class):
        mock_context = mock.MagicMock()
        mock_context.auth_url = 'http://192.168.10.10:5000/v3'
        mock_context.user_name = 'mesos_user'
        mock_context.tenant = 'admin'
        mock_context.domain_name = 'domainname'
        mock_cluster_template = mock.MagicMock()
        mock_cluster_template.tls_disabled = False
        rexray_preempt = mock_cluster_template.labels.get('rexray_preempt')
        mesos_slave_isolation = mock_cluster_template.labels.get(
            'mesos_slave_isolation')
        mesos_slave_work_dir = mock_cluster_template.labels.get(
            'mesos_slave_work_dir')
        mesos_slave_image_providers = mock_cluster_template.labels.get(
            'image_providers')
        mesos_slave_executor_env_variables = mock_cluster_template.labels.get(
            'mesos_slave_executor_env_variables')
        mock_cluster = mock.MagicMock()
        mock_cluster.uuid = '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'
        del mock_cluster.stack_id
        mock_osc = mock.MagicMock()
        mock_osc.cinder_region_name.return_value = 'RegionOne'
        mock_osc_class.return_value = mock_osc

        removal_nodes = ['node1', 'node2']
        mock_scale_manager = mock.MagicMock()
        mock_scale_manager.get_removal_nodes.return_value = removal_nodes

        mesos_def = mesos_tdef.UbuntuMesosTemplateDefinition()

        mesos_def.get_params(mock_context, mock_cluster_template, mock_cluster,
                             scale_manager=mock_scale_manager)

        expected_kwargs = {'extra_params': {
            'region_name': mock_osc.cinder_region_name.return_value,
            'auth_url': 'http://192.168.10.10:5000/v3',
            'username': 'mesos_user',
            'tenant_name': 'admin',
            'domain_name': 'domainname',
            'rexray_preempt': rexray_preempt,
            'mesos_slave_isolation': mesos_slave_isolation,
            'mesos_slave_work_dir': mesos_slave_work_dir,
            'mesos_slave_executor_env_variables':
                mesos_slave_executor_env_variables,
            'mesos_slave_image_providers': mesos_slave_image_providers,
            'slaves_to_remove': removal_nodes}}
        mock_get_params.assert_called_once_with(mock_context,
                                                mock_cluster_template,
                                                mock_cluster,
                                                **expected_kwargs)

    def test_mesos_get_heat_param(self):
        mesos_def = mesos_tdef.UbuntuMesosTemplateDefinition()

        heat_param = mesos_def.get_heat_param(cluster_attr='node_count')
        self.assertEqual('number_of_slaves', heat_param)

        heat_param = mesos_def.get_heat_param(cluster_attr='master_count')
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
        mock_cluster = mock.MagicMock()
        mock_cluster_template = mock.MagicMock()

        mesos_def.update_outputs(mock_stack, mock_cluster_template,
                                 mock_cluster)

        self.assertEqual(expected_api_address, mock_cluster.api_address)
        self.assertEqual(expected_node_addresses, mock_cluster.node_addresses)
        self.assertEqual(expected_master_addresses,
                         mock_cluster.master_addresses)
