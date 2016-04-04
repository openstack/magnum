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
from magnum.tests import base


class TestK8sAPI(base.TestCase):
    content_dict = {
        'fake-magnum-cert-ref': {
            'certificate': 'certificate-content',
            'private_key': 'private-key-content',
            'decrypted_private_key': 'private-key-content',
        },
        'fake-ca-cert-ref': {
            'certificate': 'ca-cert-content',
            'private_key': None,
            'decrypted_private_key': None,
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

    def _mock_cert_mgr_get_cert(self, cert_ref, **kwargs):
        cert_obj = mock.MagicMock()
        cert_obj.get_certificate.return_value = (
            TestK8sAPI.content_dict[cert_ref]['certificate'])
        cert_obj.get_private_key.return_value = (
            TestK8sAPI.content_dict[cert_ref]['private_key'])
        cert_obj.get_decrypted_private_key.return_value = (
            TestK8sAPI.content_dict[cert_ref]['decrypted_private_key'])

        return cert_obj

    @patch(
        'magnum.conductor.handlers.common.cert_manager.get_bay_ca_certificate')
    @patch('magnum.conductor.handlers.common.cert_manager.get_bay_magnum_cert')
    @patch('k8sclient.client.api_client.ApiClient')
    def test_create_k8s_api(self,
                            mock_api_client,
                            mock_get_bay_magnum_cert,
                            mock_get_bay_ca_cert):
        bay_obj = mock.MagicMock()
        bay_obj.uuid = 'bay-uuid'
        bay_obj.api_address = 'fake-k8s-api-endpoint'
        bay_obj.magnum_cert_ref = 'fake-magnum-cert-ref'
        bay_obj.ca_cert_ref = 'fake-ca-cert-ref'

        mock_get_bay_magnum_cert.return_value = self._mock_cert_mgr_get_cert(
            'fake-magnum-cert-ref')
        mock_get_bay_ca_cert.return_value = self._mock_cert_mgr_get_cert(
            'fake-ca-cert-ref')

        file_dict = TestK8sAPI.file_dict
        for content in file_dict.keys():
            file_hdl = file_dict[content]
            file_hdl.name = TestK8sAPI.file_name[content]

        context = 'context'
        with patch(
            'magnum.conductor.k8s_api.K8sAPI._create_temp_file_with_content',
                side_effect=self._mock_named_file_creation):
            k8s_api.create_k8s_api(context, bay_obj)

        mock_api_client.assert_called_once_with(
            bay_obj.api_address,
            key_file='priv-key-temp-file-name',
            cert_file='cert-temp-file-name',
            ca_certs='ca-cert-temp-file-name')
