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

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography import x509 as c_x509
from cryptography.x509.oid import NameOID
from unittest import mock

import six

from magnum.common import exception
from magnum.common.x509 import operations
from magnum.tests import base


class TestX509(base.BaseTestCase):

    def setUp(self):
        super(TestX509, self).setUp()
        self.issuer_name = six.u("fake-issuer")
        self.subject_name = six.u("fake-subject")
        self.organization_name = six.u("fake-organization")
        self.ca_encryption_password = six.b("fake-ca-password")
        self.encryption_password = six.b("fake-password")

    def _load_pems(self, keypairs, encryption_password):
        private_key = serialization.load_pem_private_key(
            keypairs['private_key'],
            password=encryption_password
        )
        certificate = c_x509.load_pem_x509_certificate(
            keypairs['certificate'])

        return certificate, private_key

    def _generate_ca_certificate(self, issuer_name=None):
        issuer_name = issuer_name or self.issuer_name
        keypairs = operations.generate_ca_certificate(
            issuer_name, encryption_password=self.ca_encryption_password)

        return self._load_pems(keypairs, self.ca_encryption_password)

    def _generate_client_certificate(self, issuer_name, subject_name):
        ca = operations.generate_ca_certificate(
            self.issuer_name, encryption_password=self.ca_encryption_password)
        keypairs = operations.generate_client_certificate(
            self.issuer_name,
            self.subject_name,
            self.organization_name,
            ca['private_key'],
            encryption_password=self.encryption_password,
            ca_key_password=self.ca_encryption_password,
        )

        return self._load_pems(keypairs, self.encryption_password)

    def _public_bytes(self, public_key):
        return public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def _private_bytes(self, private_key):
        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

    def _generate_private_key(self):
        return rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

    def _build_csr(self, private_key):
        csr = c_x509.CertificateSigningRequestBuilder()
        csr = csr.subject_name(c_x509.Name([
            c_x509.NameAttribute(NameOID.COMMON_NAME, self.subject_name)
        ]))

        return csr.sign(private_key, hashes.SHA256())

    def assertHasPublicKey(self, keypairs):
        key = keypairs[1]
        cert = keypairs[0]

        self.assertEqual(self._public_bytes(key.public_key()),
                         self._public_bytes(cert.public_key()))

    def assertHasSubjectName(self, cert, subject_name):
        actual_subject_name = cert.subject.get_attributes_for_oid(
            c_x509.NameOID.COMMON_NAME)
        actual_subject_name = actual_subject_name[0].value

        self.assertEqual(subject_name, actual_subject_name)

    def assertHasIssuerName(self, cert, issuer_name):
        actual_issuer_name = cert.issuer.get_attributes_for_oid(
            c_x509.NameOID.COMMON_NAME)
        actual_issuer_name = actual_issuer_name[0].value

        self.assertEqual(issuer_name, actual_issuer_name)

    def assertInClientExtensions(self, cert):
        key_usage = c_x509.KeyUsage(True, False, True, False, False, False,
                                    False, False, False)
        key_usage = c_x509.Extension(key_usage.oid, True, key_usage)
        extended_key_usage = c_x509.ExtendedKeyUsage([c_x509.OID_CLIENT_AUTH])
        extended_key_usage = c_x509.Extension(extended_key_usage.oid, False,
                                              extended_key_usage)
        basic_constraints = c_x509.BasicConstraints(ca=False, path_length=None)
        basic_constraints = c_x509.Extension(basic_constraints.oid, True,
                                             basic_constraints)

        self.assertIn(key_usage, cert.extensions)
        self.assertIn(extended_key_usage, cert.extensions)
        self.assertIn(basic_constraints, cert.extensions)

    def test_generate_ca_certificate_with_bytes_issuer_name(self):
        issuer_name = six.b("bytes-issuer-name")
        cert, _ = self._generate_ca_certificate(issuer_name)

        issuer_name = issuer_name.decode('utf-8')
        self.assertHasSubjectName(cert, issuer_name)
        self.assertHasIssuerName(cert, issuer_name)

    def test_generate_ca_certificate_has_publickey(self):
        keypairs = self._generate_ca_certificate(self.issuer_name)

        self.assertHasPublicKey(keypairs)

    def test_generate_ca_certificate_set_subject_name(self):
        cert, _ = self._generate_ca_certificate(self.issuer_name)

        self.assertHasSubjectName(cert, self.issuer_name)

    def test_generate_ca_certificate_set_issuer_name(self):
        cert, _ = self._generate_ca_certificate(self.issuer_name)

        self.assertHasIssuerName(cert, self.issuer_name)

    def test_generate_ca_certificate_set_extentions_as_ca(self):
        cert, _ = self._generate_ca_certificate(self.issuer_name)

        key_usage = c_x509.KeyUsage(False, False, False, False, False, True,
                                    False, False, False)
        key_usage = c_x509.Extension(key_usage.oid, True, key_usage)
        basic_constraints = c_x509.BasicConstraints(ca=True, path_length=0)
        basic_constraints = c_x509.Extension(basic_constraints.oid, True,
                                             basic_constraints)

        self.assertIn(key_usage, cert.extensions)
        self.assertIn(basic_constraints, cert.extensions)

    def test_generate_client_certificate_has_publickey(self):
        keypairs = self._generate_client_certificate(
            self.issuer_name, self.subject_name)

        self.assertHasPublicKey(keypairs)

    def test_generate_client_certificate_set_subject_name(self):
        cert, _ = self._generate_client_certificate(
            self.issuer_name, self.subject_name)

        self.assertHasSubjectName(cert, self.subject_name)

    def test_generate_client_certificate_set_issuer_name(self):
        cert, key = self._generate_client_certificate(
            self.issuer_name, self.subject_name)

        self.assertHasIssuerName(cert, self.issuer_name)

    def test_generate_client_certificate_set_extentions_as_client(self):
        cert, key = self._generate_client_certificate(
            self.issuer_name, self.subject_name)

        self.assertInClientExtensions(cert)

    def test_load_pem_private_key_with_bytes_private_key(self):
        private_key = self._generate_private_key()
        private_key = self._private_bytes(private_key)

        self.assertIsInstance(private_key, six.binary_type)
        private_key = operations._load_pem_private_key(private_key)
        self.assertIsInstance(private_key, rsa.RSAPrivateKey)

    def test_load_pem_private_key_with_unicode_private_key(self):
        private_key = self._generate_private_key()
        private_key = self._private_bytes(private_key)
        private_key = six.text_type(private_key.decode('utf-8'))

        self.assertIsInstance(private_key, six.text_type)
        private_key = operations._load_pem_private_key(private_key)
        self.assertIsInstance(private_key, rsa.RSAPrivateKey)

    @mock.patch('cryptography.x509.load_pem_x509_csr')
    @mock.patch('six.b')
    def test_sign_with_unicode_csr(self, mock_six, mock_load_pem):
        ca_key = self._generate_private_key()
        private_key = self._generate_private_key()
        csr_obj = self._build_csr(private_key)
        csr = csr_obj.public_bytes(serialization.Encoding.PEM)
        csr = six.text_type(csr.decode('utf-8'))

        mock_load_pem.return_value = csr_obj
        operations.sign(csr, self.issuer_name, ca_key,
                        skip_validation=True)
        mock_six.assert_called_once_with(csr)

    @mock.patch('cryptography.x509.load_pem_x509_csr')
    def test_sign_empty_chars(self, mock_load_pem):
        ca_key = self._generate_private_key()
        private_key = self._generate_private_key()
        csr_obj = self._build_csr(private_key)
        csr = csr_obj.public_bytes(serialization.Encoding.PEM)
        csr = six.text_type(csr.decode('utf-8'))

        mock_load_pem.return_value = csr_obj
        certificate = operations.sign(csr, self.issuer_name,
                                      ca_key, skip_validation=True)

        # Certificate has to be striped for some parsers
        self.assertEqual(certificate,
                         certificate.strip())

    def test_sign_with_invalid_csr(self):
        ca_key = self._generate_private_key()
        csr = 'test'
        csr = six.u(csr)

        self.assertRaises(exception.InvalidCsr,
                          operations.sign,
                          csr, self.issuer_name, ca_key, skip_validation=True)
