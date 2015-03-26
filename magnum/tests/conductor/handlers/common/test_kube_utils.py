# Copyright 2014 NEC Corporation.  All rights reserved.
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

from magnum.common import exception
from magnum.conductor.handlers.common import kube_utils
from magnum.tests import base

import mock
from mock import patch


class TestKubeUtils(base.BaseTestCase):
    def setUp(self):
        super(TestKubeUtils, self).setUp()

    @patch('magnum.conductor.handlers.common.kube_utils._k8s_create_with_data')
    def test_k8s_create_data(self,
                             mock_create_with_data):
        expected_data = 'data'
        api_address = 'api_address'
        mock_resource = mock.MagicMock()
        mock_resource.manifest = expected_data
        mock_resource.manifest_url = None

        kube_utils._k8s_create(api_address, mock_resource)
        mock_create_with_data.assert_called_once_with(api_address,
                                                      expected_data)

    @patch('magnum.conductor.handlers.common.kube_utils._k8s_create_with_path')
    def test_k8s_create_url(self,
                             mock_create_with_path):
        expected_url = 'url'
        api_address = 'api_address'
        mock_resource = mock.MagicMock()
        mock_resource.manifest = None
        mock_resource.manifest_url = expected_url

        kube_utils._k8s_create(api_address, mock_resource)
        mock_create_with_path.assert_called_once_with(api_address,
                                                      expected_url)

    @patch('magnum.openstack.common.utils.trycmd')
    def test_k8s_create_with_path(self, mock_trycmd):
        expected_api_address = 'api_address'
        expected_pod_file = 'pod_file'
        expected_command = [
            'kubectl', 'create',
            '-s', expected_api_address,
            '-f', expected_pod_file
        ]

        kube_utils._k8s_create_with_path(expected_api_address,
                                         expected_pod_file)
        mock_trycmd.assert_called_once_with(*expected_command)

    @patch('magnum.conductor.handlers.common.kube_utils._k8s_create_with_path')
    @patch('tempfile.NamedTemporaryFile')
    def test_k8s_create_with_data(self,
                                  mock_named_tempfile,
                                  mock_k8s_create):
        expected_api_address = 'api_address'
        expected_data = 'resource_data'
        expected_filename = 'resource_file'

        mock_file = mock.MagicMock()
        mock_file.name = expected_filename
        mock_named_tempfile.return_value.__enter__.return_value = mock_file

        kube_utils._k8s_create_with_data(expected_api_address,
            expected_data)

        mock_file.write.assert_called_once_with(expected_data)
        mock_k8s_create.assert_called_once_with(expected_api_address,
                                                expected_filename)

    @patch('magnum.conductor.handlers.common.kube_utils._k8s_update_with_data')
    def test_k8s_update_data(self,
                             mock_update_with_data):
        expected_data = 'data'
        api_address = 'api_address'
        mock_resource = mock.MagicMock()
        mock_resource.manifest = expected_data
        mock_resource.manifest_url = None

        kube_utils._k8s_update(api_address, mock_resource)
        mock_update_with_data.assert_called_once_with(api_address,
                                                      expected_data)

    @patch('magnum.conductor.handlers.common.kube_utils._k8s_update_with_path')
    def test_k8s_update_url(self,
                            mock_update_with_path):
        expected_url = 'url'
        api_address = 'api_address'
        mock_resource = mock.MagicMock()
        mock_resource.manifest = None
        mock_resource.manifest_url = expected_url

        kube_utils._k8s_update(api_address, mock_resource)
        mock_update_with_path.assert_called_once_with(api_address,
                                                      expected_url)

    @patch('magnum.openstack.common.utils.trycmd')
    def test_k8s_update_with_path(self, mock_trycmd):
        expected_api_address = 'api_address'
        expected_pod_file = 'pod_file'
        expected_command = [
            'kubectl', 'update',
            '-s', expected_api_address,
            '-f', expected_pod_file
        ]

        kube_utils._k8s_update_with_path(expected_api_address,
                                         expected_pod_file)
        mock_trycmd.assert_called_once_with(*expected_command)

    @patch('magnum.conductor.handlers.common.kube_utils._k8s_update_with_path')
    @patch('tempfile.NamedTemporaryFile')
    def test_k8s_update_with_data(self,
                                  mock_named_tempfile,
                                  mock_k8s_update):
        expected_api_address = 'api_address'
        expected_data = 'resource_data'
        expected_filename = 'resource_file'

        mock_file = mock.MagicMock()
        mock_file.name = expected_filename
        mock_named_tempfile.return_value.__enter__.return_value = mock_file

        kube_utils._k8s_update_with_data(expected_api_address,
            expected_data)

        mock_file.write.assert_called_once_with(expected_data)
        mock_k8s_update.assert_called_once_with(expected_api_address,
                                                expected_filename)


