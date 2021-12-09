# Copyright 2015 Huawei Technologies Co.,LTD.
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

import tempfile
from unittest import mock

from requests_mock.contrib import fixture

from magnum.common import exception
from magnum.conductor import scale_manager
from magnum.drivers.common.k8s_scale_manager import K8sScaleManager
from magnum.tests import base


class TestScaleManager(base.TestCase):

    def _test_get_removal_nodes(
            self, mock_get_hosts, mock_get_num_of_removal,
            mock_is_scale_down, mock_get_by_uuid, is_scale_down,
            num_of_removal, all_hosts, container_hosts,
            expected_removal_hosts):

        mock_is_scale_down.return_value = is_scale_down
        mock_get_num_of_removal.return_value = num_of_removal

        mock_get_hosts.return_value = container_hosts

        mock_heat_output = mock.MagicMock()
        mock_heat_output.get_output_value.return_value = all_hosts

        mock_stack = mock.MagicMock()
        mock_heat_client = mock.MagicMock()
        mock_osc = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_stack
        mock_osc.heat.return_value = mock_heat_client

        mock_context = mock.MagicMock()
        mock_cluster = mock.MagicMock()
        scale_mgr = scale_manager.ScaleManager(mock_context, mock_osc,
                                               mock_cluster)

        if expected_removal_hosts is None:
            self.assertRaises(exception.MagnumException,
                              scale_mgr.get_removal_nodes, mock_heat_output)
        else:
            removal_hosts = scale_mgr.get_removal_nodes(mock_heat_output)
            self.assertEqual(expected_removal_hosts, removal_hosts)
            if num_of_removal > 0:
                mock_get_hosts.assert_called_once_with(mock_context,
                                                       mock_cluster)

    @mock.patch('magnum.objects.Cluster.get_by_uuid')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager._is_scale_down')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager.'
                '_get_num_of_removal')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager.'
                '_get_hosts_with_container')
    def test_get_removal_nodes_no_container_host(
            self, mock_get_hosts, mock_get_num_of_removal,
            mock_is_scale_down, mock_get_by_uuid):

        is_scale_down = True
        num_of_removal = 1
        all_hosts = ['10.0.0.3']
        container_hosts = set()
        expected_removal_hosts = ['10.0.0.3']
        self._test_get_removal_nodes(
            mock_get_hosts, mock_get_num_of_removal, mock_is_scale_down,
            mock_get_by_uuid, is_scale_down, num_of_removal, all_hosts,
            container_hosts, expected_removal_hosts)

    @mock.patch('magnum.objects.Cluster.get_by_uuid')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager._is_scale_down')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager.'
                '_get_num_of_removal')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager.'
                '_get_hosts_with_container')
    def test_get_removal_nodes_one_container_host(
            self, mock_get_hosts, mock_get_num_of_removal,
            mock_is_scale_down, mock_get_by_uuid):

        is_scale_down = True
        num_of_removal = 1
        all_hosts = ['10.0.0.3', '10.0.0.4']
        container_hosts = set(['10.0.0.3'])
        expected_removal_hosts = ['10.0.0.4']
        self._test_get_removal_nodes(
            mock_get_hosts, mock_get_num_of_removal, mock_is_scale_down,
            mock_get_by_uuid, is_scale_down, num_of_removal, all_hosts,
            container_hosts, expected_removal_hosts)

    @mock.patch('magnum.objects.Cluster.get_by_uuid')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager._is_scale_down')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager.'
                '_get_num_of_removal')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager.'
                '_get_hosts_with_container')
    def test_get_removal_nodes_two_container_hosts(
            self, mock_get_hosts, mock_get_num_of_removal,
            mock_is_scale_down, mock_get_by_uuid):

        is_scale_down = True
        num_of_removal = 1
        all_hosts = ['10.0.0.3', '10.0.0.4']
        container_hosts = set(['10.0.0.3', '10.0.0.4'])
        expected_removal_hosts = []
        self._test_get_removal_nodes(
            mock_get_hosts, mock_get_num_of_removal, mock_is_scale_down,
            mock_get_by_uuid, is_scale_down, num_of_removal, all_hosts,
            container_hosts, expected_removal_hosts)

    @mock.patch('magnum.objects.Cluster.get_by_uuid')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager._is_scale_down')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager.'
                '_get_num_of_removal')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager.'
                '_get_hosts_with_container')
    def test_get_removal_nodes_three_container_hosts(
            self, mock_get_hosts, mock_get_num_of_removal,
            mock_is_scale_down, mock_get_by_uuid):

        is_scale_down = True
        num_of_removal = 1
        all_hosts = ['10.0.0.3', '10.0.0.4']
        container_hosts = set(['10.0.0.3', '10.0.0.4', '10.0.0.5'])
        expected_removal_hosts = []
        self._test_get_removal_nodes(
            mock_get_hosts, mock_get_num_of_removal, mock_is_scale_down,
            mock_get_by_uuid, is_scale_down, num_of_removal, all_hosts,
            container_hosts, expected_removal_hosts)

    @mock.patch('magnum.objects.Cluster.get_by_uuid')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager._is_scale_down')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager.'
                '_get_num_of_removal')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager.'
                '_get_hosts_with_container')
    def test_get_removal_nodes_scale_up(
            self, mock_get_hosts, mock_get_num_of_removal,
            mock_is_scale_down, mock_get_by_uuid):

        is_scale_down = False
        num_of_removal = -1
        all_hosts = ['10.0.0.3', '10.0.0.4']
        container_hosts = set()
        expected_removal_hosts = []
        self._test_get_removal_nodes(
            mock_get_hosts, mock_get_num_of_removal, mock_is_scale_down,
            mock_get_by_uuid, is_scale_down, num_of_removal, all_hosts,
            container_hosts, expected_removal_hosts)

    @mock.patch('magnum.objects.Cluster.get_by_uuid')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager._is_scale_down')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager.'
                '_get_num_of_removal')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager.'
                '_get_hosts_with_container')
    def test_get_removal_nodes_with_none_hosts(
            self, mock_get_hosts, mock_get_num_of_removal,
            mock_is_scale_down, mock_get_by_uuid):

        is_scale_down = True
        num_of_removal = 1
        all_hosts = None
        container_hosts = set()
        expected_removal_hosts = None
        self._test_get_removal_nodes(
            mock_get_hosts, mock_get_num_of_removal, mock_is_scale_down,
            mock_get_by_uuid, is_scale_down, num_of_removal, all_hosts,
            container_hosts, expected_removal_hosts)


