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

from oslo_utils import strutils

from magnum.common import utils
from magnum.conductor import k8s_api as k8s
from magnum.conductor import monitors
from magnum.objects import fields as m_fields


class K8sMonitor(monitors.MonitorBase):

    def __init__(self, context, cluster):
        super(K8sMonitor, self).__init__(context, cluster)
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
        k8s_api = k8s.KubernetesAPI(self.context, self.cluster)
        nodes = k8s_api.list_node()
        self.data['nodes'] = self._parse_node_info(nodes)
        pods = k8s_api.list_namespaced_pod('default')
        self.data['pods'] = self._parse_pod_info(pods)

    def poll_health_status(self):
        if self._is_magnum_auto_healer_running():
            return

        k8s_api = k8s.KubernetesAPI(self.context, self.cluster)
        if self._is_cluster_accessible():
            status, reason = self._poll_health_status(k8s_api)
        else:
            status = m_fields.ClusterHealthStatus.UNKNOWN
            reason = {"api": "The cluster %s is not accessible." %
                      self.cluster.name}

        self.data['health_status'] = status
        self.data['health_status_reason'] = reason

    def _is_magnum_auto_healer_running(self):
        auto_healing = self.cluster.labels.get("auto_healing_enabled")
        auto_healing_enabled = strutils.bool_from_string(auto_healing)
        controller = self.cluster.labels.get("auto_healing_controller")
        return (auto_healing_enabled and controller == "magnum-auto-healer")

    def _is_cluster_accessible(self):
        if self.cluster.master_lb_enabled:
            lb_fip = self.cluster.labels.get("master_lb_floating_ip_enabled",
                                             self.cluster.floating_ip_enabled)
            return strutils.bool_from_string(lb_fip)
        else:
            return self.cluster.floating_ip_enabled

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

        :param pods: The output of k8s_api.list_namespaced_pod()
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
        pods = pods['items']
        parsed_containers = []
        for pod in pods:
            containers = pod['spec']['containers']
            for container in containers:
                memory = 0
                cpu = 0
                resources = container['resources']
                limits = resources['limits']
                if limits is not None:
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
            }],
            'api_version': None,
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
        nodes = nodes['items']
        parsed_nodes = []
        for node in nodes:
            # Output of node.status.capacity is strong
            # for example:
            # capacity = "{'cpu': '1', 'memory': '1000Ki'}"
            capacity = node['status']['capacity']
            memory = utils.get_k8s_quantity(capacity['memory'])
            cpu = int(capacity['cpu'])
            parsed_nodes.append({'Memory': memory, 'Cpu': cpu})

        return parsed_nodes

    def _poll_health_status(self, k8s_api):
        """Poll health status of API and nodes for given cluster

        Design Policy:
        1.  How to calculate the overall health status?
            Any node (including API and minion nodes) is not OK, then the
            overall health status is UNHEALTHY

        2.  The data structure of health_status_reason
            As an attribute of the cluster, the health_status_reason have to
            use the field type from
            oslo.versionedobjects/blob/master/oslo_versionedobjects/fields.py

        3.  How to get the health_status and health_status_reason?
            3.1 Call /healthz to get the API health status
            3.2 Call list_node (using API /api/v1/nodes) to get the nodes
                health status

        :param k8s_api: The api client to the cluster
        :return: Tumple including status and reason. Example:
            (
                ClusterHealthStatus.HEALTHY,
                {
                    'api': 'ok',
                    'k8scluster-ydz7cfbxqqu3-node-0.Ready': False,
                    'k8scluster-ydz7cfbxqqu3-node-1.Ready': True,
                    'k8scluster-ydz7cfbxqqu3-node-2.Ready': True,
                }
            )

        """

        health_status = m_fields.ClusterHealthStatus.UNHEALTHY
        health_status_reason = {}
        api_status = None

        try:
            api_status = k8s_api.get_healthz()

            for node in k8s_api.list_node()['items']:
                node_key = node['metadata']['name'] + ".Ready"
                ready = False
                for condition in node['status']['conditions']:
                    if condition['type'] == 'Ready':
                        ready = strutils.bool_from_string(condition['status'])
                        break

                health_status_reason[node_key] = ready

            if (api_status == 'ok' and
                    all(n for n in health_status_reason.values())):
                health_status = m_fields.ClusterHealthStatus.HEALTHY

            health_status_reason['api'] = api_status
        except Exception as exp_api:
            if not api_status:
                api_status = (getattr(exp_api, 'body', None) or
                              getattr(exp_api, 'message', None))
                if api_status is not None:
                    health_status_reason['api'] = api_status

        return health_status, health_status_reason
