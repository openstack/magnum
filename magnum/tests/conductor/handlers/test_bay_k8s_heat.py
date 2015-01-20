# Copyright 2014 NEC Corporation.  All rights reserved.
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

from magnum.conductor.handlers import bay_k8s_heat
from magnum import objects
from magnum.tests import base

import mock
from mock import patch


class TestBayK8sHeat(base.BaseTestCase):
    def setUp(self):
        super(TestBayK8sHeat, self).setUp()
        self.baymodel_dict = {
            'image_id': 'image_id',
            'flavor_id': 'flavor_id',
            'keypair_id': 'keypair_id',
            'dns_nameserver': 'dns_nameserver',
            'external_network_id': 'external_network_id',
        }

    def test_extract_bay_definition(self):
        baymodel = objects.BayModel({}, **self.baymodel_dict)
        bay_definition = bay_k8s_heat._extract_bay_definition(
            baymodel)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network_id': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'server_flavor': 'flavor_id',
        }
        self.assertEqual(expected, bay_definition)

    def test_extract_bay_definition_without_dns(self):
        baymodel_dict = self.baymodel_dict
        baymodel_dict['dns_nameserver'] = None
        baymodel = objects.BayModel({}, **baymodel_dict)
        bay_definition = bay_k8s_heat._extract_bay_definition(
            baymodel)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network_id': 'external_network_id',
            'server_image': 'image_id',
            'server_flavor': 'flavor_id',
        }
        self.assertEqual(expected, bay_definition)

    def test_extract_bay_definition_without_server_image(self):
        baymodel_dict = self.baymodel_dict
        baymodel_dict['image_id'] = None
        baymodel = objects.BayModel({}, **baymodel_dict)
        bay_definition = bay_k8s_heat._extract_bay_definition(
            baymodel)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network_id': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_flavor': 'flavor_id',
        }
        self.assertEqual(expected, bay_definition)

    def test_extract_bay_definition_without_server_flavor(self):
        baymodel_dict = self.baymodel_dict
        baymodel_dict['flavor_id'] = None
        baymodel = objects.BayModel({}, **baymodel_dict)
        bay_definition = bay_k8s_heat._extract_bay_definition(
            baymodel)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network_id': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
        }
        self.assertEqual(expected, bay_definition)

    def test_extract_bay_definition_without_apiserver_port(self):
        baymodel_dict = self.baymodel_dict
        baymodel_dict['apiserver_port'] = None
        baymodel = objects.BayModel({}, **baymodel_dict)
        bay_definition = bay_k8s_heat._extract_bay_definition(
            baymodel)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network_id': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'server_flavor': 'flavor_id',
        }
        self.assertEqual(expected, bay_definition)

    def test_parse_stack_outputs(self):
        expected_master_address = 'master_address'
        expected_minion_address = ['minion', 'address']
        expected_minion_external_address = ['ex_minion', 'address']
        expected_return_value = {
            'kube_master': expected_master_address,
            'kube_minions': expected_minion_address,
            'kube_minions_external': expected_minion_external_address
        }

        outputs = [
          {
             "output_value": expected_minion_external_address,
             "description": "No description given",
             "output_key": "kube_minions_external"
           },
           {
             "output_value": expected_minion_address,
             "description": "No description given",
             "output_key": "kube_minions"
           },
           {
             "output_value": expected_master_address,
             "description": "No description given",
             "output_key": "kube_master"
           }
        ]

        parsed_outputs = bay_k8s_heat._parse_stack_outputs(outputs)
        self.assertEqual(expected_return_value, parsed_outputs)

    @patch('magnum.common.short_id.generate_id')
    @patch('heatclient.common.template_utils.get_template_contents')
    @patch('magnum.objects.BayModel.get_by_uuid')
    @patch('magnum.conductor.handlers.bay_k8s_heat._extract_bay_definition')
    def test_create_stack(self,
                          mock_extract_bay_definition,
                          mock_objects_baymodel_get_by_uuid,
                          mock_get_template_contents,
                          mock_generate_id):

        mock_generate_id.return_value = 'xx-xx-xx-xx'
        expected_stack_name = 'expected_stack_name-xx-xx-xx-xx'
        expected_number_of_minions = 1
        expected_template_contents = 'template_contents'
        exptected_files = []
        dummy_bay_name = 'expected_stack_name'

        mock_tpl_files = mock.MagicMock()
        mock_tpl_files.items.return_value = exptected_files
        mock_get_template_contents.return_value = [
            mock_tpl_files, expected_template_contents]
        mock_objects_baymodel_get_by_uuid.return_value = {}
        mock_extract_bay_definition.return_value = {}
        mock_heat_client = mock.MagicMock()
        mock_osc = mock.MagicMock()
        mock_osc.heat.return_value = mock_heat_client
        mock_bay = mock.MagicMock()
        mock_bay.name = dummy_bay_name
        mock_bay.node_count = expected_number_of_minions

        bay_k8s_heat._create_stack({}, mock_osc, mock_bay)

        expected_args = {
            'stack_name': expected_stack_name,
            'parameters': {
                'number_of_minions': str(expected_number_of_minions)},
            'template': expected_template_contents,
            'files': dict(exptected_files)
        }
        mock_heat_client.stacks.create.assert_called_once_with(**expected_args)
