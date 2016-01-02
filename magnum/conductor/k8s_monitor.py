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
        }

    def pull_data(self):
        k8s_api = k8s.create_k8s_api(self.context, self.bay.uuid)
        nodes = k8s_api.list_namespaced_node()
        self.data['nodes'] = self._parse_node_info(nodes)
        pods = k8s_api.list_namespaced_pod('default')
        self.data['pods'] = self._parse_pod_info(pods)

    def compute_memory_util(self):
        mem_total = 0
        for node in self.data['nodes']:
            mem_total += node['Memory']
        mem_reserved = 0

        for pod in self.data['pods']:
            mem_reserved += pod['Memory']

        if mem_total == 0:
            return 0
        else:
            return mem_reserved * 100 / mem_total

    def _parse_pod_info(self, pods):
        """Parse pods and retrieve memory details about each pod

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
                              'limits': "{u'memory': u'1280e3'}"},
                    }],
                },
                'api_version': None,
            }],
            'kind': 'PodList',
        }

        The above output is the dict form of:
        magnum.common.pythonk8sclient.swagger_client.models.v1_pod_list.
        V1PodList object

        :return: Memory size of each pod. Example:
            [{'Memory': 1280000.0},
             {'Memory': 1280000.0}]
        """
        pods = pods.items
        parsed_containers = []
        for pod in pods:
            containers = pod.spec.containers
            for container in containers:
                memory = 0
                resources = container.resources
                limits = resources.limits
                if limits is not None:
                    # Output of resources.limits is string
                    # for example:
                    # limits = "{'memory': '1000Ki'}"
                    limits = ast.literal_eval(limits)
                    if limits.get('memory', ''):
                        memory = utils.get_memory_bytes(limits['memory'])
                container_dict = {
                    'Memory': memory
                }
                parsed_containers.append(container_dict)
        return parsed_containers

    def _parse_node_info(self, nodes):
        """Parse nodes to retrieve memory of each node

        :param nodes: The output of k8s_api.list_namespaced_node()
        For example:
        {
            'items': [{
                'status': {
                    'phase': None,
                    'capacity': "{u'memory': u'2049852Ki'}",
                },
            },
            'api_version': None,
            }],
            'kind': 'NodeList',
            'api_version': 'v1',
        }

        The above output is the dict form of:
        magnum.common.pythonk8sclient.swagger_client.models.v1_node_list.
        V1NodeList object

        :return: Memory size of each node. Excample:
            [{'Memory': 1024.0},
             {'Memory': 1024.0}]

        """
        nodes = nodes.items
        parsed_nodes = []
        for node in nodes:
            # Output of node.status.capacity is strong
            # for example:
            # capacity = "{'memory': '1000Ki'}"
            capacity = ast.literal_eval(node.status.capacity)
            memory = utils.get_memory_bytes(capacity['memory'])
            parsed_nodes.append({'Memory': memory})

        return parsed_nodes