class KubeClientTestCase(base.TestCase):
    def setUp(self):
        super(KubeClientTestCase, self).setUp()
        self.kube_client = kube_utils.KubeClient()

    @patch('magnum.openstack.common.utils.trycmd')
    def test_pod_delete(self, mock_trycmd):
        expected_api_address = 'master-address'
        expected_pod_name = 'test-pod'
        expected_command = [
            'kubectl', 'delete', 'pod', expected_pod_name,
            '-s', expected_api_address
        ]
        mock_trycmd.return_value = ("", "")

        result = self.kube_client.pod_delete(expected_api_address,
                                             expected_pod_name)
        self.assertTrue(result)
        mock_trycmd.assert_called_once_with(*expected_command)

    @patch('magnum.openstack.common.utils.trycmd')
    def test_pod_delete_failure_err_not_empty(self, mock_trycmd):
        expected_api_address = 'master-address'
        expected_pod_name = 'test-pod'
        expected_command = [
            'kubectl', 'delete', 'pod', expected_pod_name,
            '-s', expected_api_address
        ]
        mock_trycmd.return_value = ("", "error")

        result = self.kube_client.pod_delete(expected_api_address,
                                             expected_pod_name)
        self.assertFalse(result)
        mock_trycmd.assert_called_once_with(*expected_command)

    @patch('magnum.openstack.common.utils.trycmd')
    def test_pod_delete_failure_exception(self, mock_trycmd):
        expected_api_address = 'master-address'
        expected_pod_name = 'test-pod'
        expected_command = [
            'kubectl', 'delete', 'pod', expected_pod_name,
            '-s', expected_api_address
        ]
        mock_trycmd.side_effect = Exception()

        result = self.kube_client.pod_delete(expected_api_address,
                                             expected_pod_name)
        self.assertFalse(result)
        mock_trycmd.assert_called_once_with(*expected_command)

    @patch('magnum.openstack.common.utils.trycmd')
    def test_pod_delete_not_found_old(self, mock_trycmd):
        expected_api_address = 'master-address'
        expected_pod_name = 'test-pod'
        expected_command = [
            'kubectl', 'delete', 'pod', expected_pod_name,
            '-s', expected_api_address
        ]
        mock_trycmd.return_value = ("", 'pod "test-pod" not found')

        self.assertRaises(exception.PodNotFound, self.kube_client.pod_delete,
                          expected_api_address, expected_pod_name)

        mock_trycmd.assert_called_once_with(*expected_command)

    @patch('magnum.openstack.common.utils.trycmd')
    def test_pod_delete_not_found_new(self, mock_trycmd):
        expected_api_address = 'master-address'
        expected_pod_name = 'test-pod'
        expected_command = [
            'kubectl', 'delete', 'pod', expected_pod_name,
            '-s', expected_api_address
        ]
        mock_trycmd.return_value = ("", 'pods "test-pod" not found')

        self.assertRaises(exception.PodNotFound, self.kube_client.pod_delete,
                          expected_api_address, expected_pod_name)

        mock_trycmd.assert_called_once_with(*expected_command)

    @patch('magnum.openstack.common.utils.trycmd')
    def test_service_delete(self, mock_trycmd):
        expected_api_address = 'master-address'
        expected_service_name = 'test-service'
        expected_command = [
            'kubectl', 'delete', 'service', expected_service_name,
            '-s', expected_api_address
        ]
        mock_trycmd.return_value = ("", "")

        result = self.kube_client.service_delete(expected_api_address,
                                             expected_service_name)
        self.assertTrue(result)
        mock_trycmd.assert_called_once_with(*expected_command)

    @patch('magnum.openstack.common.utils.trycmd')
    def test_service_delete_failure_exception(self, mock_trycmd):
        expected_api_address = 'master-address'
        expected_service_name = 'test-service'
        expected_command = [
            'kubectl', 'delete', 'service', expected_service_name,
            '-s', expected_api_address
        ]
        mock_trycmd.side_effect = Exception()

        result = self.kube_client.service_delete(expected_api_address,
                                             expected_service_name)
        self.assertFalse(result)
        mock_trycmd.assert_called_once_with(*expected_command)
