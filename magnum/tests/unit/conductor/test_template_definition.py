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

import mock
from oslo_config import cfg

from magnum.common import exception
from magnum.conductor import template_definition as tdef
from magnum.tests import base


class TemplateDefinitionTestCase(base.TestCase):

    @mock.patch.object(tdef, 'iter_entry_points')
    def test_load_entry_points(self, mock_iter_entry_points):
        mock_entry_point = mock.MagicMock()
        mock_entry_points = [mock_entry_point]
        mock_iter_entry_points.return_value = mock_entry_points.__iter__()

        entry_points = tdef.TemplateDefinition.load_entry_points()

        for (expected_entry_point,
             (actual_entry_point, loaded_cls)) in zip(mock_entry_points,
                                                      entry_points):
            self.assertEqual(expected_entry_point, actual_entry_point)
            expected_entry_point.load.assert_called_once_with(require=False)

    def test_get_template_definitions(self):
        defs = tdef.TemplateDefinition.get_template_definitions()

        vm_atomic_k8s = defs[('vm', 'fedora-atomic', 'kubernetes')]
        vm_coreos_k8s = defs[('vm', 'coreos', 'kubernetes')]

        self.assertEqual(1, len(vm_atomic_k8s))
        self.assertEqual(tdef.AtomicK8sTemplateDefinition,
                         vm_atomic_k8s['magnum_vm_atomic_k8s'])
        self.assertEqual(1, len(vm_coreos_k8s))
        self.assertEqual(tdef.CoreOSK8sTemplateDefinition,
                         vm_coreos_k8s['magnum_vm_coreos_k8s'])

    def test_get_vm_atomic_kubernetes_definition(self):
        definition = tdef.TemplateDefinition.get_template_definition(
            'vm',
            'fedora-atomic',
            'kubernetes')

        self.assertIsInstance(definition,
                              tdef.AtomicK8sTemplateDefinition)

    def test_get_vm_coreos_kubernetes_definition(self):
        definition = tdef.TemplateDefinition.get_template_definition(
            'vm',
            'coreos',
            'kubernetes')

        self.assertIsInstance(definition,
                              tdef.CoreOSK8sTemplateDefinition)

    def test_get_vm_atomic_swarm_definition(self):
        definition = tdef.TemplateDefinition.get_template_definition(
            'vm',
            'fedora-atomic',
            'swarm')

        self.assertIsInstance(definition,
                              tdef.AtomicSwarmTemplateDefinition)

    def test_get_vm_ubuntu_mesos_definition(self):
        definition = tdef.TemplateDefinition.get_template_definition(
            'vm',
            'ubuntu',
            'mesos')

        self.assertIsInstance(definition,
                              tdef.UbuntuMesosTemplateDefinition)

    def test_get_definition_not_supported(self):
        self.assertRaises(exception.BayTypeNotSupported,
                          tdef.TemplateDefinition.get_template_definition,
                          'vm', 'not_supported', 'kubernetes')

    def test_get_definition_not_enabled(self):
        cfg.CONF.set_override('enabled_definitions',
                              ['magnum_vm_atomic_k8s'],
                              group='bay')
        self.assertRaises(exception.BayTypeNotEnabled,
                          tdef.TemplateDefinition.get_template_definition,
                          'vm', 'coreos', 'kubernetes')

    def test_required_param_not_set(self):
        param = tdef.ParameterMapping('test', baymodel_attr='test',
                                      required=True)
        mock_baymodel = mock.MagicMock()
        mock_baymodel.test = None

        self.assertRaises(exception.RequiredParameterNotProvided,
                          param.set_param, {}, mock_baymodel, None)

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

        output = tdef.OutputMapping('key1')
        value = output.get_output_value(mock_stack)
        self.assertEqual('value1', value)

        output = tdef.OutputMapping('key2')
        value = output.get_output_value(mock_stack)
        self.assertEqual(["value2", "value3"], value)

        output = tdef.OutputMapping('key3')
        value = output.get_output_value(mock_stack)
        self.assertIsNone(value)

        # verify stack with no 'outputs' attribute
        mock_stack.to_dict.return_value = {}
        output = tdef.OutputMapping('key1')
        value = output.get_output_value(mock_stack)
        self.assertIsNone(value)

    def test_add_output_with_mapping_type(self):
        definition = tdef.TemplateDefinition.get_template_definition(
            'vm',
            'fedora-atomic',
            'kubernetes')

        mock_args = [1, 3, 4]
        mock_kwargs = {'test': 'test'}
        mock_mapping_type = mock.MagicMock()
        mock_mapping_type.return_value = mock.MagicMock()
        definition.add_output(mapping_type=mock_mapping_type, *mock_args,
                              **mock_kwargs)

        mock_mapping_type.assert_called_once_with(*mock_args, **mock_kwargs)
        self.assertIn(mock_mapping_type.return_value,
                      definition.output_mappings)


