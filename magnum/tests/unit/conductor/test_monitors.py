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

from collections import namedtuple

import mock
from oslo_serialization import jsonutils

from magnum.common import exception
from magnum.drivers.common import k8s_monitor
from magnum.drivers.mesos_ubuntu_v1 import monitor as mesos_monitor
from magnum.drivers.swarm_fedora_atomic_v1 import monitor as swarm_monitor
from magnum.drivers.swarm_fedora_atomic_v2 import monitor as swarm_v2_monitor
from magnum import objects
from magnum.objects import fields as m_fields
from magnum.tests import base
from magnum.tests.unit.db import utils

NODE_STATUS_CONDITION = namedtuple('Condition',
                                   ['type', 'status'])


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

        cluster = utils.get_test_cluster(node_addresses=['1.2.3.4'],
                                         api_address='https://5.6.7.8:2376',
                                         master_addresses=['10.0.0.6'])
        self.cluster = objects.Cluster(self.context, **cluster)
        self.monitor = swarm_monitor.SwarmMonitor(self.context, self.cluster)
        self.v2_monitor = swarm_v2_monitor.SwarmMonitor(self.context,
                                                        self.cluster)
        self.k8s_monitor = k8s_monitor.K8sMonitor(self.context, self.cluster)
        self.mesos_monitor = mesos_monitor.MesosMonitor(self.context,
                                                        self.cluster)
        p = mock.patch('magnum.drivers.swarm_fedora_atomic_v1.monitor.'
                       'SwarmMonitor.metrics_spec',
                       new_callable=mock.PropertyMock)
        self.mock_metrics_spec = p.start()
        self.mock_metrics_spec.return_value = self.test_metrics_spec
        self.addCleanup(p.stop)

        p2 = mock.patch('magnum.drivers.swarm_fedora_atomic_v2.monitor.'
                        'SwarmMonitor.metrics_spec',
                        new_callable=mock.PropertyMock)
        self.mock_metrics_spec_v2 = p2.start()
        self.mock_metrics_spec_v2.return_value = self.test_metrics_spec
        self.addCleanup(p2.stop)

    @mock.patch('magnum.common.docker_utils.docker_for_cluster')
    def test_swarm_monitor_pull_data_success(self, mock_docker_cluster):
        mock_docker = mock.MagicMock()
        mock_docker.info.return_value = {'DriverStatus': [[
            u' \u2514 Reserved Memory', u'0 B / 1 GiB']]}
        mock_docker.containers.return_value = [mock.MagicMock()]
        mock_docker.inspect_container.return_value = 'test_container'
        mock_docker_cluster.return_value.__enter__.return_value = mock_docker

        self.monitor.pull_data()

        self.assertEqual([{'MemTotal': 1073741824.0}],
                         self.monitor.data['nodes'])
        self.assertEqual(['test_container'], self.monitor.data['containers'])

    @mock.patch('magnum.common.docker_utils.docker_for_cluster')
    def test_swarm_v2_monitor_pull_data_success(self, mock_docker_cluster):
        mock_docker = mock.MagicMock()
        mock_docker.info.return_value = {'DriverStatus': [[
            u' \u2514 Reserved Memory', u'0 B / 1 GiB']]}
        mock_docker.containers.return_value = [mock.MagicMock()]
        mock_docker.inspect_container.return_value = 'test_container'
        mock_docker_cluster.return_value.__enter__.return_value = mock_docker

        self.v2_monitor.pull_data()

        self.assertEqual([{'MemTotal': 1073741824.0}],
                         self.v2_monitor.data['nodes'])
        self.assertEqual(['test_container'],
                         self.v2_monitor.data['containers'])

    @mock.patch('magnum.common.docker_utils.docker_for_cluster')
    def test_swarm_monitor_pull_data_raise(self, mock_docker_cluster):
        mock_container = mock.MagicMock()
        mock_docker = mock.MagicMock()
        mock_docker.info.return_value = {'DriverStatus': [[
            u' \u2514 Reserved Memory', u'0 B / 1 GiB']]}
        mock_docker.containers.return_value = [mock_container]
        mock_docker.inspect_container.side_effect = Exception("inspect error")
        mock_docker_cluster.return_value.__enter__.return_value = mock_docker

        self.monitor.pull_data()

        self.assertEqual([{'MemTotal': 1073741824.0}],
                         self.monitor.data['nodes'])
        self.assertEqual([mock_container], self.monitor.data['containers'])

    @mock.patch('magnum.common.docker_utils.docker_for_cluster')
    def test_swarm_v2_monitor_pull_data_raise(self, mock_docker_cluster):
        mock_container = mock.MagicMock()
        mock_docker = mock.MagicMock()
        mock_docker.info.return_value = {'DriverStatus': [[
            u' \u2514 Reserved Memory', u'0 B / 1 GiB']]}
        mock_docker.containers.return_value = [mock_container]
        mock_docker.inspect_container.side_effect = Exception("inspect error")
        mock_docker_cluster.return_value.__enter__.return_value = mock_docker

        self.v2_monitor.pull_data()

        self.assertEqual([{'MemTotal': 1073741824.0}],
                         self.v2_monitor.data['nodes'])
        self.assertEqual([mock_container], self.v2_monitor.data['containers'])

    def test_swarm_monitor_get_metric_names(self):
        names = self.monitor.get_metric_names()
        self.assertEqual(sorted(['metric1', 'metric2']), sorted(names))

    def test_swarm_v2_monitor_get_metric_names(self):
        names = self.v2_monitor.get_metric_names()
        self.assertEqual(sorted(['metric1', 'metric2']), sorted(names))

    def test_swarm_monitor_get_metric_unit(self):
        unit = self.monitor.get_metric_unit('metric1')
        self.assertEqual('metric1_unit', unit)

    def test_swarm_v2_monitor_get_metric_unit(self):
        unit = self.v2_monitor.get_metric_unit('metric1')
        self.assertEqual('metric1_unit', unit)

    def test_swarm_monitor_compute_metric_value(self):
        mock_func = mock.MagicMock()
        mock_func.return_value = 'metric1_value'
        self.monitor.metric1_func = mock_func
        value = self.monitor.compute_metric_value('metric1')
        self.assertEqual('metric1_value', value)

    def test_swarm_v2_monitor_compute_metric_value(self):
        mock_func = mock.MagicMock()
        mock_func.return_value = 'metric1_value'
        self.v2_monitor.metric1_func = mock_func
        value = self.v2_monitor.compute_metric_value('metric1')
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

    def test_swarm_v2_monitor_compute_memory_util(self):
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
        self.v2_monitor.data = test_data
        mem_util = self.v2_monitor.compute_memory_util()
        self.assertEqual(50, mem_util)

        test_data = {
            'nodes': [],
            'containers': [],
        }
        self.v2_monitor.data = test_data
        mem_util = self.v2_monitor.compute_memory_util()
        self.assertEqual(0, mem_util)

    @mock.patch('magnum.conductor.k8s_api.create_k8s_api')
    def test_k8s_monitor_pull_data_success(self, mock_k8s_api):
        mock_nodes = mock.MagicMock()
        mock_node = mock.MagicMock()
        mock_node.status = mock.MagicMock()
        mock_node.status.capacity = {'memory': '2000Ki', 'cpu': '1'}
        mock_nodes.items = [mock_node]
        mock_k8s_api.return_value.list_node.return_value = (
            mock_nodes)
        mock_pods = mock.MagicMock()
        mock_pod = mock.MagicMock()
        mock_pod.spec = mock.MagicMock()
        mock_container = mock.MagicMock()
        mock_container.resources = mock.MagicMock()
        mock_container.resources.limits = "{'memory': '100Mi', 'cpu': '500m'}"
        mock_pod.spec.containers = [mock_container]
        mock_pods.items = [mock_pod]
        mock_k8s_api.return_value.list_namespaced_pod.return_value = mock_pods

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

    def _test_mesos_monitor_pull_data(
            self, mock_url_get, state_json, expected_mem_total,
            expected_mem_used, expected_cpu_total, expected_cpu_used):
        state_json = jsonutils.dumps(state_json)
        mock_url_get.return_value = state_json
        self.mesos_monitor.pull_data()
        self.assertEqual(self.mesos_monitor.data['mem_total'],
                         expected_mem_total)
        self.assertEqual(self.mesos_monitor.data['mem_used'],
                         expected_mem_used)
        self.assertEqual(self.mesos_monitor.data['cpu_total'],
                         expected_cpu_total)
        self.assertEqual(self.mesos_monitor.data['cpu_used'],
                         expected_cpu_used)

    @mock.patch('magnum.common.urlfetch.get')
    def test_mesos_monitor_pull_data_success(self, mock_url_get):
        state_json = {
            'leader': 'master@10.0.0.6:5050',
            'pid': 'master@10.0.0.6:5050',
            'slaves': [{
                'resources': {
                    'mem': 100,
                    'cpus': 1,
                },
                'used_resources': {
                    'mem': 50,
                    'cpus': 0.2,
                }
            }]
        }
        self._test_mesos_monitor_pull_data(mock_url_get, state_json,
                                           100, 50, 1, 0.2)

    @mock.patch('magnum.common.urlfetch.get')
    def test_mesos_monitor_pull_data_success_not_leader(self, mock_url_get):
        state_json = {
            'leader': 'master@10.0.0.6:5050',
            'pid': 'master@1.1.1.1:5050',
            'slaves': []
        }
        self._test_mesos_monitor_pull_data(mock_url_get, state_json,
                                           0, 0, 0, 0)

    @mock.patch('magnum.common.urlfetch.get')
    def test_mesos_monitor_pull_data_success_no_master(self, mock_url_get):
        self.cluster.master_addresses = []
        self._test_mesos_monitor_pull_data(mock_url_get, {}, 0, 0, 0, 0)

    def test_mesos_monitor_get_metric_names(self):
        mesos_metric_spec = ('magnum.drivers.mesos_ubuntu_v1.monitor.'
                             'MesosMonitor.metrics_spec')
        with mock.patch(mesos_metric_spec,
                        new_callable=mock.PropertyMock) as mock_mesos_metric:
            mock_mesos_metric.return_value = self.test_metrics_spec
            names = self.mesos_monitor.get_metric_names()
            self.assertEqual(sorted(['metric1', 'metric2']), sorted(names))

    def test_mesos_monitor_get_metric_unit(self):
        mesos_metric_spec = ('magnum.drivers.mesos_ubuntu_v1.monitor.'
                             'MesosMonitor.metrics_spec')
        with mock.patch(mesos_metric_spec,
                        new_callable=mock.PropertyMock) as mock_mesos_metric:
            mock_mesos_metric.return_value = self.test_metrics_spec
            unit = self.mesos_monitor.get_metric_unit('metric1')
            self.assertEqual('metric1_unit', unit)

    def test_mesos_monitor_compute_memory_util(self):
        test_data = {
            'mem_total': 100,
            'mem_used': 50
        }
        self.mesos_monitor.data = test_data
        mem_util = self.mesos_monitor.compute_memory_util()
        self.assertEqual(50, mem_util)

        test_data = {
            'mem_total': 0,
            'pods': 0,
        }
        self.mesos_monitor.data = test_data
        mem_util = self.mesos_monitor.compute_memory_util()
        self.assertEqual(0, mem_util)

        test_data = {
            'mem_total': 100,
            'mem_used': 0,
            'pods': 0,
        }
        self.mesos_monitor.data = test_data
        mem_util = self.mesos_monitor.compute_memory_util()
        self.assertEqual(0, mem_util)

    def test_mesos_monitor_compute_cpu_util(self):
        test_data = {
            'cpu_total': 1,
            'cpu_used': 0.2,
        }
        self.mesos_monitor.data = test_data
        cpu_util = self.mesos_monitor.compute_cpu_util()
        self.assertEqual(20, cpu_util)

        test_data = {
            'cpu_total': 100,
            'cpu_used': 0,
        }
        self.mesos_monitor.data = test_data
        cpu_util = self.mesos_monitor.compute_cpu_util()
        self.assertEqual(0, cpu_util)

    @mock.patch('magnum.conductor.k8s_api.create_k8s_api')
    def test_k8s_monitor_health_healthy(self, mock_k8s_api):
        mock_nodes = mock.MagicMock()
        mock_node = mock.MagicMock()
        mock_api_client = mock.MagicMock()
        mock_node.status = mock.MagicMock()
        mock_node.metadata.name = 'k8s-cluster-node-0'
        mock_node.status.conditions = [NODE_STATUS_CONDITION(type='Ready',
                                                             status='True')]
        mock_nodes.items = [mock_node]
        mock_k8s_api.return_value.list_node.return_value = (
            mock_nodes)
        mock_k8s_api.return_value.api_client = mock_api_client
        mock_api_client.call_api.return_value = ('ok', None, None)

        self.k8s_monitor.poll_health_status()
        self.assertEqual(self.k8s_monitor.data['health_status'],
                         m_fields.ClusterHealthStatus.HEALTHY)
        self.assertEqual(self.k8s_monitor.data['health_status_reason'],
                         {'api': 'ok', 'k8s-cluster-node-0.Ready': True})

    @mock.patch('magnum.conductor.k8s_api.create_k8s_api')
    def test_k8s_monitor_health_unhealthy_api(self, mock_k8s_api):
        mock_nodes = mock.MagicMock()
        mock_node = mock.MagicMock()
        mock_api_client = mock.MagicMock()
        mock_node.status = mock.MagicMock()
        mock_node.metadata.name = 'k8s-cluster-node-0'
        mock_node.status.conditions = [NODE_STATUS_CONDITION(type='Ready',
                                                             status='True')]
        mock_nodes.items = [mock_node]
        mock_k8s_api.return_value.list_node.return_value = (
            mock_nodes)
        mock_k8s_api.return_value.api_client = mock_api_client
        mock_api_client.call_api.side_effect = exception.MagnumException(
            message='failed')

        self.k8s_monitor.poll_health_status()
        self.assertEqual(self.k8s_monitor.data['health_status'],
                         m_fields.ClusterHealthStatus.UNHEALTHY)
        self.assertEqual(self.k8s_monitor.data['health_status_reason'],
                         {'api': 'failed'})

    @mock.patch('magnum.conductor.k8s_api.create_k8s_api')
    def test_k8s_monitor_health_unhealthy_node(self, mock_k8s_api):
        mock_nodes = mock.MagicMock()
        mock_api_client = mock.MagicMock()

        mock_node0 = mock.MagicMock()
        mock_node0.status = mock.MagicMock()
        mock_node0.metadata.name = 'k8s-cluster-node-0'
        mock_node0.status.conditions = [NODE_STATUS_CONDITION(type='Ready',
                                                              status='False')]
        mock_node1 = mock.MagicMock()
        mock_node1.status = mock.MagicMock()
        mock_node1.metadata.name = 'k8s-cluster-node-1'
        mock_node1.status.conditions = [NODE_STATUS_CONDITION(type='Ready',
                                                              status='True')]

        mock_nodes.items = [mock_node0, mock_node1]
        mock_k8s_api.return_value.list_node.return_value = (
            mock_nodes)
        mock_k8s_api.return_value.api_client = mock_api_client
        mock_api_client.call_api.return_value = ('ok', None, None)

        self.k8s_monitor.poll_health_status()
        self.assertEqual(self.k8s_monitor.data['health_status'],
                         m_fields.ClusterHealthStatus.UNHEALTHY)
        self.assertEqual(self.k8s_monitor.data['health_status_reason'],
                         {'api': 'ok', 'k8s-cluster-node-0.Ready': False,
                          'api': 'ok', 'k8s-cluster-node-1.Ready': True})
