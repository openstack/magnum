# Copyright 2014, 2015 Rackspace US, Inc.
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
import uuid

from openstack.key_manager.v1 import container as sdk_container
from unittest.mock import patch

from magnum.common.cert_manager import barbican_cert_manager as bcm
from magnum.common.cert_manager import cert_manager
from magnum.common import exception as magnum_exc
from magnum.tests import base


class TestBarbicanCert(base.BaseTestCase):

    def setUp(self):
        self.certificate = "My Certificate"
        self.intermediates = "My Intermediates"
        self.private_key = "My Private Key"
        self.private_key_passphrase = "My Private Key Passphrase"

        self.barbican_endpoint = 'http://localhost:9311/v1'
        self.certificate_ref = f'{self.barbican_endpoint}/secrets/cert-uuid'
        self.intermediates_ref = f'{self.barbican_endpoint}/secrets/int-uuid'
        self.private_key_ref = f'{self.barbican_endpoint}/secrets/pk-uuid'
        self.pkp_ref = f'{self.barbican_endpoint}/secrets/pkp-uuid'

        super(TestBarbicanCert, self).setUp()

    def _make_container(self, secret_refs=None):
        container = mock.Mock(spec=sdk_container.Container)
        container.type = 'certificate'
        container.secret_refs = secret_refs or []
        return container

    def _make_connection(self):
        payload_map = {
            'cert-uuid': self.certificate,
            'int-uuid': self.intermediates,
            'pk-uuid': self.private_key,
            'pkp-uuid': self.private_key_passphrase,
        }
        conn = mock.MagicMock()

        def get_secret(secret_uuid):
            s = mock.Mock()
            s.payload = payload_map[secret_uuid]
            return s

        conn.get_secret.side_effect = get_secret
        return conn

    def test_barbican_cert(self):
        container = self._make_container([
            {'name': 'certificate', 'secret_ref': self.certificate_ref},
            {'name': 'intermediates', 'secret_ref': self.intermediates_ref},
            {'name': 'private_key', 'secret_ref': self.private_key_ref},
            {'name': 'private_key_passphrase', 'secret_ref': self.pkp_ref},
        ])
        conn = self._make_connection()
        cert = bcm.Cert(cert_container=container, connection=conn)

        self.assertEqual(self.certificate, cert.get_certificate())
        self.assertEqual(self.intermediates, cert.get_intermediates())
        self.assertEqual(self.private_key, cert.get_private_key())
        self.assertEqual(self.private_key_passphrase,
                         cert.get_private_key_passphrase())

    def test_barbican_cert_none_values(self):
        container = self._make_container([])
        conn = mock.MagicMock()
        cert = bcm.Cert(cert_container=container, connection=conn)

        self.assertIsNone(cert.get_certificate())
        self.assertIsNone(cert.get_intermediates())
        self.assertIsNone(cert.get_private_key())
        self.assertIsNone(cert.get_private_key_passphrase())