class AtomicK8sTemplateDefinitionTestCase(base.TestCase):

    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch('magnum.conductor.template_definition'
                '.AtomicK8sTemplateDefinition.get_discovery_url')
    @mock.patch('magnum.conductor.template_definition.BaseTemplateDefinition'
                '.get_params')
    @mock.patch('magnum.conductor.template_definition.TemplateDefinition'
                '.get_output')
    def test_k8s_get_params(self, mock_get_output, mock_get_params,
                            mock_get_discovery_url, mock_osc_class):
        mock_context = mock.MagicMock()
        mock_context.auth_token = 'AUTH_TOKEN'
        mock_baymodel = mock.MagicMock()
        mock_baymodel.tls_disabled = False
        mock_baymodel.registry_enabled = False
        mock_bay = mock.MagicMock()
        mock_bay.uuid = '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'
        del mock_bay.stack_id
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
        mock_context.tenant = 'fake_tenant'

        flannel_cidr = mock_baymodel.labels.get('flannel_network_cidr')
        flannel_subnet = mock_baymodel.labels.get('flannel_network_subnetlen')
        flannel_backend = mock_baymodel.labels.get('flannel_backend')

        k8s_def = tdef.AtomicK8sTemplateDefinition()

        k8s_def.get_params(mock_context, mock_baymodel, mock_bay,
                           scale_manager=mock_scale_manager)

        expected_kwargs = {'extra_params': {
            'minions_to_remove': removal_nodes,
            'discovery_url': 'fake_discovery_url',
            'flannel_network_cidr': flannel_cidr,
            'flannel_network_subnetlen': flannel_subnet,
            'flannel_backend': flannel_backend,
            'username': 'fake_user',
            'tenant_name': 'fake_tenant',
            'magnum_url': mock_osc.magnum_url.return_value,
            'region_name': mock_osc.cinder_region_name.return_value}}
        mock_get_params.assert_called_once_with(mock_context, mock_baymodel,
                                                mock_bay, **expected_kwargs)

    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch('magnum.conductor.template_definition'
                '.AtomicK8sTemplateDefinition.get_discovery_url')
    @mock.patch('magnum.conductor.template_definition.BaseTemplateDefinition'
                '.get_params')
    @mock.patch('magnum.conductor.template_definition.TemplateDefinition'
                '.get_output')
    def test_k8s_get_params_insecure(self, mock_get_output, mock_get_params,
                                     mock_get_discovery_url, mock_osc_class):
        mock_context = mock.MagicMock()
        mock_context.auth_token = 'AUTH_TOKEN'
        mock_baymodel = mock.MagicMock()
        mock_baymodel.tls_disabled = True
        mock_baymodel.registry_enabled = False
        mock_bay = mock.MagicMock()
        mock_bay.uuid = '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'
        del mock_bay.stack_id
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
        mock_context.tenant = 'fake_tenant'

        flannel_cidr = mock_baymodel.labels.get('flannel_network_cidr')
        flannel_subnet = mock_baymodel.labels.get('flannel_network_subnetlen')
        flannel_backend = mock_baymodel.labels.get('flannel_backend')

        k8s_def = tdef.AtomicK8sTemplateDefinition()

        k8s_def.get_params(mock_context, mock_baymodel, mock_bay,
                           scale_manager=mock_scale_manager)

        expected_kwargs = {'extra_params': {
            'minions_to_remove': removal_nodes,
            'discovery_url': 'fake_discovery_url',
            'flannel_network_cidr': flannel_cidr,
            'flannel_network_subnetlen': flannel_subnet,
            'flannel_backend': flannel_backend,
            'username': 'fake_user',
            'tenant_name': 'fake_tenant',
            'magnum_url': mock_osc.magnum_url.return_value,
            'region_name': mock_osc.cinder_region_name.return_value,
            'loadbalancing_protocol': 'HTTP',
            'kubernetes_port': 8080}}
        mock_get_params.assert_called_once_with(mock_context, mock_baymodel,
                                                mock_bay, **expected_kwargs)

    @mock.patch('requests.get')
    def test_k8s_get_discovery_url(self, mock_get):
        cfg.CONF.set_override('etcd_discovery_service_endpoint_format',
                              'http://etcd/test?size=%(size)d',
                              group='bay')
        expected_discovery_url = 'http://etcd/token'
        mock_resp = mock.MagicMock()
        mock_resp.text = expected_discovery_url
        mock_get.return_value = mock_resp
        mock_bay = mock.MagicMock()
        mock_bay.master_count = 10
        mock_bay.discovery_url = None

        k8s_def = tdef.AtomicK8sTemplateDefinition()
        discovery_url = k8s_def.get_discovery_url(mock_bay)

        mock_get.assert_called_once_with('http://etcd/test?size=10')
        self.assertEqual(expected_discovery_url, mock_bay.discovery_url)
        self.assertEqual(expected_discovery_url, discovery_url)

    @mock.patch('requests.get')
    def test_k8s_get_discovery_url_fail(self, mock_get):
        cfg.CONF.set_override('etcd_discovery_service_endpoint_format',
                              'http://etcd/test?size=%(size)d',
                              group='bay')
        mock_get.side_effect = Exception()
        mock_bay = mock.MagicMock()
        mock_bay.master_count = 10
        mock_bay.discovery_url = None

        k8s_def = tdef.AtomicK8sTemplateDefinition()

        self.assertRaises(exception.GetDiscoveryUrlFailed,
                          k8s_def.get_discovery_url, mock_bay)

    def test_k8s_get_heat_param(self):
        k8s_def = tdef.AtomicK8sTemplateDefinition()

        heat_param = k8s_def.get_heat_param(bay_attr='node_count')
        self.assertEqual('number_of_minions', heat_param)

    @mock.patch('requests.get')
    def test_k8s_get_discovery_url_not_found(self, mock_get):
        mock_resp = mock.MagicMock()
        mock_resp.text = ''
        mock_get.return_value = mock_resp

        fake_bay = mock.MagicMock()
        fake_bay.discovery_url = None

        self.assertRaises(exception.InvalidDiscoveryURL,
                          tdef.AtomicK8sTemplateDefinition().get_discovery_url,
                          fake_bay)

    def _test_update_outputs_api_address(self, coe, params, tls=True):

        definition = tdef.TemplateDefinition.get_template_definition(
            'vm',
            'fedora-atomic',
            coe)
        expected_api_address = '%(protocol)s://%(address)s:%(port)s' % params

        outputs = [
            {"output_value": params['address'],
             "description": "No description given",
             "output_key": 'api_address'},
        ]
        mock_stack = mock.MagicMock()
        mock_stack.to_dict.return_value = {'outputs': outputs}
        mock_bay = mock.MagicMock()
        mock_baymodel = mock.MagicMock()
        mock_baymodel.tls_disabled = tls

        definition.update_outputs(mock_stack, mock_baymodel, mock_bay)

        self.assertEqual(expected_api_address, mock_bay.api_address)

    def test_update_k8s_outputs_api_address(self):
        address = 'updated_address'
        protocol = 'http'
        port = '8080'
        params = {
            'protocol': protocol,
            'address': address,
            'port': port,
        }
        self._test_update_outputs_api_address('kubernetes', params)

    def test_update_swarm_outputs_api_address(self):
        address = 'updated_address'
        protocol = 'tcp'
        port = '2376'
        params = {
            'protocol': protocol,
            'address': address,
            'port': port,
        }
        self._test_update_outputs_api_address('swarm', params)

    def test_update_k8s_outputs_if_baymodel_is_secure(self):
        address = 'updated_address'
        protocol = 'https'
        port = '6443'
        params = {
            'protocol': protocol,
            'address': address,
            'port': port,
        }
        self._test_update_outputs_api_address('kubernetes', params, tls=False)

    def test_update_swarm_outputs_if_baymodel_is_secure(self):
        address = 'updated_address'
        protocol = 'https'
        port = '2376'
        params = {
            'protocol': protocol,
            'address': address,
            'port': port,
        }
        self._test_update_outputs_api_address('swarm', params, tls=False)


