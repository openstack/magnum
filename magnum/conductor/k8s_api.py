# Copyright 2015 Huawei Technologies Co.,LTD.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import requests

from magnum.conductor.handlers.common.cert_manager import create_client_files


class KubernetesAPI:
    """Simple Kubernetes API client using requests.

    This API wrapper allows for a set of very simple operations to be
    performed on a Kubernetes cluster using the `requests` library. The
    reason behind it is that the native `kubernetes` library does not
    seem to be quite thread-safe at the moment.

    Also, our interactions with the Kubernetes API are happening inside
    Greenthreads so we don't need to use connection pooling on top of it,
    in addition to pools not being something that you can disable with
    the native Kubernetes API.
    """

    def __init__(self, context, cluster):
        self.context = context
        self.cluster = cluster

        # Load certificates for cluster
        (self.ca_file, self.key_file, self.cert_file) = create_client_files(
            self.cluster, self.context
        )

    def _request(self, method, url, json=True):
        response = requests.request(
            method,
            url,
            verify=self.ca_file.name,
            cert=(self.cert_file.name, self.key_file.name)
        )
        response.raise_for_status()
        if json:
            return response.json()
        else:
            return response.text

    def get_healthz(self):
        """Get the health of the cluster from API"""
        return self._request(
            'GET',
            f"{self.cluster.api_address}/healthz",
            json=False
        )

    def list_node(self):
        """List all nodes in the cluster.

        :return: List of nodes.
        """
        return self._request(
            'GET',
            f"{self.cluster.api_address}/api/v1/nodes"
        )

    def list_namespaced_pod(self, namespace):
        """List all pods in the given namespace.

        :param namespace: Namespace to list pods from.
        :return: List of pods.
        """
        return self._request(
            'GET',
            f"{self.cluster.api_address}/api/v1/namespaces/{namespace}/pods"
        )

    def __del__(self):
        """Close all of the file descriptions for the certificates

        They are left open by `create_client_files`.

        TODO(mnaser): Use a context manager and avoid having these here.
        """
        if hasattr(self, 'ca_file'):
            self.ca_file.close()
        if hasattr(self, 'cert_file'):
            self.cert_file.close()
        if hasattr(self, 'key_file'):
            self.key_file.close()
