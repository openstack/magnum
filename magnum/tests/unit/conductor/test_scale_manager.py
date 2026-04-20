# Copyright 2015 Huawei Technologies Co.,LTD.
#
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

import tempfile
from unittest import mock

from requests_mock.contrib import fixture

from magnum.drivers.common.k8s_scale_manager import K8sScaleManager
from magnum.tests import base


class TestK8sScaleManager(base.TestCase):

    def setUp(self):
        super(TestK8sScaleManager, self).setUp()
        self.requests_mock = self.useFixture(fixture.Fixture())

    @mock.patch('magnum.objects.Cluster.get_by_uuid')
    @mock.patch('magnum.conductor.k8s_api.create_client_files')
    def test_get_hosts_with_container(
            self, mock_create_client_files, mock_get):
        mock_cluster = mock.MagicMock()
        mock_cluster.api_address = "https://foobar.com:6443"

        mock_create_client_files.return_value = (
            tempfile.NamedTemporaryFile(),
            tempfile.NamedTemporaryFile(),
            tempfile.NamedTemporaryFile()
        )

        self.requests_mock.register_uri(
            'GET',
            f"{mock_cluster.api_address}/api/v1/namespaces/default/pods",
            json={
                'items': [
                    {
                        'spec': {
                            'node_name': 'node1',
                        }
                    },
                    {
                        'spec': {
                            'node_name': 'node2',
                        }
                    }
                ]
            },
        )

        mgr = K8sScaleManager(
            mock.MagicMock(), mock.MagicMock(), mock.MagicMock())
        hosts = mgr._get_hosts_with_container(
            mock.MagicMock(), mock_cluster)
        self.assertEqual(hosts, {'node1', 'node2'})
