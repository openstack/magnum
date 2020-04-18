# Copyright 2016 Intel, Inc
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
from unittest import mock

from magnum.common.cert_manager import x509keypair_cert_manager as x509_cm
from magnum.common import context
from magnum.tests import base
from magnum.tests.unit.db import base as db_base
from magnum.tests.unit.db import utils


class TestX509keypairCert(base.BaseTestCase):

    def setUp(self):
        self.certificate = "My Certificate"
        self.intermediates = "My Intermediates"
        self.private_key = "My Private Key"
        self.private_key_passphrase = "My Private Key Passphrase"

        super(TestX509keypairCert, self).setUp()

    def test_x509keypair_cert(self):
        # Create a cert
        cert = x509_cm.Cert(
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


class TestX509keypairManager(db_base.DbTestCase):

    def setUp(self):
        self.certificate = "My Certificate"
        self.intermediates = "My Intermediates"
        self.private_key = "My Private Key"
        self.private_key_passphrase = "My Private Key Passphrase"
        self.context = context.make_admin_context()
        super(TestX509keypairManager, self).setUp()

    def test_store_cert(self):
        x509keypair = utils.get_test_x509keypair()
        with mock.patch.object(self.dbapi, 'create_x509keypair',
                               autospec=True) as mock_create_x509keypair:
            mock_create_x509keypair.return_value = x509keypair

            uuid = x509_cm.CertManager.store_cert(context=self.context,
                                                  **x509keypair)
            self.assertEqual(uuid, '72625085-c507-4410-9b28-cd7cf1fbf1ad')

    def test_get_cert(self):
        x509keypair = utils.get_test_x509keypair(uuid='fake-uuid')
        with mock.patch.object(self.dbapi, 'get_x509keypair_by_uuid',
                               autospec=True) as mock_get_x509keypair:
            mock_get_x509keypair.return_value = x509keypair
            cert_obj = x509_cm.CertManager.get_cert('fake-uuid',
                                                    context=self.context)
            self.assertEqual(cert_obj.certificate, 'certificate')
            self.assertEqual(cert_obj.private_key, 'private_key')
            self.assertEqual(cert_obj.private_key_passphrase,
                             'private_key_passphrase')
            self.assertEqual(cert_obj.intermediates, 'intermediates')
            mock_get_x509keypair.assert_called_once_with(self.context,
                                                         'fake-uuid')

    def test_delete_cert(self):
        x509keypair = utils.get_test_x509keypair(uuid='fake-uuid')
        with mock.patch.object(self.dbapi, 'get_x509keypair_by_uuid',
                               autospec=True) as mock_get_x509keypair:
            mock_get_x509keypair.return_value = x509keypair
            with mock.patch.object(self.dbapi, 'destroy_x509keypair',
                                   autospec=True) as mock_destroy_x509keypair:
                x509_cm.CertManager.delete_cert('fake-uuid',
                                                context=self.context)
                mock_get_x509keypair.assert_called_once_with(self.context,
                                                             'fake-uuid')
                mock_destroy_x509keypair.assert_called_once_with('fake-uuid')
