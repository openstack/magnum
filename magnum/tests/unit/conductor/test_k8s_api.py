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

from unittest import mock

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

    def _mock_cert_mgr_get_cert(self, cert_ref, **kwargs):
        cert_obj = mock.MagicMock()
        cert_obj.get_certificate.return_value = (
            TestK8sAPI.content_dict[cert_ref]['certificate'])
        cert_obj.get_private_key.return_value = (
            TestK8sAPI.content_dict[cert_ref]['private_key'])
        cert_obj.get_decrypted_private_key.return_value = (
            TestK8sAPI.content_dict[cert_ref]['decrypted_private_key'])

        return cert_obj