class TestBarbicanManager(base.BaseTestCase):

    def setUp(self):
        self.barbican_endpoint = 'http://localhost:9311/v1'
        self.container_uuid = str(uuid.uuid4())
        self.container_ref = '{0}/containers/{1}'.format(
            self.barbican_endpoint, self.container_uuid
        )

        self.name = 'My Fancy Cert'
        self.certificate = b'My Certificate PEM'
        self.private_key = b'My Private Key PEM'
        self.intermediates = b'My Intermediates PEM'
        self.private_key_passphrase = b'My Private Key Passphrase'

        self.cert_secret_ref = f'{self.barbican_endpoint}/secrets/cert-uuid'
        self.pk_secret_ref = f'{self.barbican_endpoint}/secrets/pk-uuid'
        self.int_secret_ref = f'{self.barbican_endpoint}/secrets/int-uuid'
        self.pkp_secret_ref = f'{self.barbican_endpoint}/secrets/pkp-uuid'

        cert_secret = mock.MagicMock()
        cert_secret.secret_ref = self.cert_secret_ref
        pk_secret = mock.MagicMock()
        pk_secret.secret_ref = self.pk_secret_ref
        int_secret = mock.MagicMock()
        int_secret.secret_ref = self.int_secret_ref
        pkp_secret = mock.MagicMock()
        pkp_secret.secret_ref = self.pkp_secret_ref

        self.secrets_by_name = {
            'Certificate': cert_secret,
            'Private Key': pk_secret,
            'Intermediates': int_secret,
            'Private Key Passphrase': pkp_secret,
        }

        self.container = mock.MagicMock(spec=sdk_container.Container)
        self.container.container_ref = self.container_ref
        self.container.type = 'certificate'
        self.container.secret_refs = [
            {'name': 'certificate', 'secret_ref': self.cert_secret_ref},
            {'name': 'private_key', 'secret_ref': self.pk_secret_ref},
            {'name': 'intermediates', 'secret_ref': self.int_secret_ref},
            {'name': 'private_key_passphrase',
             'secret_ref': self.pkp_secret_ref},
        ]

        super(TestBarbicanManager, self).setUp()

    @patch('magnum.common.clients.OpenStackClients.barbican')
    def test_store_cert(self, mock_barbican):
        bc = mock.MagicMock()
        bc.create_container.return_value = self.container

        def create_secret_side_effect(**kwargs):
            return self.secrets_by_name[kwargs['name']]

        bc.create_secret.side_effect = create_secret_side_effect
        mock_barbican.return_value = bc

        bcm.CertManager.store_cert(
            certificate=self.certificate,
            private_key=self.private_key,
            intermediates=self.intermediates,
            private_key_passphrase=self.private_key_passphrase,
            name=self.name
        )

        calls = [
            mock.call(payload=self.certificate, expiration=None,
                      name=mock.ANY),
            mock.call(payload=self.private_key, expiration=None,
                      name=mock.ANY),
            mock.call(payload=self.intermediates, expiration=None,
                      name=mock.ANY),
            mock.call(payload=self.private_key_passphrase, expiration=None,
                      name=mock.ANY),
        ]
        bc.create_secret.assert_has_calls(calls, any_order=True)
        self.assertEqual(1, bc.create_container.call_count)

    @patch('magnum.common.clients.OpenStackClients.barbican')
    def test_store_cert_failure(self, mock_barbican):
        bc = mock.MagicMock()

        cert_secret = mock.MagicMock()
        cert_secret.secret_ref = self.cert_secret_ref
        pk_secret = mock.MagicMock()
        pk_secret.secret_ref = self.pk_secret_ref
        int_secret = mock.MagicMock()
        int_secret.secret_ref = self.int_secret_ref
        pkp_secret = mock.MagicMock()
        pkp_secret.secret_ref = self.pkp_secret_ref

        bc.create_secret.side_effect = [
            cert_secret, pk_secret, int_secret, pkp_secret
        ]
        bc.create_container.side_effect = (
            magnum_exc.CertificateStorageException)
        mock_barbican.return_value = bc

        self.assertRaises(
            magnum_exc.CertificateStorageException,
            bcm.CertManager.store_cert,
            certificate=self.certificate,
            private_key=self.private_key,
            intermediates=self.intermediates,
            private_key_passphrase=self.private_key_passphrase,
            name=self.name
        )

        self.assertEqual(1, bc.create_container.call_count)
        # All created secrets should have been deleted in rollback
        self.assertEqual(4, bc.delete_secret.call_count)

    @patch('magnum.common.clients.OpenStackClients.barbican')
    def test_get_cert(self, mock_barbican):
        bc = mock.MagicMock()
        bc.get_container.return_value = self.container
        mock_barbican.return_value = bc

        data = bcm.CertManager.get_cert(
            cert_ref=self.container_ref,
            resource_ref=self.container_ref,
            service_name='Magnum'
        )

        bc.get_container.assert_called_once_with(self.container_uuid)
        self.assertIsInstance(data, cert_manager.Cert)

    @patch('magnum.common.clients.OpenStackClients.barbican')
    def test_get_cert_no_registration(self, mock_barbican):
        bc = mock.MagicMock()
        bc.get_container.return_value = self.container
        mock_barbican.return_value = bc

        data = bcm.CertManager.get_cert(
            cert_ref=self.container_ref, check_only=True
        )

        bc.get_container.assert_called_once_with(self.container_uuid)
        self.assertIsInstance(data, cert_manager.Cert)

    @patch('magnum.common.clients.OpenStackClients.barbican')
    def test_delete_cert(self, mock_barbican):
        bc = mock.MagicMock()
        bc.get_container.return_value = self.container
        mock_barbican.return_value = bc

        bcm.CertManager.delete_cert(
            cert_ref=self.container_ref
        )

        bc.get_container.assert_called_once_with(self.container_uuid)
        bc.delete_secret.assert_any_call('cert-uuid')
        bc.delete_secret.assert_any_call('pk-uuid')
        bc.delete_secret.assert_any_call('int-uuid')
        bc.delete_secret.assert_any_call('pkp-uuid')
        bc.delete_container.assert_called_once_with(self.container_uuid)
