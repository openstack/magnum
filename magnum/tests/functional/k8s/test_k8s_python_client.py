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

from magnum.common.pythonk8sclient.swagger_client import api_client
from magnum.common.pythonk8sclient.swagger_client.apis import apiv_api
from magnum.tests.functional.common import utils
from magnum.tests.functional.python_client_base import BayTest


class TestKubernetesAPIs(BayTest):
    coe = 'kubernetes'
    baymodel_kwargs = {
        "tls_disabled": False,
        "network_driver": 'flannel',
        "volume_driver": 'cinder',
        "fixed_network": '192.168.0.0/24'
    }

    def setUp(self):
        super(TestKubernetesAPIs, self).setUp()
        self.kube_api_url = self.cs.bays.get(self.bay.uuid).api_address
        k8s_client = api_client.ApiClient(self.kube_api_url,
                                          key_file=self.key_file,
                                          cert_file=self.cert_file,
                                          ca_certs=self.ca_file)
        self.k8s_api = apiv_api.ApivApi(k8s_client)
        # TODO(coreypobrien) https://bugs.launchpad.net/magnum/+bug/1551824
        utils.wait_for_condition(self._is_api_ready, 5, 600)

    def _is_api_ready(self):
        try:
            self.k8s_api.list_namespaced_node()
            self.LOG.info("API is ready.")
            return True
        except Exception:
            self.LOG.info("API is not ready yet.")
            return False

    def test_pod_apis(self):
        pod_manifest = {'apiVersion': 'v1',
                        'kind': 'Pod',
                        'metadata': {'color': 'blue', 'name': 'test'},
                        'spec': {'containers': [{'image': 'dockerfile/redis',
                                 'name': 'redis'}]}}

        resp = self.k8s_api.create_namespaced_pod(body=pod_manifest,
                                                  namespace='default')
        self.assertEqual('test', resp.metadata.name)
        self.assertTrue(resp.status.phase)

        resp = self.k8s_api.read_namespaced_pod(name='test',
                                                namespace='default')
        self.assertEqual('test', resp.metadata.name)
        self.assertTrue(resp.status.phase)

        resp = self.k8s_api.delete_namespaced_pod(name='test', body={},
                                                  namespace='default')

    def test_service_apis(self):
        service_manifest = {'apiVersion': 'v1',
                            'kind': 'Service',
                            'metadata': {'labels': {'name': 'frontend'},
                                         'name': 'frontend',
                                         'resourceversion': 'v1'},
                            'spec': {'ports': [{'port': 80,
                                                'protocol': 'TCP',
                                                'targetPort': 80}],
                                     'selector': {'name': 'frontend'}}}

        resp = self.k8s_api.create_namespaced_service(body=service_manifest,
                                                      namespace='default')
        self.assertEqual('frontend', resp.metadata.name)
        self.assertTrue(resp.status)

        resp = self.k8s_api.read_namespaced_service(name='frontend',
                                                    namespace='default')
        self.assertEqual('frontend', resp.metadata.name)
        self.assertTrue(resp.status)

        resp = self.k8s_api.delete_namespaced_service(name='frontend',
                                                      namespace='default')

    def test_replication_controller_apis(self):
        rc_manifest = {
            'apiVersion': 'v1',
            'kind': 'ReplicationController',
            'metadata': {'labels': {'name': 'frontend'},
                         'name': 'frontend'},
            'spec': {'replicas': 2,
                     'selector': {'name': 'frontend'},
                     'template': {'metadata': {
                         'labels': {'name': 'frontend'}},
                         'spec': {'containers': [{
                             'image': 'nginx',
                             'name': 'nginx',
                             'ports': [{'containerPort': 80,
                                        'protocol': 'TCP'}]}]}}}}

        resp = self.k8s_api.create_namespaced_replication_controller(
            body=rc_manifest, namespace='default')
        self.assertEqual('frontend', resp.metadata.name)
        self.assertEqual(2, resp.spec.replicas)

        resp = self.k8s_api.read_namespaced_replication_controller(
            name='frontend', namespace='default')
        self.assertEqual('frontend', resp.metadata.name)
        self.assertEqual(2, resp.spec.replicas)

        resp = self.k8s_api.delete_namespaced_replication_controller(
            name='frontend', body={}, namespace='default')

    """
    NB : Bug1504379. This is placeholder and will be removed when all
         the objects-from-bay patches are checked in.
    def test_pods_list(self):
        self.assertIsNotNone(self.cs.pods.list(self.bay.uuid))

    def test_rcs_list(self):
        self.assertIsNotNone(self.cs.rcs.list(self.bay.uuid))

    def test_services_list(self):
        self.assertIsNotNone(self.cs.services.list(self.bay.uuid))
    """
