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

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from oslo_log import log as logging

from magnum.common import exception
from magnum.common.x509 import validator
import magnum.conf

LOG = logging.getLogger(__name__)

CONF = magnum.conf.CONF


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


def generate_client_certificate(issuer_name, subject_name,
                                organization_name, ca_key,
                                encryption_password=None,
                                ca_key_password=None):
    """Generate Client Certificate

    :param issuer_name: issuer name
    :param subject_name: subject name of client
    :param organization_name: Organization name of client
    :param ca_key: private key of CA
    :param encryption_password: encryption passsword for private key
    :param ca_key_password: private key password for given ca key
    :returns: generated private key and certificate pair
    """
    return _generate_certificate(issuer_name, subject_name,
                                 _build_client_extentions(),
                                 organization_name, ca_key=ca_key,
                                 encryption_password=encryption_password,
                                 ca_key_password=ca_key_password)


def _build_client_extentions():
    # Digital Signature and Key Encipherment are enabled
    key_usage = x509.KeyUsage(True, False, True, False, False, False, False,
                              False, False)
    key_usage = x509.Extension(key_usage.oid, True, key_usage)
    extended_key_usage = x509.ExtendedKeyUsage([x509.OID_CLIENT_AUTH])
    extended_key_usage = x509.Extension(extended_key_usage.oid, False,
                                        extended_key_usage)
    basic_constraints = x509.BasicConstraints(ca=False, path_length=None)
    basic_constraints = x509.Extension(basic_constraints.oid, True,
                                       basic_constraints)

    return [key_usage, extended_key_usage, basic_constraints]


def _build_ca_extentions():
    # Certificate Sign is enabled
    key_usage = x509.KeyUsage(False, False, False, False, False, True, False,
                              False, False)
    key_usage = x509.Extension(key_usage.oid, True, key_usage)

    basic_constraints = x509.BasicConstraints(ca=True, path_length=0)
    basic_constraints = x509.Extension(basic_constraints.oid, True,
                                       basic_constraints)

    return [basic_constraints, key_usage]


def _generate_self_signed_certificate(subject_name, extensions,
                                      encryption_password=None):
    return _generate_certificate(subject_name, subject_name, extensions,
                                 encryption_password=encryption_password)


def _generate_certificate(issuer_name, subject_name, extensions,
                          organization_name=None, ca_key=None,
                          encryption_password=None, ca_key_password=None):

    if not isinstance(subject_name, six.text_type):
        subject_name = six.text_type(subject_name.decode('utf-8'))
    if organization_name and not isinstance(organization_name, six.text_type):
        organization_name = six.text_type(organization_name.decode('utf-8'))

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=CONF.x509.rsa_key_size
    )

    # subject name is set as common name
    csr = x509.CertificateSigningRequestBuilder()
    name_attributes = [x509.NameAttribute(x509.OID_COMMON_NAME, subject_name)]
    if organization_name:
        name_attributes.append(x509.NameAttribute(x509.OID_ORGANIZATION_NAME,
                                                  organization_name))
    csr = csr.subject_name(x509.Name(name_attributes))

    for extention in extensions:
        csr = csr.add_extension(extention.value, critical=extention.critical)

    # if ca_key is not provided, it means self signed
    if not ca_key:
        ca_key = private_key
        ca_key_password = encryption_password

    csr = csr.sign(private_key, hashes.SHA256())

    if six.PY3 and isinstance(encryption_password, six.text_type):
        encryption_password = encryption_password.encode()

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


def _load_pem_private_key(ca_key, ca_key_password=None):
    if not isinstance(ca_key, rsa.RSAPrivateKey):
        if isinstance(ca_key, six.text_type):
            ca_key = six.b(str(ca_key))
        if isinstance(ca_key_password, six.text_type):
            ca_key_password = six.b(str(ca_key_password))

        ca_key = serialization.load_pem_private_key(
            ca_key,
            password=ca_key_password
        )

    return ca_key


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

    ca_key = _load_pem_private_key(ca_key, ca_key_password)

    if not isinstance(issuer_name, six.text_type):
        issuer_name = six.text_type(issuer_name.decode('utf-8'))

    if isinstance(csr, six.text_type):
        csr = six.b(str(csr))
    if not isinstance(csr, x509.CertificateSigningRequest):
        try:
            csr = x509.load_pem_x509_csr(csr)
        except ValueError:
            LOG.exception("Received invalid csr %s.", csr)
            raise exception.InvalidCsr(csr=csr)

    term_of_validity = CONF.x509.term_of_validity
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
    ).public_bytes(serialization.Encoding.PEM).strip()

    return certificate


def generate_csr_and_key(common_name):
    """Return a dict with a new csr, public key and private key."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    public_key = private_key.public_key()

    csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
        x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, common_name),
    ])).sign(private_key, hashes.SHA256())

    result = {
        'csr': csr.public_bytes(
            encoding=serialization.Encoding.PEM).decode("utf-8"),
        'private_key': private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()).decode("utf-8"),
        'public_key': public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo).decode(
                "utf-8"),
    }

    return result


def decrypt_key(encrypted_key, password):
    private_key = _load_pem_private_key(encrypted_key, password)

    decrypted_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    return decrypted_pem
