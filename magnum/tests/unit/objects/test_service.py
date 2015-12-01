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


class TestServiceObject(base.DbTestCase):

    def setUp(self):
        super(TestServiceObject, self).setUp()
        self.fake_service = utils.get_test_service()

    @mock.patch('magnum.conductor.k8s_api.create_k8s_api')
    @mock.patch('ast.literal_eval')
    def test_get_by_uuid(self, mock_ast, mock_kube_api):
        uuid = self.fake_service['uuid']
        bay_uuid = self.fake_service['bay_uuid']
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
                    'selector': {},
                    'cluster_ip': '10.98.100.19',
                    'ports': [
                        {
                            'port': 80
                        }
                    ]
                }
            }
        ]

        fake_obj.items = items
        fake_obj.items[0] = mock.MagicMock()
        fake_obj.items[0].metadata = mock.MagicMock()
        fake_obj.items[0].metadata.uid = '10a47dd1-4874-4298-91cf-eff046dbdb8d'
        fake_obj.items[0].metadata.name = 'fake-name'
        fake_obj.items[0].spec = mock.MagicMock()
        fake_obj.items[0].spec.selector = {}
        fake_obj.items[0].spec.cluster_ip = '10.98.100.19'

        k8s_api_mock.list_namespaced_service.return_value = fake_obj

        objects.Service.get_by_uuid(self.context,
                                    uuid, bay_uuid,
                                    k8s_api_mock)

        (k8s_api_mock.list_namespaced_service.assert_called_once_with(
            namespace='default'))

    @mock.patch('magnum.conductor.k8s_api.create_k8s_api')
    @mock.patch('ast.literal_eval')
    def test_get_by_name(self, mock_ast, mock_kube_api):
        name = self.fake_service['name']
        bay_uuid = self.fake_service['bay_uuid']
        mock_ast.return_value = {}

        k8s_api_mock = mock.MagicMock()
        mock_kube_api.return_value = k8s_api_mock
        fake_service = mock.MagicMock()
        fake_service.metadata.uid = 'fake-uuid'
        fake_service.metadata.name = 'fake-name'
        fake_service.spec.ports.port = ["1234"]
        fake_service.spec.selector = {}
        fake_service.spec.cluster_ip = '192.10.10.10'
        fake_service.metadata.labels = mock_ast.return_value
        k8s_api_mock.read_namespaced_service.return_value = fake_service
        objects.Service.get_by_name(self.context,
                                    name, bay_uuid,
                                    k8s_api_mock)
        (k8s_api_mock.read_namespaced_service.assert_called_once_with(
            name=name,
            namespace='default'))
