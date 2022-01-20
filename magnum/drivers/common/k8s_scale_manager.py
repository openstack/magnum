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

from magnum.conductor import k8s_api as k8s
from magnum.conductor.scale_manager import ScaleManager


class K8sScaleManager(ScaleManager):

    def __init__(self, context, osclient, cluster):
        super(K8sScaleManager, self).__init__(context, osclient, cluster)

    def _get_hosts_with_container(self, context, cluster):
        k8s_api = k8s.KubernetesAPI(context, cluster)
        hosts = set()
        for pod in k8s_api.list_namespaced_pod(namespace='default')['items']:
            hosts.add(pod['spec']['node_name'])

        return hosts
