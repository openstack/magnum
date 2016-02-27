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

import datetime
import six
import uuid

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from cryptography.x509 import Extension
from oslo_config import cfg
from oslo_log import log as logging

from magnum.common import exception
from magnum.common.x509 import validator
from magnum.i18n import _LE

LOG = logging.getLogger(__name__)

cfg.CONF.import_group('x509', 'magnum.common.x509.config')


def generate_ca_certificate(subject_name, encryption_password=None):
    """Generate CA Certificate

    :param subject_name: subject name of CA
    :param encryption_password: encryption passsword for private key
    :returns: generated private key and certificate pair
    """
    return _generate_self_signed_certificate(
        subject_name,
        _build_ca_extentions(),
        encryption_password=encryption_password
    )


def generate_client_certificate(issuer_name, subject_name, ca_key,
                                encryption_password=None,
                                ca_key_password=None):
    """Generate Client Certificate

    :param issuer_name: issuer name
    :param subject_name: subject name of client
    :param ca_key: private key of CA
    :param encryption_password: encryption passsword for private key
    :param ca_key_password: private key password for given ca key
    :returns: generated private key and certificate pair
    """
    return _generate_certificate(issuer_name, subject_name,
                                 _build_client_extentions(), ca_key=ca_key,
                                 encryption_password=encryption_password,
                                 ca_key_password=ca_key_password)


def _build_client_extentions():
    # Digital Signature and Key Encipherment are enabled
    key_usage = x509.KeyUsage(True, False, True, False, False, False, False,
                              False, False)
    key_usage = Extension(key_usage.oid, True, key_usage)
    extended_key_usage = x509.ExtendedKeyUsage([x509.OID_CLIENT_AUTH])
    extended_key_usage = Extension(extended_key_usage.oid, False,
                                   extended_key_usage)
    basic_constraints = x509.BasicConstraints(ca=False, path_length=None)
    basic_constraints = Extension(basic_constraints.oid, True,
                                  basic_constraints)

    return [key_usage, extended_key_usage, basic_constraints]


def _build_ca_extentions():
    # Certificate Sign is enabled
    key_usage = x509.KeyUsage(False, False, False, False, False, True, False,
                              False, False)
    key_usage = Extension(key_usage.oid, True, key_usage)
    basic_constraints = x509.BasicConstraints(ca=True, path_length=0)
    basic_constraints = Extension(basic_constraints.oid, True,
                                  basic_constraints)

    return [basic_constraints, key_usage]


def _generate_self_signed_certificate(subject_name, extensions,
                                      encryption_password=None):
    return _generate_certificate(subject_name, subject_name, extensions,
                                 encryption_password=encryption_password)


def _generate_certificate(issuer_name, subject_name, extensions, ca_key=None,
                          encryption_password=None, ca_key_password=None):

    if not isinstance(subject_name, six.text_type):
        subject_name = six.text_type(subject_name.decode('utf-8'))

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=cfg.CONF.x509.rsa_key_size,
        backend=default_backend()
    )

    # subject name is set as common name
    csr = x509.CertificateSigningRequestBuilder()
    csr = csr.subject_name(x509.Name([
        x509.NameAttribute(x509.OID_COMMON_NAME, subject_name),
    ]))

    for extention in extensions:
        csr = csr.add_extension(extention.value, critical=extention.critical)

    # if ca_key is not provided, it means self signed
    if not ca_key:
        ca_key = private_key
        ca_key_password = encryption_password

    csr = csr.sign(private_key, hashes.SHA256(), default_backend())

    if encryption_password:
        encryption_algorithm = serialization.BestAvailableEncryption(
            encryption_password)
    else:
        encryption_algorithm = serialization.NoEncryption()

    private_key = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption_algorithm
    )

    keypairs = {
        'private_key': private_key,
        'certificate': sign(
            csr,
            issuer_name,
            ca_key,
            ca_key_password=ca_key_password,
            skip_validation=True),
    }
    return keypairs


def sign(csr, issuer_name, ca_key, ca_key_password=None,
         skip_validation=False):
    """Sign a given csr

    :param csr: certificate signing request object or pem encoded csr
    :param issuer_name: issuer name
    :param ca_key: private key of CA
    :param ca_key_password: private key password for given ca key
    :param skip_validation: skip csr validation if true
    :returns: generated certificate
    """

    if not isinstance(ca_key, rsa.RSAPrivateKey):
        ca_key = serialization.load_pem_private_key(ca_key,
                                                    password=ca_key_password,
                                                    backend=default_backend())

    if not isinstance(issuer_name, six.text_type):
        issuer_name = six.text_type(issuer_name.decode('utf-8'))

    if isinstance(csr, six.text_type):
        csr = six.b(str(csr))
    if not isinstance(csr, x509.CertificateSigningRequest):
        try:
            csr = x509.load_pem_x509_csr(csr, backend=default_backend())
        except ValueError:
            LOG.exception(_LE("Received invalid csr {0}.").format(csr))
            raise exception.InvalidCsr(csr=csr)

    term_of_validity = cfg.CONF.x509.term_of_validity
    one_day = datetime.timedelta(1, 0, 0)
    expire_after = datetime.timedelta(term_of_validity, 0, 0)

    builder = x509.CertificateBuilder()
    builder = builder.subject_name(csr.subject)
    # issuer_name is set as common name
    builder = builder.issuer_name(x509.Name([
        x509.NameAttribute(x509.OID_COMMON_NAME, issuer_name),
    ]))
    builder = builder.not_valid_before(datetime.datetime.today() - one_day)
    builder = builder.not_valid_after(datetime.datetime.today() + expire_after)
    builder = builder.serial_number(int(uuid.uuid4()))
    builder = builder.public_key(csr.public_key())

    if skip_validation:
        extensions = csr.extensions
    else:
        extensions = validator.filter_extensions(csr.extensions)

    for extention in extensions:
        builder = builder.add_extension(extention.value,
                                        critical=extention.critical)

    certificate = builder.sign(
        private_key=ca_key, algorithm=hashes.SHA256(),
        backend=default_backend()
    ).public_bytes(serialization.Encoding.PEM)

    return certificate


def decrypt_key(encrypted_key, password):
    private_key = serialization.load_pem_private_key(
        encrypted_key, password=password, backend=default_backend()
    )
    decrypted_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    return decrypted_pem
