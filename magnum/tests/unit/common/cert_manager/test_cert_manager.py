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

from unittest import mock

from oslo_config import fixture

from magnum.common import cert_manager
from magnum.common.cert_manager import barbican_cert_manager as bcm
from magnum.common.cert_manager import cert_manager as cert_manager_iface
from magnum.common.cert_manager import get_backend
from magnum.common.cert_manager import local_cert_manager as lcm
from magnum.tests import base


class FakeCert(cert_manager_iface.Cert):
    def get_certificate(self):
        return 'fake-cert'

    def get_intermediates(self):
        return 'fake-intermediates'

    def get_private_key(self):
        return 'fake-private-key'

    def get_private_key_passphrase(self):
        return 'fake-passphrase'


class TestCert(base.BaseTestCase):
    @mock.patch.object(cert_manager_iface, 'operations')
    def test_get_decrypted_private_key(self, mock_x509_ops):
        mock_x509_ops.decrypt_key.return_value = 'fake-key'
        fake_cert = FakeCert()
        decrypted_key = fake_cert.get_decrypted_private_key()
        self.assertEqual('fake-key', decrypted_key)
        mock_x509_ops.decrypt_key.assert_called_once_with('fake-private-key',
                                                          'fake-passphrase')


class TestCertManager(base.BaseTestCase):

    def setUp(self):
        cert_manager._CERT_MANAGER_PLUGIN = None
        super(TestCertManager, self).setUp()

    def test_barbican_cert_manager(self):
        fixture.Config().config(group='certificates',
                                cert_manager_type='barbican')
        self.assertEqual(get_backend().CertManager,
                         bcm.CertManager)

    def test_local_cert_manager(self):
        fixture.Config().config(group='certificates',
                                cert_manager_type='local')
        self.assertEqual(get_backend().CertManager,
                         lcm.CertManager)
