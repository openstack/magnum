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

import mock
from mock import patch

from magnum.conductor import k8s_api
from magnum import objects
from magnum.tests import base


class TestK8sAPI(base.TestCase):
    content_dict = {
        'fake-magnum-cert-ref': {
            'certificate': 'certificate-content',
            'private_key': 'private-key-content'
        },
        'fake-ca-cert-ref': {
            'certificate': 'ca-cert-content',
            'private_key': None
        }
    }
    file_dict = {
        'ca-cert-content': mock.MagicMock(),
        'certificate-content': mock.MagicMock(),
        'private-key-content': mock.MagicMock()
    }
    file_name = {
        'ca-cert-content': 'ca-cert-temp-file-name',
        'certificate-content': 'cert-temp-file-name',
        'private-key-content': 'priv-key-temp-file-name'
    }

    def _mock_named_file_creation(self, content):
        return TestK8sAPI.file_dict[content]

    def _mock_cert_mgr_get_cert(self, cert_ref):
        cert_obj = mock.MagicMock()
        cert_obj.certificate = TestK8sAPI.content_dict[cert_ref]['certificate']
        cert_obj.private_key = TestK8sAPI.content_dict[cert_ref]['private_key']
        return cert_obj

    @patch('magnum.conductor.k8s_api.serialization.load_pem_private_key')
    @patch('magnum.conductor.utils.retrieve_bay')
    @patch('magnum.common.pythonk8sclient.swagger_client.api_client.ApiClient')
    @patch(
        'magnum.common.pythonk8sclient.swagger_client.apis.apiv_api.ApivApi')
    def _test_create_k8s_api(self, cls,
                             mock_api_vapi,
                             mock_api_client,
                             mock_bay_retrieval,
                             mock_load_pem_private_key):
        bay_obj = mock.MagicMock()
        bay_obj.uuid = 'bay-uuid'
        bay_obj.api_address = 'fake-k8s-api-endpoint'
        bay_obj.magnum_cert_ref = 'fake-magnum-cert-ref'
        bay_obj.ca_cert_ref = 'fake-ca-cert-ref'
        mock_bay_retrieval.return_value = bay_obj
        mock_private_bytes = mock.MagicMock()
        mock_load_pem_private_key.return_value = mock_private_bytes
        mock_private_bytes.private_bytes = mock.MagicMock(
            return_value='private-key-content')

        file_dict = TestK8sAPI.file_dict
        for content in file_dict.keys():
            file_hdl = file_dict[content]
            file_hdl.name = TestK8sAPI.file_name[content]

        context = 'context'

        obj = getattr(objects, cls)({})
        self.assertFalse(hasattr(obj, 'bay_uuid'))
        obj.bay_uuid = 'bay-uuid'

        with patch(
            'magnum.conductor.k8s_api.K8sAPI._create_temp_file_with_content',
                side_effect=self._mock_named_file_creation):
            with patch(
                'magnum.common.cert_manager.local_cert_manager'
                    '.CertManager.get_cert',
                    side_effect=self._mock_cert_mgr_get_cert):
                with patch(
                    'magnum.common.cert_manager.barbican_cert_manager'
                        '.CertManager.get_cert',
                        side_effect=self._mock_cert_mgr_get_cert):
                    k8s_api.create_k8s_api(context, obj)

        mock_bay_retrieval.assert_called_once_with(context, obj)

        mock_api_client.assert_called_once_with(
            bay_obj.api_address,
            key_file='priv-key-temp-file-name',
            cert_file='cert-temp-file-name',
            ca_certs='ca-cert-temp-file-name')

    def test_create_k8s_api_with_service(self):
        self._test_create_k8s_api('Service')

    def test_create_k8s_api_with_bay(self):
        self._test_create_k8s_api('Bay')

    def test_create_k8s_api_with_pod(self):
        self._test_create_k8s_api('Pod')

    def test_create_k8s_api_with_rc(self):
        self._test_create_k8s_api('ReplicationController')
