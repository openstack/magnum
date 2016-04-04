#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import ast

from magnum.common import utils
from magnum.conductor import k8s_api as k8s
from magnum.conductor.monitors import MonitorBase


class K8sMonitor(MonitorBase):

    def __init__(self, context, bay):
        super(K8sMonitor, self).__init__(context, bay)
        self.data = {}
        self.data['nodes'] = []
        self.data['pods'] = []

    @property
    def metrics_spec(self):
        return {
            'memory_util': {
                'unit': '%',
                'func': 'compute_memory_util',
            },
            'cpu_util': {
                'unit': '%',
                'func': 'compute_cpu_util',
            },
        }

    def pull_data(self):
        k8s_api = k8s.create_k8s_api(self.context, self.bay)
        nodes = k8s_api.list_namespaced_node()
        self.data['nodes'] = self._parse_node_info(nodes)
        pods = k8s_api.list_namespaced_pod('default')
        self.data['pods'] = self._parse_pod_info(pods)

    def _compute_res_util(self, res):
        res_total = 0
        for node in self.data['nodes']:
            res_total += node[res]
        res_reserved = 0

        for pod in self.data['pods']:
            res_reserved += pod[res]

        if res_total == 0:
            return 0
        else:
            return res_reserved * 100 / res_total

    def compute_memory_util(self):
        return self._compute_res_util('Memory')

    def compute_cpu_util(self):
        return self._compute_res_util('Cpu')

    def _parse_pod_info(self, pods):
        """Parse pods and retrieve memory and cpu details about each pod

        :param pods: The output of k8s_api.list_namespaced_pods()
        For example:
        {
            'items': [{
                'status': {
                    'container_statuses': None,
                    'pod_ip': None,
                    'phase': 'Pending',
                    'message': None,
                    'conditions': None,
                },
                'spec': {
                    'containers': [{
                        'image': 'nginx',
                        'resources': {'requests': None,
                              'limits': "{u'cpu': u'500m',
                                          u'memory': u'1280e3'}"},
                    }],
                },
                'api_version': None,
            }],
            'kind': 'PodList',
        }

        The above output is the dict form of:
        k8sclient.client.models.v1_pod_list.
        V1PodList object

        :return: Memory size of each pod. Example:
            [{'Memory': 1280000.0, cpu: 0.5},
             {'Memory': 1280000.0, cpu: 0.5}]
        """
        pods = pods.items
        parsed_containers = []
        for pod in pods:
            containers = pod.spec.containers
            for container in containers:
                memory = 0
                cpu = 0
                resources = container.resources
                limits = resources.limits
                if limits is not None:
                    # Output of resources.limits is string
                    # for example:
                    # limits = "{cpu': '500m': 'memory': '1000Ki'}"
                    limits = ast.literal_eval(limits)
                    if limits.get('memory', ''):
                        memory = utils.get_k8s_quantity(limits['memory'])
                    if limits.get('cpu', ''):
                        cpu = utils.get_k8s_quantity(limits['cpu'])
                container_dict = {
                    'Memory': memory,
                    'Cpu': cpu,
                }
                parsed_containers.append(container_dict)
        return parsed_containers

    def _parse_node_info(self, nodes):
        """Parse nodes to retrieve memory and cpu of each node

        :param nodes: The output of k8s_api.list_namespaced_node()
        For example:
        {
            'items': [{
                'status': {
                    'phase': None,
                    'capacity': "{u'cpu': u'1',
                                  u'memory': u'2049852Ki'}",
                },
            },
            'api_version': None,
            }],
            'kind': 'NodeList',
            'api_version': 'v1',
        }

        The above output is the dict form of:
        k8sclient.client.models.v1_node_list.
        V1NodeList object

        :return: CPU core number and Memory size of each node. Example:
            [{'cpu': 1, 'Memory': 1024.0},
             {'cpu': 1, 'Memory': 1024.0}]

        """
        nodes = nodes.items
        parsed_nodes = []
        for node in nodes:
            # Output of node.status.capacity is strong
            # for example:
            # capacity = "{'cpu': '1', 'memory': '1000Ki'}"
            capacity = ast.literal_eval(node.status.capacity)
            memory = utils.get_k8s_quantity(capacity['memory'])
            cpu = int(capacity['cpu'])
            parsed_nodes.append({'Memory': memory, 'Cpu': cpu})

        return parsed_nodes