class AtomicSwarmTemplateDefinitionTestCase(base.TestCase):

    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch('magnum.conductor.template_definition'
                '.AtomicSwarmTemplateDefinition.get_discovery_url')
    @mock.patch('magnum.conductor.template_definition.BaseTemplateDefinition'
                '.get_params')
    @mock.patch('magnum.conductor.template_definition.TemplateDefinition'
                '.get_output')
    def test_swarm_get_params(self, mock_get_output, mock_get_params,
                              mock_get_discovery_url, mock_osc_class):
        mock_context = mock.MagicMock()
        mock_context.auth_token = 'AUTH_TOKEN'
        mock_baymodel = mock.MagicMock()
        mock_baymodel.tls_disabled = False
        mock_baymodel.registry_enabled = False
        mock_bay = mock.MagicMock()
        mock_bay.uuid = '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'
        del mock_bay.stack_id
        mock_osc = mock.MagicMock()
        mock_osc.magnum_url.return_value = 'http://127.0.0.1:9511/v1'
        mock_osc_class.return_value = mock_osc

        mock_get_discovery_url.return_value = 'fake_discovery_url'

        mock_context.auth_url = 'http://192.168.10.10:5000/v3'
        mock_context.user_name = 'fake_user'
        mock_context.tenant = 'fake_tenant'

        flannel_cidr = mock_baymodel.labels.get('flannel_network_cidr')
        flannel_subnet = mock_baymodel.labels.get('flannel_network_subnetlen')
        flannel_backend = mock_baymodel.labels.get('flannel_backend')

        swarm_def = tdef.AtomicSwarmTemplateDefinition()

        swarm_def.get_params(mock_context, mock_baymodel, mock_bay)

        expected_kwargs = {'extra_params': {
            'discovery_url': 'fake_discovery_url',
            'magnum_url': mock_osc.magnum_url.return_value,
            'flannel_network_cidr': flannel_cidr,
            'flannel_backend': flannel_backend,
            'flannel_network_subnetlen': flannel_subnet}}
        mock_get_params.assert_called_once_with(mock_context, mock_baymodel,
                                                mock_bay, **expected_kwargs)

    @mock.patch('requests.get')
    def test_swarm_get_discovery_url(self, mock_get):
        cfg.CONF.set_override('etcd_discovery_service_endpoint_format',
                              'http://etcd/test?size=%(size)d',
                              group='bay')
        expected_discovery_url = 'http://etcd/token'
        mock_resp = mock.MagicMock()
        mock_resp.text = expected_discovery_url
        mock_get.return_value = mock_resp
        mock_bay = mock.MagicMock()
        mock_bay.discovery_url = None

        swarm_def = tdef.AtomicSwarmTemplateDefinition()
        discovery_url = swarm_def.get_discovery_url(mock_bay)

        mock_get.assert_called_once_with('http://etcd/test?size=1')
        self.assertEqual(mock_bay.discovery_url, expected_discovery_url)
        self.assertEqual(discovery_url, expected_discovery_url)

    @mock.patch('requests.get')
    def test_swarm_get_discovery_url_not_found(self, mock_get):
        mock_resp = mock.MagicMock()
        mock_resp.text = ''
        mock_get.return_value = mock_resp

        fake_bay = mock.MagicMock()
        fake_bay.discovery_url = None

        self.assertRaises(exception.InvalidDiscoveryURL,
                          tdef.AtomicK8sTemplateDefinition().get_discovery_url,
                          fake_bay)

    def test_swarm_get_heat_param(self):
        swarm_def = tdef.AtomicSwarmTemplateDefinition()

        heat_param = swarm_def.get_heat_param(bay_attr='node_count')
        self.assertEqual('number_of_nodes', heat_param)

    def test_update_outputs(self):
        swarm_def = tdef.AtomicSwarmTemplateDefinition()

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
        mock_bay = mock.MagicMock()
        mock_baymodel = mock.MagicMock()

        swarm_def.update_outputs(mock_stack, mock_baymodel, mock_bay)
        expected_api_address = "tcp://%s:2376" % expected_api_address
        self.assertEqual(expected_api_address, mock_bay.api_address)
        self.assertEqual(expected_node_addresses, mock_bay.node_addresses)


