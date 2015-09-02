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

        self.assertEqual(len(vm_atomic_k8s), 1)
        self.assertEqual(vm_atomic_k8s['magnum_vm_atomic_k8s'],
                         tdef.AtomicK8sTemplateDefinition)
        self.assertEqual(len(vm_coreos_k8s), 1)
        self.assertEqual(vm_coreos_k8s['magnum_vm_coreos_k8s'],
                         tdef.CoreOSK8sTemplateDefinition)

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
        mock_stack.outputs = heat_outputs

        output = tdef.OutputMapping('key1')
        value = output.get_output_value(mock_stack)
        self.assertEqual(value, 'value1')

        output = tdef.OutputMapping('key2')
        value = output.get_output_value(mock_stack)
        self.assertEqual(value, ["value2", "value3"])

        output = tdef.OutputMapping('key3')
        value = output.get_output_value(mock_stack)
        self.assertIsNone(value)


class AtomicK8sTemplateDefinitionTestCase(base.TestCase):

    @mock.patch('magnum.conductor.template_definition'
                '.AtomicK8sTemplateDefinition.get_discovery_url')
    @mock.patch('magnum.conductor.template_definition.BaseTemplateDefinition'
                '.get_params')
    @mock.patch('magnum.conductor.template_definition.TemplateDefinition'
                '.get_output')
    def test_k8s_get_params(self, mock_get_output, mock_get_params,
                            mock_get_discovery_url):
        mock_context = mock.MagicMock()
        mock_baymodel = mock.MagicMock()
        mock_bay = mock.MagicMock()
        mock_scale_manager = mock.MagicMock()

        removal_nodes = ['node1', 'node2']
        mock_scale_manager.get_removal_nodes.return_value = removal_nodes
        mock_get_discovery_url.return_value = 'fake_discovery_url'
        k8s_def = tdef.AtomicK8sTemplateDefinition()

        k8s_def.get_params(mock_context, mock_baymodel, mock_bay,
                           scale_manager=mock_scale_manager)

        expected_kwargs = {'extra_params': {
            'minions_to_remove': removal_nodes,
            'discovery_url': 'fake_discovery_url'}}
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
        self.assertEqual(mock_bay.discovery_url, expected_discovery_url)
        self.assertEqual(discovery_url, expected_discovery_url)


class AtomicSwarmTemplateDefinitionTestCase(base.TestCase):

    @mock.patch('requests.post')
    def test_swarm_discovery_url_public_token(self, mock_post):

        mock_resp = mock.MagicMock()
        mock_resp.text = 'some_token'
        mock_post.return_value = mock_resp

        mock_bay = mock.MagicMock()
        mock_bay.discovery_url = None
        mock_bay.id = 1
        mock_bay.uuid = 'some_uuid'

        swarm_def = tdef.AtomicSwarmTemplateDefinition()
        actual_url = swarm_def.get_discovery_url(mock_bay)

        self.assertEqual('token://some_token', actual_url)

    def test_swarm_discovery_url_format_bay_id(self):
        cfg.CONF.set_override('public_swarm_discovery', False, group='bay')
        cfg.CONF.set_override('swarm_discovery_url_format',
                              'etcd://test.com/bay-%(bay_id)s', group='bay')

        mock_bay = mock.MagicMock()
        mock_bay.discovery_url = None
        mock_bay.id = 1
        mock_bay.uuid = 'some_uuid'

        swarm_def = tdef.AtomicSwarmTemplateDefinition()
        actual_url = swarm_def.get_discovery_url(mock_bay)

        self.assertEqual('etcd://test.com/bay-1', actual_url)

    def test_swarm_discovery_url_format_bay_uuid(self):
        cfg.CONF.set_override('public_swarm_discovery', False, group='bay')
        cfg.CONF.set_override('swarm_discovery_url_format',
                              'etcd://test.com/bay-%(bay_uuid)s', group='bay')

        mock_bay = mock.MagicMock()
        mock_bay.discovery_url = None
        mock_bay.id = 1
        mock_bay.uuid = 'some_uuid'

        swarm_def = tdef.AtomicSwarmTemplateDefinition()
        actual_url = swarm_def.get_discovery_url(mock_bay)

        self.assertEqual('etcd://test.com/bay-some_uuid', actual_url)

    def test_swarm_discovery_url_from_bay(self):
        mock_bay = mock.MagicMock()
        mock_bay.discovery_url = 'token://some_token'
        mock_bay.id = 1
        mock_bay.uuid = 'some_uuid'

        swarm_def = tdef.AtomicSwarmTemplateDefinition()
        actual_url = swarm_def.get_discovery_url(mock_bay)

        self.assertEqual(mock_bay.discovery_url, actual_url)
