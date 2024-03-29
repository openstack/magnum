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

import tempfile
from unittest import mock

from requests_mock.contrib import fixture

from magnum.common import exception
from magnum.drivers.common import k8s_monitor
from magnum import objects
from magnum.objects import fields as m_fields
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
        self.requests_mock = self.useFixture(fixture.Fixture())
        cluster = utils.get_test_cluster(node_addresses=['1.2.3.4'],
                                         api_address='https://5.6.7.8:2376',
                                         master_addresses=['10.0.0.6'],
                                         labels={})
        self.cluster = objects.Cluster(self.context, **cluster)
        cluster_template = (
            utils.get_test_cluster_template(master_lb_enabled=False))
        self.cluster.cluster_template = (
            objects.ClusterTemplate(self.context, **cluster_template))
        nodegroups = utils.get_nodegroups_for_cluster(
            node_addresses=['1.2.3.4'], master_addresses=['10.0.0.6'])
        self.nodegroups = [
            objects.NodeGroup(self.context, **nodegroups['master']),
            objects.NodeGroup(self.context, **nodegroups['worker'])
        ]
        self.k8s_monitor = k8s_monitor.K8sMonitor(self.context, self.cluster)

    @mock.patch('magnum.conductor.k8s_api.create_client_files')
    def test_k8s_monitor_pull_data_success(self, mock_create_client_files):
        mock_create_client_files.return_value = (
            tempfile.NamedTemporaryFile(),
            tempfile.NamedTemporaryFile(),
            tempfile.NamedTemporaryFile()
        )

        self.requests_mock.register_uri(
            'GET',
            f"{self.cluster.api_address}/api/v1/nodes",
            json={
                'items': [
                    {
                        'status': {
                            'capacity': {'memory': '2000Ki', 'cpu': '1'}
                        }
                    }
                ]
            },
        )

        self.requests_mock.register_uri(
            'GET',
            f"{self.cluster.api_address}/api/v1/namespaces/default/pods",
            json={
                'items': [
                    {
                        'spec': {
                            'containers': [
                                {
                                    'resources': {
                                        'limits': {
                                            'memory': '100Mi',
                                            'cpu': '500m'
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        )

        self.k8s_monitor.pull_data()
        self.assertEqual(self.k8s_monitor.data['nodes'],
                         [{'Memory': 2048000.0, 'Cpu': 1}])
        self.assertEqual(self.k8s_monitor.data['pods'],
                         [{'Memory': 104857600.0, 'Cpu': 0.5}])

    def test_k8s_monitor_get_metric_names(self):
        k8s_metric_spec = 'magnum.drivers.common.k8s_monitor.K8sMonitor.'\
                          'metrics_spec'
        with mock.patch(k8s_metric_spec,
                        new_callable=mock.PropertyMock) as mock_k8s_metric:
            mock_k8s_metric.return_value = self.test_metrics_spec
            names = self.k8s_monitor.get_metric_names()
            self.assertEqual(sorted(['metric1', 'metric2']), sorted(names))

    def test_k8s_monitor_get_metric_unit(self):
        k8s_metric_spec = 'magnum.drivers.common.k8s_monitor.K8sMonitor.'\
                          'metrics_spec'
        with mock.patch(k8s_metric_spec,
                        new_callable=mock.PropertyMock) as mock_k8s_metric:
            mock_k8s_metric.return_value = self.test_metrics_spec
            unit = self.k8s_monitor.get_metric_unit('metric1')
            self.assertEqual('metric1_unit', unit)

    def test_k8s_monitor_compute_memory_util(self):
        test_data = {
            'nodes': [
                {
                    'Memory': 20,
                },
            ],
            'pods': [
                {
                    'Memory': 10,
                },
            ],
        }
        self.k8s_monitor.data = test_data
        mem_util = self.k8s_monitor.compute_memory_util()
        self.assertEqual(50, mem_util)

        test_data = {
            'nodes': [],
            'pods': [],
        }
        self.k8s_monitor.data = test_data
        mem_util = self.k8s_monitor.compute_memory_util()
        self.assertEqual(0, mem_util)

    def test_k8s_monitor_compute_cpu_util(self):
        test_data = {
            'nodes': [
                {
                    'Cpu': 1,
                },
            ],
            'pods': [
                {
                    'Cpu': 0.5,
                },
            ],
        }
        self.k8s_monitor.data = test_data
        cpu_util = self.k8s_monitor.compute_cpu_util()
        self.assertEqual(50, cpu_util)

        test_data = {
            'nodes': [],
            'pods': [],
        }
        self.k8s_monitor.data = test_data
        cpu_util = self.k8s_monitor.compute_cpu_util()
        self.assertEqual(0, cpu_util)

    @mock.patch('magnum.conductor.k8s_api.create_client_files')
    def test_k8s_monitor_health_healthy(self, mock_create_client_files):
        mock_create_client_files.return_value = (
            tempfile.NamedTemporaryFile(),
            tempfile.NamedTemporaryFile(),
            tempfile.NamedTemporaryFile()
        )

        self.requests_mock.register_uri(
            'GET',
            f"{self.cluster.api_address}/api/v1/nodes",
            json={
                'items': [
                    {
                        'metadata': {
                            'name': 'k8s-cluster-node-0'
                        },
                        'status': {
                            'conditions': [
                                {
                                    'type': 'Ready',
                                    'status': 'True',
                                }
                            ]
                        }
                    }
                ]
            }
        )

        self.requests_mock.register_uri(
            'GET',
            f"{self.cluster.api_address}/healthz",
            text="ok",
        )

        self.k8s_monitor.poll_health_status()
        self.assertEqual(self.k8s_monitor.data['health_status'],
                         m_fields.ClusterHealthStatus.HEALTHY)
        self.assertEqual(self.k8s_monitor.data['health_status_reason'],
                         {'api': 'ok', 'k8s-cluster-node-0.Ready': True})

    @mock.patch('magnum.conductor.k8s_api.create_client_files')
    def test_k8s_monitor_health_unhealthy_api(self, mock_create_client_files):
        mock_create_client_files.return_value = (
            tempfile.NamedTemporaryFile(),
            tempfile.NamedTemporaryFile(),
            tempfile.NamedTemporaryFile()
        )

        self.requests_mock.register_uri(
            'GET',
            f"{self.cluster.api_address}/api/v1/nodes",
            json={
                'items': [
                    {
                        'metadata': {
                            'name': 'k8s-cluster-node-0'
                        },
                        'status': {
                            'conditions': [
                                {
                                    'type': 'Ready',
                                    'status': 'True',
                                }
                            ]
                        }
                    }
                ]
            }
        )

        self.requests_mock.register_uri(
            'GET',
            f"{self.cluster.api_address}/healthz",
            exc=exception.MagnumException(message='failed'),
        )

        self.k8s_monitor.poll_health_status()
        self.assertEqual(self.k8s_monitor.data['health_status'],
                         m_fields.ClusterHealthStatus.UNHEALTHY)
        self.assertEqual(self.k8s_monitor.data['health_status_reason'],
                         {'api': 'failed'})

    @mock.patch('magnum.conductor.k8s_api.create_client_files')
    def test_k8s_monitor_health_unhealthy_node(self, mock_create_client_files):
        mock_create_client_files.return_value = (
            tempfile.NamedTemporaryFile(),
            tempfile.NamedTemporaryFile(),
            tempfile.NamedTemporaryFile()
        )

        self.requests_mock.register_uri(
            'GET',
            f"{self.cluster.api_address}/api/v1/nodes",
            json={
                'items': [
                    {
                        'metadata': {
                            'name': 'k8s-cluster-node-0'
                        },
                        'status': {
                            'conditions': [
                                {
                                    'type': 'Ready',
                                    'status': 'False',
                                }
                            ]
                        }
                    },
                    {
                        'metadata': {
                            'name': 'k8s-cluster-node-1'
                        },
                        'status': {
                            'conditions': [
                                {
                                    'type': 'Ready',
                                    'status': 'True',
                                }
                            ]
                        }
                    }
                ]
            }
        )

        self.requests_mock.register_uri(
            'GET',
            f"{self.cluster.api_address}/healthz",
            text="ok",
        )

        self.k8s_monitor.poll_health_status()
        self.assertEqual(self.k8s_monitor.data['health_status'],
                         m_fields.ClusterHealthStatus.UNHEALTHY)
        self.assertEqual(self.k8s_monitor.data['health_status_reason'],
                         {'api': 'ok', 'k8s-cluster-node-0.Ready': False,
                          'k8s-cluster-node-1.Ready': True})

    @mock.patch('magnum.conductor.k8s_api.create_client_files')
    def test_k8s_monitor_health_unreachable_cluster(
            self, mock_create_client_files):
        mock_create_client_files.return_value = (
            tempfile.NamedTemporaryFile(),
            tempfile.NamedTemporaryFile(),
            tempfile.NamedTemporaryFile()
        )

        self.requests_mock.register_uri(
            'GET',
            f"{self.cluster.api_address}/api/v1/nodes",
            json={
                'items': [
                    {}
                ]
            }
        )

        self.k8s_monitor.cluster.floating_ip_enabled = False

        self.k8s_monitor.poll_health_status()
        self.assertEqual(self.k8s_monitor.data['health_status'],
                         m_fields.ClusterHealthStatus.UNKNOWN)

    @mock.patch('magnum.conductor.k8s_api.create_client_files')
    def test_k8s_monitor_health_unreachable_with_master_lb(
            self, mock_create_client_files):
        mock_create_client_files.return_value = (
            tempfile.NamedTemporaryFile(),
            tempfile.NamedTemporaryFile(),
            tempfile.NamedTemporaryFile()
        )

        self.requests_mock.register_uri(
            'GET',
            f"{self.cluster.api_address}/api/v1/nodes",
            json={
                'items': [
                    {}
                ]
            }
        )

        cluster = self.k8s_monitor.cluster
        cluster.floating_ip_enabled = True
        cluster.master_lb_enabled = True
        cluster.labels['master_lb_floating_ip_enabled'] = False

        self.k8s_monitor.poll_health_status()
        self.assertEqual(self.k8s_monitor.data['health_status'],
                         m_fields.ClusterHealthStatus.UNKNOWN)

    def test_is_magnum_auto_healer_running(self):
        cluster = self.k8s_monitor.cluster
        cluster.labels['auto_healing_enabled'] = True
        cluster.labels['auto_healing_controller'] = 'magnum-auto-healer'
        self.k8s_monitor._is_magnum_auto_healer_running()
        self.assertTrue(self.k8s_monitor._is_magnum_auto_healer_running())

        cluster.labels['auto_healing_enabled'] = False
        cluster.labels['auto_healing_controller'] = 'magnum-auto-healer'
        self.k8s_monitor._is_magnum_auto_healer_running()
        self.assertFalse(self.k8s_monitor._is_magnum_auto_healer_running())

        cluster.labels['auto_healing_enabled'] = True
        cluster.labels['auto_healing_controller'] = 'draino'
        self.k8s_monitor._is_magnum_auto_healer_running()
        self.assertFalse(self.k8s_monitor._is_magnum_auto_healer_running())

        cluster.labels = {}
        self.k8s_monitor._is_magnum_auto_healer_running()
        self.assertFalse(self.k8s_monitor._is_magnum_auto_healer_running())