class UbuntuMesosTemplateDefinitionTestCase(base.TestCase):

    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch('magnum.conductor.template_definition.BaseTemplateDefinition'
                '.get_params')
    @mock.patch('magnum.conductor.template_definition.TemplateDefinition'
                '.get_output')
    def test_mesos_get_params(self, mock_get_output, mock_get_params,
                              mock_osc_class):
        mock_context = mock.MagicMock()
        mock_context.auth_url = 'http://192.168.10.10:5000/v3'
        mock_context.user_name = 'mesos_user'
        mock_context.tenant = 'admin'
        mock_context.domain_name = 'domainname'
        mock_baymodel = mock.MagicMock()
        mock_baymodel.tls_disabled = False
        rexray_preempt = mock_baymodel.labels.get('rexray_preempt')
        mesos_slave_isolation = mock_baymodel.labels.get(
            'mesos_slave_isolation')
        mesos_slave_work_dir = mock_baymodel.labels.get('mesos_slave_work_dir')
        mesos_slave_image_providers = mock_baymodel.labels.get(
            'image_providers')
        mesos_slave_executor_env_variables = mock_baymodel.labels.get(
            'mesos_slave_executor_env_variables')
        mock_bay = mock.MagicMock()
        mock_bay.uuid = '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'
        del mock_bay.stack_id
        mock_osc = mock.MagicMock()
        mock_osc.cinder_region_name.return_value = 'RegionOne'
        mock_osc_class.return_value = mock_osc

        mesos_def = tdef.UbuntuMesosTemplateDefinition()

        mesos_def.get_params(mock_context, mock_baymodel, mock_bay)

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
            'mesos_slave_image_providers': mesos_slave_image_providers}}
        mock_get_params.assert_called_once_with(mock_context, mock_baymodel,
                                                mock_bay, **expected_kwargs)

    def test_mesos_get_heat_param(self):
        mesos_def = tdef.UbuntuMesosTemplateDefinition()

        heat_param = mesos_def.get_heat_param(bay_attr='node_count')
        self.assertEqual('number_of_slaves', heat_param)

        heat_param = mesos_def.get_heat_param(bay_attr='master_count')
        self.assertEqual('number_of_masters', heat_param)

    def test_update_outputs(self):
        mesos_def = tdef.UbuntuMesosTemplateDefinition()

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
        mock_bay = mock.MagicMock()
        mock_baymodel = mock.MagicMock()

        mesos_def.update_outputs(mock_stack, mock_baymodel, mock_bay)

        self.assertEqual(expected_api_address, mock_bay.api_address)
        self.assertEqual(expected_node_addresses, mock_bay.node_addresses)
        self.assertEqual(expected_master_addresses, mock_bay.master_addresses)
