# Copyright 2014 Rackspace US, Inc
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
import os

import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture

from magnum.common.cert_manager import cert_manager
from magnum.common.cert_manager import local_cert_manager
from magnum.tests import base


class TestLocalCert(base.BaseTestCase):

    def setUp(self):
        self.certificate = "My Certificate"
        self.intermediates = "My Intermediates"
        self.private_key = "My Private Key"
        self.private_key_passphrase = "My Private Key Passphrase"

        super(TestLocalCert, self).setUp()

    def test_local_cert(self):
        # Create a cert
        cert = local_cert_manager.Cert(
            certificate=self.certificate,
            intermediates=self.intermediates,
            private_key=self.private_key,
            private_key_passphrase=self.private_key_passphrase
        )

        # Validate the cert functions
        self.assertEqual(cert.get_certificate(), self.certificate)
        self.assertEqual(cert.get_intermediates(), self.intermediates)
        self.assertEqual(cert.get_private_key(), self.private_key)
        self.assertEqual(cert.get_private_key_passphrase(),
                         self.private_key_passphrase)


class TestLocalManager(base.BaseTestCase):

    def setUp(self):
        self.certificate = "My Certificate"
        self.intermediates = "My Intermediates"
        self.private_key = "My Private Key"
        self.private_key_passphrase = "My Private Key Passphrase"

        conf = oslo_fixture.Config(cfg.CONF)
        conf.config(group="certificates", storage_path="/tmp/")

        super(TestLocalManager, self).setUp()

    def _store_cert(self):
        file_mock = mock.mock_open()
        # Attempt to store the cert
        with mock.patch('__builtin__.open', file_mock, create=True):
            cert_id = local_cert_manager.CertManager.store_cert(
                certificate=self.certificate,
                intermediates=self.intermediates,
                private_key=self.private_key,
                private_key_passphrase=self.private_key_passphrase
            )

        # Check that something came back
        self.assertIsNotNone(cert_id)

        # Verify the correct files were opened
        file_mock.assert_has_calls([
            mock.call(os.path.join('/tmp/{0}.crt'.format(cert_id)), 'w'),
            mock.call(os.path.join('/tmp/{0}.key'.format(cert_id)), 'w'),
            mock.call(os.path.join('/tmp/{0}.int'.format(cert_id)), 'w'),
            mock.call(os.path.join('/tmp/{0}.pass'.format(cert_id)), 'w')
        ], any_order=True)

        # Verify the writes were made
        file_mock().write.assert_has_calls([
            mock.call(self.certificate),
            mock.call(self.intermediates),
            mock.call(self.private_key),
            mock.call(self.private_key_passphrase)
        ], any_order=True)

        return cert_id

    def _get_cert(self, cert_id):
        file_mock = mock.mock_open()
        # Attempt to retrieve the cert
        with mock.patch('__builtin__.open', file_mock, create=True):
            data = local_cert_manager.CertManager.get_cert(cert_id)

        # Verify the correct files were opened
        file_mock.assert_has_calls([
            mock.call(os.path.join('/tmp/{0}.crt'.format(cert_id)), 'r'),
            mock.call(os.path.join('/tmp/{0}.key'.format(cert_id)), 'r'),
            mock.call(os.path.join('/tmp/{0}.int'.format(cert_id)), 'r'),
            mock.call(os.path.join('/tmp/{0}.pass'.format(cert_id)), 'r')
        ], any_order=True)

        # The returned data should be a Cert object
        self.assertIsInstance(data, cert_manager.Cert)

        return data

    def _delete_cert(self, cert_id):
        remove_mock = mock.Mock()
        # Delete the cert
        with mock.patch('os.remove', remove_mock):
            local_cert_manager.CertManager.delete_cert(cert_id)

        # Verify the correct files were removed
        remove_mock.assert_has_calls([
            mock.call(os.path.join('/tmp/{0}.crt'.format(cert_id))),
            mock.call(os.path.join('/tmp/{0}.key'.format(cert_id))),
            mock.call(os.path.join('/tmp/{0}.int'.format(cert_id))),
            mock.call(os.path.join('/tmp/{0}.pass'.format(cert_id)))
        ], any_order=True)

    def test_store_cert(self):
        self._store_cert()

    def test_get_cert(self):
        # Store a cert
        cert_id = self._store_cert()

        # Get the cert
        self._get_cert(cert_id)

    def test_delete_cert(self):
        # Store a cert
        cert_id = self._store_cert()

        # Verify the cert exists
        self._get_cert(cert_id)

        # Delete the cert
        self._delete_cert(cert_id)
