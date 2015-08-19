# Copyright 2015 NEC Corporation.  All rights reserved.
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

from magnum.common.cert_manager import get_backend
from magnum.conductor.handlers.common import cert_manager
from magnum.tests import base


class CertManagerTestCase(base.BaseTestCase):

    @mock.patch('magnum.common.x509.operations.generate_ca_certificate')
    @mock.patch('magnum.common.short_id.generate_id')
    def test_generate_ca_cert(self, mock_generate_id, mock_generate_ca_cert):
        expected_ca_name = 'ca-name'
        expected_ca_password = 'password'
        expected_ca_cert = {
            'private_key': 'private_key', 'certificate': 'certificate'}
        expected_ca_cert_ref = 'ca_cert_ref'

        mock_generate_id.return_value = expected_ca_password
        mock_generate_ca_cert.return_value = expected_ca_cert

        with mock.patch.object(get_backend().CertManager,
                               'store_cert') as mock_store_cert:
            mock_store_cert.return_value = expected_ca_cert_ref
            self.assertEqual(
                cert_manager._generate_ca_cert(expected_ca_name),
                (expected_ca_cert_ref, expected_ca_cert,
                    expected_ca_password))

        mock_generate_ca_cert.assert_called_once_with(
            expected_ca_name, encryption_password=expected_ca_password)
        mock_store_cert.assert_called_once_with(
            certificate=expected_ca_cert['certificate'],
            private_key=expected_ca_cert['private_key'],
            private_key_passphrase=expected_ca_password,
            name=expected_ca_name,
        )

    @mock.patch('magnum.common.x509.operations.generate_client_certificate')
    @mock.patch('magnum.common.short_id.generate_id')
    def test_generate_client_cert(self, mock_generate_id, mock_generate_cert):
        expected_name = cert_manager.CONDUCTOR_CLIENT_NAME
        expected_ca_name = 'ca-name'
        expected_password = 'password'
        expected_ca_password = 'ca-password'
        expected_cert = {
            'private_key': 'private_key', 'certificate': 'certificate'}
        expected_ca_cert = {
            'private_key': 'ca_private_key', 'certificate': 'ca_certificate'}
        expected_cert_ref = 'cert_ref'

        mock_generate_id.return_value = expected_password
        mock_generate_cert.return_value = expected_cert

        with mock.patch.object(get_backend().CertManager,
                               'store_cert') as mock_store_cert:
            mock_store_cert.return_value = expected_cert_ref
            self.assertEqual(
                cert_manager._generate_client_cert(
                    expected_ca_name, expected_ca_cert, expected_ca_password),
                expected_cert_ref)

        mock_generate_cert.assert_called_once_with(
            expected_ca_name,
            expected_name,
            expected_ca_cert['private_key'],
            encryption_password=expected_password,
            ca_key_password=expected_ca_password,
        )
        mock_store_cert.assert_called_once_with(
            certificate=expected_cert['certificate'],
            private_key=expected_cert['private_key'],
            private_key_passphrase=expected_password,
            name=expected_name,
        )

    @mock.patch('magnum.conductor.handlers.common.cert_manager.'
                '_generate_client_cert')
    @mock.patch('magnum.conductor.handlers.common.cert_manager.'
                '_generate_ca_cert')
    def test_generate_certificates(self, mock_generate_ca_cert,
                                   mock_generate_client_cert):
        expected_ca_name = 'ca-name'
        expected_ca_password = 'ca-password'
        expected_ca_cert = {
            'private_key': 'ca_private_key', 'certificate': 'ca_certificate'}
        expected_cert_ref = 'cert_ref'
        expected_ca_cert_ref = 'ca-cert-ref'
        mock_bay = mock.MagicMock()
        mock_bay.name = expected_ca_name

        mock_generate_ca_cert.return_value = (expected_ca_cert_ref,
                                              expected_ca_cert,
                                              expected_ca_password)
        mock_generate_client_cert.return_value = expected_cert_ref

        cert_manager.generate_certificates_to_bay(mock_bay)
        self.assertEqual(mock_bay.ca_cert_ref, expected_ca_cert_ref)
        self.assertEqual(mock_bay.magnum_cert_ref, expected_cert_ref)

        mock_generate_ca_cert.assert_called_once_with(expected_ca_name)
        mock_generate_client_cert.assert_called_once_with(
            expected_ca_name, expected_ca_cert, expected_ca_password)
