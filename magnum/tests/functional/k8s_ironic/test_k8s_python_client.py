# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from magnum.tests.functional import python_client_base as base


class TestFedoraKubernetesIronicAPIs(base.BaseK8sTest):
    cluster_complete_timeout = 3200
    cluster_template_kwargs = {
        "tls_disabled": True,
        "network_driver": 'flannel',
        "volume_driver": None,
        "fixed_subnet": 'private-subnet',
        "server_type": 'bm',
        "docker_storage_driver": 'overlay',
        "labels": {
            "system_pods_initial_delay": 3600,
            "system_pods_timeout": 600,
            "kube_dashboard_enabled": False
        }
    }
