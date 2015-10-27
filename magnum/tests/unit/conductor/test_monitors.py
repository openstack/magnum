# Copyright 2015 Huawei Technologies Co.,LTD.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock

from magnum.conductor import monitors
from magnum import objects
from magnum.tests import base
from magnum.tests.unit.db import utils


class MonitorsTestCase(base.TestCase):

    test_metrics_spec = {
        'metric1': {
            'unit': 'metric1_unit',
            'func': 'metric1_func',
        },
        'metric2': {
            'unit': 'metric2_unit',
            'func': 'metric2_func',
        },
    }

    def setUp(self):
        super(MonitorsTestCase, self).setUp()

        bay = utils.get_test_bay(node_addresses=['1.2.3.4'],
                                 api_address='5.6.7.8')
        self.bay = objects.Bay(self.context, **bay)
        self.monitor = monitors.SwarmMonitor(self.context, self.bay)
        p = mock.patch('magnum.conductor.monitors.SwarmMonitor.metrics_spec',
                       new_callable=mock.PropertyMock)
        self.mock_metrics_spec = p.start()
        self.mock_metrics_spec.return_value = self.test_metrics_spec
        self.addCleanup(p.stop)

    @mock.patch('magnum.objects.BayModel.get_by_uuid')
    def test_create_monitor_success(self, mock_baymodel_get_by_uuid):
        baymodel = mock.MagicMock()
        baymodel.coe = 'swarm'
        mock_baymodel_get_by_uuid.return_value = baymodel
        monitor = monitors.create_monitor(self.context, self.bay)
        self.assertIsInstance(monitor, monitors.SwarmMonitor)

    @mock.patch('magnum.objects.BayModel.get_by_uuid')
    def test_create_monitor_unsupported_coe(self, mock_baymodel_get_by_uuid):
        baymodel = mock.MagicMock()
        baymodel.coe = 'unsupported'
        mock_baymodel_get_by_uuid.return_value = baymodel
        monitor = monitors.create_monitor(self.context, self.bay)
        self.assertIsNone(monitor)

    @mock.patch('magnum.common.docker_utils.docker_for_bay')
    def test_swarm_monitor_pull_data_success(self, mock_docker_for_bay):
        mock_docker = mock.MagicMock()
        mock_docker.info.return_value = {'DriverStatus': [[
            u' \u2514 Reserved Memory', u'0 B / 1 GiB']]}
        mock_docker.containers.return_value = [mock.MagicMock()]
        mock_docker.inspect_container.return_value = 'test_container'
        mock_docker_for_bay.return_value.__enter__.return_value = mock_docker

        self.monitor.pull_data()

        self.assertEqual([{'MemTotal': 1073741824.0}],
                         self.monitor.data['nodes'])
        self.assertEqual(['test_container'], self.monitor.data['containers'])

    @mock.patch('magnum.common.docker_utils.docker_for_bay')
    def test_swarm_monitor_pull_data_raise(self, mock_docker_for_bay):
        mock_container = mock.MagicMock()
        mock_docker = mock.MagicMock()
        mock_docker.info.return_value = {'DriverStatus': [[
            u' \u2514 Reserved Memory', u'0 B / 1 GiB']]}
        mock_docker.containers.return_value = [mock_container]
        mock_docker.inspect_container.side_effect = Exception("inspect error")
        mock_docker_for_bay.return_value.__enter__.return_value = mock_docker

        self.monitor.pull_data()

        self.assertEqual([{'MemTotal': 1073741824.0}],
                         self.monitor.data['nodes'])
        self.assertEqual([mock_container], self.monitor.data['containers'])

    def test_swarm_monitor_get_metric_names(self):
        names = self.monitor.get_metric_names()
        self.assertEqual(sorted(['metric1', 'metric2']), sorted(names))

    def test_swarm_monitor_get_metric_unit(self):
        unit = self.monitor.get_metric_unit('metric1')
        self.assertEqual('metric1_unit', unit)

    def test_swarm_monitor_compute_metric_value(self):
        mock_func = mock.MagicMock()
        mock_func.return_value = 'metric1_value'
        self.monitor.metric1_func = mock_func
        value = self.monitor.compute_metric_value('metric1')
        self.assertEqual('metric1_value', value)

    def test_swarm_monitor_compute_memory_util(self):
        test_data = {
            'nodes': [
                {
                    'Name': 'node',
                    'MemTotal': 20,
                },
            ],
            'containers': [
                {
                    'Name': 'container',
                    'HostConfig': {
                        'Memory': 10,
                    },
                },
            ],
        }
        self.monitor.data = test_data
        mem_util = self.monitor.compute_memory_util()
        self.assertEqual(50, mem_util)

        test_data = {
            'nodes': [],
            'containers': [],
        }
        self.monitor.data = test_data
        mem_util = self.monitor.compute_memory_util()
        self.assertEqual(0, mem_util)
