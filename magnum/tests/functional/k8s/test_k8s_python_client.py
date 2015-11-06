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
from magnum.tests.functional.python_client_base import BayAPITLSTest
from magnum.tests.functional.python_client_base import BayTest


class TestBayModelResource(BayTest):
    coe = 'kubernetes'

    def test_baymodel_create_and_delete(self):
        self._test_baymodel_create_and_delete('test_k8s_baymodel')


class TestBayResource(BayTest):
    coe = 'kubernetes'

    def test_bay_create_and_delete(self):
        baymodel_uuid = self._test_baymodel_create_and_delete(
            'test_k8s_baymodel', delete=False, tls_disabled=True)
        self._test_bay_create_and_delete('test_k8s_bay', baymodel_uuid)


class TestKubernetesAPIs(BayAPITLSTest):
    @classmethod
    def setUpClass(cls):
        super(TestKubernetesAPIs, cls).setUpClass()

        cls.baymodel = cls._create_baymodel('testk8sAPI',
                                            coe='kubernetes',
                                            tls_disabled=False,
                                            network_driver='flannel',
                                            fixed_network='192.168.0.0/24',
                                            )
        cls.bay = cls._create_bay('testk8sAPI', cls.baymodel.uuid)

        config_contents = """[req]
distinguished_name = req_distinguished_name
req_extensions     = req_ext
prompt = no
[req_distinguished_name]
CN = Your Name
[req_ext]
extendedKeyUsage = clientAuth
"""
        cls._create_tls_ca_files(config_contents)
        cls.kube_api_url = cls.cs.bays.get(cls.bay.uuid).api_address
        k8s_client = api_client.ApiClient(cls.kube_api_url,
                                          key_file=cls.key_file,
                                          cert_file=cls.cert_file,
                                          ca_certs=cls.ca_file)
        cls.k8s_api = apiv_api.ApivApi(k8s_client)

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
