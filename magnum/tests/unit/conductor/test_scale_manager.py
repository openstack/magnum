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

import mock

from magnum.common import exception
from magnum.conductor import scale_manager
from magnum.tests import base


class TestScaleManager(base.TestCase):

    def _test_get_removal_nodes(
            self, mock_create_k8s_api, mock_get_num_of_removal,
            mock_is_scale_down, mock_get_by_uuid, is_scale_down,
            num_of_removal, all_hosts, pod_hosts, expected_removal_hosts):

        mock_is_scale_down.return_value = is_scale_down
        mock_get_num_of_removal.return_value = num_of_removal

        pods = list()
        for h in pod_hosts:
            pod = mock.MagicMock()
            pod.spec.node_name = h
            pods.append(pod)

        mock_k8s_api = mock.MagicMock()
        mock_k8s_api.list_namespaced_pod.return_value.items = pods
        mock_create_k8s_api.return_value = mock_k8s_api

        mock_heat_output = mock.MagicMock()
        mock_heat_output.get_output_value.return_value = all_hosts

        mock_stack = mock.MagicMock()
        mock_heat_client = mock.MagicMock()
        mock_osc = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_stack
        mock_osc.heat.return_value = mock_heat_client

        mock_context = mock.MagicMock()
        mock_bay = mock.MagicMock()
        scale_mgr = scale_manager.ScaleManager(mock_context, mock_osc,
                                               mock_bay)

        if expected_removal_hosts is None:
            self.assertRaises(exception.MagnumException,
                              scale_mgr.get_removal_nodes, mock_heat_output)
        else:
            removal_hosts = scale_mgr.get_removal_nodes(mock_heat_output)
            self.assertEqual(expected_removal_hosts, removal_hosts)
            if num_of_removal > 0:
                mock_create_k8s_api.assert_called_once_with(mock_context,
                                                            mock_bay)

    @mock.patch('magnum.objects.Bay.get_by_uuid')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager._is_scale_down')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager.'
                '_get_num_of_removal')
    @mock.patch('magnum.conductor.k8s_api.create_k8s_api')
    def test_get_removal_nodes_no_pod(
            self, mock_create_k8s_api, mock_get_num_of_removal,
            mock_is_scale_down, mock_get_by_uuid):

        is_scale_down = True
        num_of_removal = 1
        hosts = ['10.0.0.3', '10.0.0.4']
        pods = []
        expected_removal_hosts = ['10.0.0.3']
        self._test_get_removal_nodes(
            mock_create_k8s_api, mock_get_num_of_removal, mock_is_scale_down,
            mock_get_by_uuid, is_scale_down, num_of_removal, hosts, pods,
            expected_removal_hosts)

    @mock.patch('magnum.objects.Bay.get_by_uuid')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager._is_scale_down')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager.'
                '_get_num_of_removal')
    @mock.patch('magnum.conductor.k8s_api.create_k8s_api')
    def test_get_removal_nodes_one_pod(
            self, mock_create_k8s_api, mock_get_num_of_removal,
            mock_is_scale_down, mock_get_by_uuid):

        is_scale_down = True
        num_of_removal = 1
        hosts = ['10.0.0.3', '10.0.0.4']
        pods = ['10.0.0.3']
        expected_removal_hosts = ['10.0.0.4']
        self._test_get_removal_nodes(
            mock_create_k8s_api, mock_get_num_of_removal, mock_is_scale_down,
            mock_get_by_uuid, is_scale_down, num_of_removal, hosts, pods,
            expected_removal_hosts)

    @mock.patch('magnum.objects.Bay.get_by_uuid')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager._is_scale_down')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager.'
                '_get_num_of_removal')
    @mock.patch('magnum.conductor.k8s_api.create_k8s_api')
    def test_get_removal_nodes_two_pods(
            self, mock_create_k8s_api, mock_get_num_of_removal,
            mock_is_scale_down, mock_get_by_uuid):

        is_scale_down = True
        num_of_removal = 1
        hosts = ['10.0.0.3', '10.0.0.4']
        pods = ['10.0.0.3', '10.0.0.4']
        expected_removal_hosts = []
        self._test_get_removal_nodes(
            mock_create_k8s_api, mock_get_num_of_removal, mock_is_scale_down,
            mock_get_by_uuid, is_scale_down, num_of_removal, hosts, pods,
            expected_removal_hosts)

    @mock.patch('magnum.objects.Bay.get_by_uuid')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager._is_scale_down')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager.'
                '_get_num_of_removal')
    @mock.patch('magnum.conductor.k8s_api.create_k8s_api')
    def test_get_removal_nodes_three_pods(
            self, mock_create_k8s_api, mock_get_num_of_removal,
            mock_is_scale_down, mock_get_by_uuid):

        is_scale_down = True
        num_of_removal = 1
        hosts = ['10.0.0.3', '10.0.0.4']
        pods = ['10.0.0.3', '10.0.0.4', '10.0.0.5']
        expected_removal_hosts = []
        self._test_get_removal_nodes(
            mock_create_k8s_api, mock_get_num_of_removal, mock_is_scale_down,
            mock_get_by_uuid, is_scale_down, num_of_removal, hosts, pods,
            expected_removal_hosts)

    @mock.patch('magnum.objects.Bay.get_by_uuid')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager._is_scale_down')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager.'
                '_get_num_of_removal')
    @mock.patch('magnum.conductor.k8s_api.create_k8s_api')
    def test_get_removal_nodes_scale_up(
            self, mock_create_k8s_api, mock_get_num_of_removal,
            mock_is_scale_down, mock_get_by_uuid):

        is_scale_down = False
        num_of_removal = -1
        hosts = ['10.0.0.3', '10.0.0.4']
        pods = []
        expected_removal_hosts = []
        self._test_get_removal_nodes(
            mock_create_k8s_api, mock_get_num_of_removal, mock_is_scale_down,
            mock_get_by_uuid, is_scale_down, num_of_removal, hosts, pods,
            expected_removal_hosts)

    @mock.patch('magnum.objects.Bay.get_by_uuid')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager._is_scale_down')
    @mock.patch('magnum.conductor.scale_manager.ScaleManager.'
                '_get_num_of_removal')
    @mock.patch('magnum.conductor.k8s_api.create_k8s_api')
    def test_get_removal_nodes_with_none_hosts(
            self, mock_create_k8s_api, mock_get_num_of_removal,
            mock_is_scale_down, mock_get_by_uuid):

        is_scale_down = True
        num_of_removal = 1
        hosts = None
        pods = []
        expected_removal_hosts = None
        self._test_get_removal_nodes(
            mock_create_k8s_api, mock_get_num_of_removal, mock_is_scale_down,
            mock_get_by_uuid, is_scale_down, num_of_removal, hosts, pods,
            expected_removal_hosts)
