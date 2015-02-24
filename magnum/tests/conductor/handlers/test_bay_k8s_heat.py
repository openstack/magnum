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


class TestBayK8sHeat(base.TestCase):
    def setUp(self):
        super(TestBayK8sHeat, self).setUp()
        self.baymodel_dict = {
            'image_id': 'image_id',
            'flavor_id': 'flavor_id',
            'keypair_id': 'keypair_id',
            'dns_nameserver': 'dns_nameserver',
            'external_network_id': 'external_network_id',
            'docker_volume_size': 20,
        }
        self.bay_dict = {
            'baymodel_id': 'xx-xx-xx-xx',
            'name': 'bay1',
            'stack_id': 'xx-xx-xx-xx',
            'master_address': '172.17.2.3',
            'minions_address': ['172.17.2.4'],
            'node_count': 1,
        }

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_bay_definition(self,
                                    mock_objects_baymodel_get_by_uuid):
        baymodel = objects.BayModel(self.context, **self.baymodel_dict)
        mock_objects_baymodel_get_by_uuid.return_value = baymodel
        bay = objects.Bay(self.context, **self.bay_dict)

        bay_definition = bay_k8s_heat._extract_bay_definition(self.context,
                                                              bay)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network_id': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'server_flavor': 'flavor_id',
            'number_of_minions': '1',
            'docker_volume_size': 20,
        }
        self.assertEqual(expected, bay_definition)

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_bay_definition_without_dns(self,
                                        mock_objects_baymodel_get_by_uuid):
        baymodel_dict = self.baymodel_dict
        baymodel_dict['dns_nameserver'] = None
        baymodel = objects.BayModel(self.context, **baymodel_dict)
        mock_objects_baymodel_get_by_uuid.return_value = baymodel
        bay = objects.Bay(self.context, **self.bay_dict)

        bay_definition = bay_k8s_heat._extract_bay_definition(self.context,
                                                              bay)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network_id': 'external_network_id',
            'server_image': 'image_id',
            'server_flavor': 'flavor_id',
            'number_of_minions': '1',
            'docker_volume_size': 20,
        }
        self.assertEqual(expected, bay_definition)

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_bay_definition_without_server_image(self,
                                        mock_objects_baymodel_get_by_uuid):
        baymodel_dict = self.baymodel_dict
        baymodel_dict['image_id'] = None
        baymodel = objects.BayModel(self.context, **baymodel_dict)
        mock_objects_baymodel_get_by_uuid.return_value = baymodel
        bay = objects.Bay(self.context, **self.bay_dict)

        bay_definition = bay_k8s_heat._extract_bay_definition(self.context,
                                                              bay)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network_id': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_flavor': 'flavor_id',
            'number_of_minions': '1',
            'docker_volume_size': 20,
        }
        self.assertEqual(expected, bay_definition)

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_bay_definition_without_server_flavor(self,
                                        mock_objects_baymodel_get_by_uuid):
        baymodel_dict = self.baymodel_dict
        baymodel_dict['flavor_id'] = None
        baymodel = objects.BayModel(self.context, **baymodel_dict)
        mock_objects_baymodel_get_by_uuid.return_value = baymodel
        bay = objects.Bay(self.context, **self.bay_dict)

        bay_definition = bay_k8s_heat._extract_bay_definition(self.context,
                                                              bay)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network_id': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'number_of_minions': '1',
            'docker_volume_size': 20,
        }
        self.assertEqual(expected, bay_definition)

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_bay_definition_without_docker_volume_size(self,
                                        mock_objects_baymodel_get_by_uuid):
        baymodel_dict = self.baymodel_dict
        baymodel_dict['docker_volume_size'] = None
        baymodel = objects.BayModel(self.context, **baymodel_dict)
        mock_objects_baymodel_get_by_uuid.return_value = baymodel
        bay = objects.Bay(self.context, **self.bay_dict)

        bay_definition = bay_k8s_heat._extract_bay_definition(self.context,
                                                              bay)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network_id': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'server_flavor': 'flavor_id',
            'number_of_minions': '1',
        }
        self.assertEqual(expected, bay_definition)

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_bay_definition_without_apiserver_port(self,
                                        mock_objects_baymodel_get_by_uuid):
        baymodel_dict = self.baymodel_dict
        baymodel_dict['apiserver_port'] = None
        baymodel = objects.BayModel(self.context, **baymodel_dict)
        mock_objects_baymodel_get_by_uuid.return_value = baymodel
        bay = objects.Bay(self.context, **self.bay_dict)

        bay_definition = bay_k8s_heat._extract_bay_definition(self.context,
                                                              bay)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network_id': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'server_flavor': 'flavor_id',
            'number_of_minions': '1',
            'docker_volume_size': 20,
        }
        self.assertEqual(expected, bay_definition)

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_bay_definition_without_node_count(self,
                                        mock_objects_baymodel_get_by_uuid):
        bay_dict = self.bay_dict
        bay_dict['node_count'] = None
        baymodel = objects.BayModel(self.context, **self.baymodel_dict)
        mock_objects_baymodel_get_by_uuid.return_value = baymodel
        bay = objects.Bay(self.context, **bay_dict)

        bay_definition = bay_k8s_heat._extract_bay_definition(self.context,
                                                              bay)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network_id': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'server_flavor': 'flavor_id',
            'docker_volume_size': 20,
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
    @patch('magnum.conductor.handlers.bay_k8s_heat._extract_bay_definition')
    def test_create_stack(self,
                          mock_extract_bay_definition,
                          mock_get_template_contents,
                          mock_generate_id):

        mock_generate_id.return_value = 'xx-xx-xx-xx'
        expected_stack_name = 'expected_stack_name-xx-xx-xx-xx'
        expected_template_contents = 'template_contents'
        exptected_files = []
        dummy_bay_name = 'expected_stack_name'

        mock_tpl_files = mock.MagicMock()
        mock_tpl_files.items.return_value = exptected_files
        mock_get_template_contents.return_value = [
            mock_tpl_files, expected_template_contents]
        mock_extract_bay_definition.return_value = {}
        mock_heat_client = mock.MagicMock()
        mock_osc = mock.MagicMock()
        mock_osc.heat.return_value = mock_heat_client
        mock_bay = mock.MagicMock()
        mock_bay.name = dummy_bay_name

        bay_k8s_heat._create_stack(self.context, mock_osc, mock_bay)

        expected_args = {
            'stack_name': expected_stack_name,
            'parameters': {},
            'template': expected_template_contents,
            'files': dict(exptected_files)
        }
        mock_heat_client.stacks.create.assert_called_once_with(**expected_args)

    @patch('heatclient.common.template_utils.get_template_contents')
    @patch('magnum.conductor.handlers.bay_k8s_heat._extract_bay_definition')
    def test_update_stack(self,
                          mock_extract_bay_definition,
                          mock_get_template_contents):

        mock_stack_id = 'xx-xx-xx-xx'
        expected_template_contents = 'template_contents'
        exptected_files = []

        mock_tpl_files = mock.MagicMock()
        mock_tpl_files.items.return_value = exptected_files
        mock_get_template_contents.return_value = [
            mock_tpl_files, expected_template_contents]
        mock_extract_bay_definition.return_value = {}
        mock_heat_client = mock.MagicMock()
        mock_osc = mock.MagicMock()
        mock_osc.heat.return_value = mock_heat_client
        mock_bay = mock.MagicMock()
        mock_bay.stack_id = mock_stack_id

        bay_k8s_heat._update_stack({}, mock_osc, mock_bay)

        expected_args = {
            'parameters': {},
            'template': expected_template_contents,
            'files': dict(exptected_files)
        }
        mock_heat_client.stacks.update.assert_called_once_with(mock_stack_id,
                                                               **expected_args)