class TestK8sScaleManager(base.TestCase):

    def setUp(self):
        super(TestK8sScaleManager, self).setUp()
        self.requests_mock = self.useFixture(fixture.Fixture())

    @mock.patch('magnum.objects.Cluster.get_by_uuid')
    @mock.patch('magnum.conductor.k8s_api.create_client_files')
    def test_get_hosts_with_container(
            self, mock_create_client_files, mock_get):
        mock_cluster = mock.MagicMock()
        mock_cluster.api_address = "https://foobar.com:6443"

        mock_create_client_files.return_value = (
            tempfile.NamedTemporaryFile(),
            tempfile.NamedTemporaryFile(),
            tempfile.NamedTemporaryFile()
        )

        self.requests_mock.register_uri(
            'GET',
            f"{mock_cluster.api_address}/api/v1/namespaces/default/pods",
            json={
                'items': [
                    {
                        'spec': {
                            'node_name': 'node1',
                        }
                    },
                    {
                        'spec': {
                            'node_name': 'node2',
                        }
                    }
                ]
            },
        )

        mgr = K8sScaleManager(
            mock.MagicMock(), mock.MagicMock(), mock.MagicMock())
        hosts = mgr._get_hosts_with_container(
            mock.MagicMock(), mock_cluster)
        self.assertEqual(hosts, {'node1', 'node2'})
