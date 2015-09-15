# Copyright 2015 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from magnum import objects
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils

import mock


class TestPodObject(base.DbTestCase):

    def setUp(self):
        super(TestPodObject, self).setUp()
        self.fake_pod = utils.get_test_pod()

    @mock.patch('magnum.conductor.k8s_api.create_k8s_api')
    @mock.patch('ast.literal_eval')
    def test_get_by_uuid(self, mock_ast, mock_kube_api):
        uuid = self.fake_pod['uuid']
        bay_uuid = self.fake_pod['bay_uuid']
        mock_ast.return_value = {}

        k8s_api_mock = mock.MagicMock()
        mock_kube_api.return_value = k8s_api_mock

        fake_obj = mock.MagicMock()

        items = [
            {
                'metadata': {
                    'uid': '10a47dd1-4874-4298-91cf-eff046dbdb8d',
                    'name': 'fake-name',
                    'labels': {}
                },
                'spec': {
                    'node_name': 'fake-node',
                    'containers': [
                        {
                            'image': 'fake-image'
                        }
                    ]
                },
                'status': {
                    'phase': 'CREATED'
                }
            }
        ]

        fake_obj.items = items
        fake_obj.items[0] = mock.MagicMock()
        fake_obj.items[0].metadata = mock.MagicMock()
        fake_obj.items[0].metadata.uid = '10a47dd1-4874-4298-91cf-eff046dbdb8d'
        fake_obj.items[0].metadata.name = 'fake-name'
        fake_obj.items[0].spec = mock.MagicMock()
        fake_obj.items[0].spec.node_name = 'fake-host'
        fake_obj.items[0].status = mock.MagicMock()
        fake_obj.items[0].status.phase = 'fake-status'
        k8s_api_mock.list_namespaced_pod.return_value = fake_obj
        objects.Pod.get_by_uuid(self.context,
                                uuid, bay_uuid,
                                k8s_api_mock)
        (k8s_api_mock.list_namespaced_pod.assert_called_once_with(
            namespace='default'))

    @mock.patch('magnum.conductor.k8s_api.create_k8s_api')
    @mock.patch('ast.literal_eval')
    def test_get_by_name(self, mock_ast, mock_kube_api):
        name = self.fake_pod['name']
        bay_uuid = self.fake_pod['bay_uuid']

        mock_ast.return_value = {}
        k8s_api_mock = mock.MagicMock()
        mock_kube_api.return_value = k8s_api_mock
        fake_pod = mock.MagicMock()
        fake_pod.metadata.uid = 'fake-uuid'
        fake_pod.metadata.name = 'fake-name'
        fake_pod.spec.containers[0].image = ['fake-image']
        fake_pod.metadata.labels = {}
        fake_pod.status.phase = 'fake-status'
        fake_pod.spec.node_name = 'fake-host'
        k8s_api_mock.read_namespaced_pod.return_value = fake_pod
        objects.Pod.get_by_name(self.context,
                                name, bay_uuid,
                                k8s_api_mock)
        (k8s_api_mock.read_namespaced_pod.assert_called_once_with(
            name=name,
            namespace='default'))
