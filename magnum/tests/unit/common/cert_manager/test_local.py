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
from unittest import mock

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture

from magnum.common.cert_manager import cert_manager
from magnum.common.cert_manager import local_cert_manager
from magnum.common import exception
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
        self.assertEqual(self.certificate, cert.get_certificate())
        self.assertEqual(self.intermediates, cert.get_intermediates())
        self.assertEqual(self.private_key, cert.get_private_key())
        self.assertEqual(self.private_key_passphrase,
                         cert.get_private_key_passphrase())


class TestLocalManager(base.BaseTestCase):

    def setUp(self):
        self.certificate = "My Certificate"
        self.intermediates = "My Intermediates"
        self.private_key = "My Private Key"
        self.private_key_passphrase = "My Private Key Passphrase"

        def _mock_isfile(path):
            _, ext = os.path.splitext(path)
            if self.intermediates is None and ext == '.int':
                return False
            if self.private_key_passphrase is None and ext == '.pass':
                return False
            return True
        isfile_patcher = mock.patch('os.path.isfile')
        self.mock_isfile = isfile_patcher.start()
        self.addCleanup(isfile_patcher.stop)
        self.mock_isfile.side_effect = _mock_isfile

        conf = oslo_fixture.Config(cfg.CONF)
        conf.config(group="certificates", storage_path="/tmp/")

        super(TestLocalManager, self).setUp()

    def _open_calls(self, cert_id, mode='w'):
        open_calls = []
        unexpected_calls = []
        for ext in ['crt', 'key', 'int', 'pass']:
            args = [os.path.join('/tmp/{0}.{1}'.format(cert_id, ext))]
            if mode:
                args.append(mode)

            call = mock.call(*args)
            if ext == 'int' and not self.intermediates:
                unexpected_calls.append(call)
            elif ext == 'pass' and not self.private_key_passphrase:
                unexpected_calls.append(call)
            else:
                open_calls.append(call)
        return open_calls, unexpected_calls

    def _write_calls(self):
        write_calls = [
            mock.call(self.certificate),
            mock.call(self.private_key),
        ]
        if self.intermediates:
            write_calls.append(mock.call(self.intermediates))
        if self.private_key_passphrase:
            write_calls.append(mock.call(self.private_key_passphrase))
        return write_calls

    def _store_cert(self):
        file_mock = mock.mock_open()
        # Attempt to store the cert
        with mock.patch('builtins.open', file_mock, create=True):
            cert_id = local_cert_manager.CertManager.store_cert(
                certificate=self.certificate,
                intermediates=self.intermediates,
                private_key=self.private_key,
                private_key_passphrase=self.private_key_passphrase
            )

        # Check that something came back
        self.assertIsNotNone(cert_id)

        # Verify the correct files were opened
        open_calls, unexpected_calls = self._open_calls(cert_id)
        file_mock.assert_has_calls(open_calls, any_order=True)
        for unexpected_call in unexpected_calls:
            self.assertNotIn(unexpected_call, file_mock.mock_calls)

        # Verify the writes were made
        file_mock().write.assert_has_calls(self._write_calls(), any_order=True)

        return cert_id

    def _get_cert(self, cert_id):
        file_mock = mock.mock_open()
        # Attempt to retrieve the cert
        with mock.patch('builtins.open', file_mock, create=True):
            data = local_cert_manager.CertManager.get_cert(cert_id)

        # Verify the correct files were opened
        open_calls, unexpected_calls = self._open_calls(cert_id, 'r')
        file_mock.assert_has_calls(open_calls, any_order=True)
        for unexpected_call in unexpected_calls:
            self.assertNotIn(unexpected_call, file_mock.mock_calls)

        # The returned data should be a Cert object
        self.assertIsInstance(data, cert_manager.Cert)

        return data

    def _get_cert_with_fail(self, cert_id, failed='crt'):
        def fake_open(path, mode):
            if path == os.path.join('/tmp/{0}.{1}'.format(cert_id, failed)):
                raise IOError()
            return mock.DEFAULT

        file_mock = mock.mock_open()
        file_mock.side_effect = fake_open
        # Attempt to retrieve the cert
        with mock.patch('builtins.open', file_mock, create=True):
            self.assertRaises(
                exception.CertificateStorageException,
                local_cert_manager.CertManager.get_cert,
                cert_id
            )

    def _delete_cert(self, cert_id):
        remove_mock = mock.Mock()
        # Delete the cert
        with mock.patch('os.remove', remove_mock):
            local_cert_manager.CertManager.delete_cert(cert_id)

        open_calls, unexpected_calls = self._open_calls(cert_id, mode=None)
        # Verify the correct files were removed
        remove_mock.assert_has_calls(open_calls, any_order=True)
        for unexpected_call in unexpected_calls:
            self.assertNotIn(unexpected_call, remove_mock.mock_calls)

    def _delete_cert_with_fail(self, cert_id):
        remove_mock = mock.Mock()
        remove_mock.side_effect = IOError
        # Delete the cert
        with mock.patch('os.remove', remove_mock):
            self.assertRaises(
                exception.CertificateStorageException,
                local_cert_manager.CertManager.delete_cert,
                cert_id
            )

    def test_store_cert(self):
        self._store_cert()

    @mock.patch('builtins.open', create=True)
    def test_store_cert_with_io_error(self, file_mock):
        file_mock.side_effect = IOError

        self.assertRaises(
            exception.CertificateStorageException,
            local_cert_manager.CertManager.store_cert,
            certificate=self.certificate,
            intermediates=self.intermediates,
            private_key=self.private_key,
            private_key_passphrase=self.private_key_passphrase
        )

    def test_get_cert(self):
        # Store a cert
        cert_id = self._store_cert()

        # Get the cert
        self._get_cert(cert_id)

    def test_get_cert_with_loading_cert_fail(self):
        # Store a cert
        cert_id = self._store_cert()

        self._get_cert_with_fail(cert_id, failed='crt')

    def test_get_cert_with_loading_private_key_fail(self):
        # Store a cert
        cert_id = self._store_cert()

        self._get_cert_with_fail(cert_id, failed='key')

    def test_get_cert_with_loading_intermediates_fail(self):
        # Store a cert
        cert_id = self._store_cert()

        self._get_cert_with_fail(cert_id, failed='int')

    def test_get_cert_with_loading_pkp_fail(self):
        # Store a cert
        cert_id = self._store_cert()

        self._get_cert_with_fail(cert_id, failed='pass')

    def test_get_cert_without_intermediate(self):
        self.intermediates = None
        # Store a cert
        cert_id = self._store_cert()

        # Get the cert
        self._get_cert(cert_id)

    def test_get_cert_without_pkp(self):
        self.private_key_passphrase = None
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

    def test_delete_cert_with_fail(self):
        # Store a cert
        cert_id = self._store_cert()

        # Verify the cert exists
        self._get_cert(cert_id)

        # Delete the cert with fail
        self._delete_cert_with_fail(cert_id)

    def test_delete_cert_without_intermediate(self):
        self.intermediates = None
        # Store a cert
        cert_id = self._store_cert()

        # Delete the cert with fail
        self._delete_cert_with_fail(cert_id)

    def test_delete_cert_without_pkp(self):
        self.private_key_passphrase = None
        # Store a cert
        cert_id = self._store_cert()

        # Delete the cert with fail
        self._delete_cert_with_fail(cert_id)
