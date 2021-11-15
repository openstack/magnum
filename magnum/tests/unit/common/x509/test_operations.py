# Copyright 2015 Rackspace, inc.  All rights reserved.
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

from cryptography.hazmat.primitives import serialization
from unittest import mock

from magnum.common.x509 import operations
from magnum.tests import base


class TestX509Operations(base.BaseTestCase):
    def setUp(self):
        super(TestX509Operations, self).setUp()

    @mock.patch.object(serialization, 'NoEncryption')
    @mock.patch.object(operations, '_load_pem_private_key')
    def test_decrypt_key(self, mock_load_pem_private_key,
                         mock_no_encryption_class):
        mock_private_key = mock.MagicMock()
        mock_load_pem_private_key.return_value = mock_private_key
        mock_private_key.private_bytes.return_value = mock.sentinel.decrypted

        actual_decrypted = operations.decrypt_key(mock.sentinel.key,
                                                  mock.sentinel.passphrase)

        mock_load_pem_private_key.assert_called_once_with(
            mock.sentinel.key, mock.sentinel.passphrase)
        mock_private_key.private_bytes.assert_called_once_with(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=mock_no_encryption_class.return_value
        )
        self.assertEqual(mock.sentinel.decrypted, actual_decrypted)

    def test_generate_csr_and_key(self):
        csr_keys = operations.generate_csr_and_key(u"Test")
        self.assertIsNotNone(csr_keys)
        self.assertTrue("public_key" in csr_keys)
        self.assertTrue("private_key" in csr_keys)
