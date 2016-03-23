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

import tempfile

from oslo_log import log as logging
import six

from magnum.common import cert_manager
from magnum.common import exception
from magnum.common import short_id
from magnum.common.x509 import operations as x509
from magnum.i18n import _LE
from magnum.i18n import _LW

CONDUCTOR_CLIENT_NAME = six.u('Magnum-Conductor')

LOG = logging.getLogger(__name__)


def _generate_ca_cert(issuer_name):
    """Generate and store ca_cert

    :param issuer_name: CA subject name
    :returns: CA cert uuid and CA cert, CA private key password
    """
    ca_password = short_id.generate_id()
    ca_cert = x509.generate_ca_certificate(issuer_name,
                                           encryption_password=ca_password)
    ca_cert_ref = cert_manager.get_backend().CertManager.store_cert(
        certificate=ca_cert['certificate'],
        private_key=ca_cert['private_key'],
        private_key_passphrase=ca_password,
        name=issuer_name,
    )
    LOG.debug('CA cert is created: %s', ca_cert_ref)
    return ca_cert_ref, ca_cert, ca_password


def _generate_client_cert(issuer_name, ca_cert, ca_password):
    """Generate and store magnum_client_cert

    :param issuer_name: CA subject name
    :param ca_cert: CA certificate
    :param ca_password: CA private key password
    :returns: Magnum client cert uuid
    """
    client_password = short_id.generate_id()
    client_cert = x509.generate_client_certificate(
        issuer_name,
        CONDUCTOR_CLIENT_NAME,
        ca_cert['private_key'],
        encryption_password=client_password,
        ca_key_password=ca_password,
    )
    magnum_cert_ref = cert_manager.get_backend().CertManager.store_cert(
        certificate=client_cert['certificate'],
        private_key=client_cert['private_key'],
        private_key_passphrase=client_password,
        name=CONDUCTOR_CLIENT_NAME,
    )
    LOG.debug('Magnum client cert is created: %s', magnum_cert_ref)
    return magnum_cert_ref


def _get_issuer_name(bay):
    issuer_name = bay.name
    # When user create a Bay without name, the bay.name is None.
    # We should use bay.uuid as issuer name.
    if issuer_name is None:
        issuer_name = bay.uuid
    return issuer_name


def generate_certificates_to_bay(bay):
    """Generate ca_cert and magnum client cert and set to bay

    :param bay: The bay to set CA cert and magnum client cert
    :returns: CA cert uuid and magnum client cert uuid
    """
    try:
        issuer_name = _get_issuer_name(bay)

        LOG.debug('Start to generate certificates: %s', issuer_name)

        ca_cert_ref, ca_cert, ca_password = _generate_ca_cert(issuer_name)
        magnum_cert_ref = _generate_client_cert(issuer_name,
                                                ca_cert,
                                                ca_password)

        bay.ca_cert_ref = ca_cert_ref
        bay.magnum_cert_ref = magnum_cert_ref
    except Exception:
        LOG.exception(_LE('Failed to generate certificates for Bay: %s'),
                      bay.uuid)
        raise exception.CertificatesToBayFailed(bay_uuid=bay.uuid)


def get_bay_ca_certificate(bay):
    ca_cert = cert_manager.get_backend().CertManager.get_cert(
        bay.ca_cert_ref,
        resource_ref=bay.uuid
    )

    return ca_cert


def get_bay_magnum_cert(bay):
    magnum_cert = cert_manager.get_backend().CertManager.get_cert(
        bay.magnum_cert_ref,
        resource_ref=bay.uuid
    )

    return magnum_cert


def create_client_files(bay):
    ca_cert = get_bay_ca_certificate(bay)
    magnum_cert = get_bay_magnum_cert(bay)

    ca_cert_file = tempfile.NamedTemporaryFile()
    ca_cert_file.write(ca_cert.get_certificate())
    ca_cert_file.flush()

    magnum_key_file = tempfile.NamedTemporaryFile()
    magnum_key_file.write(magnum_cert.get_decrypted_private_key())
    magnum_key_file.flush()

    magnum_cert_file = tempfile.NamedTemporaryFile()
    magnum_cert_file.write(magnum_cert.get_certificate())
    magnum_cert_file.flush()

    return ca_cert_file, magnum_key_file, magnum_cert_file


def sign_node_certificate(bay, csr):
    ca_cert = cert_manager.get_backend().CertManager.get_cert(
        bay.ca_cert_ref,
        resource_ref=bay.uuid
    )

    node_cert = x509.sign(csr,
                          _get_issuer_name(bay),
                          ca_cert.get_private_key(),
                          ca_cert.get_private_key_passphrase())
    return node_cert


def delete_certificates_from_bay(bay):
    """Delete ca cert and magnum client cert from bay

    :param bay: The bay which has certs
    """
    for cert_ref in ['ca_cert_ref', 'magnum_cert_ref']:
        try:
            cert_ref = getattr(bay, cert_ref, None)
            if cert_ref:
                cert_manager.get_backend().CertManager.delete_cert(
                    cert_ref, resource_ref=bay.uuid)
        except Exception:
            LOG.warning(_LW("Deleting certs is failed for Bay %s"), bay.uuid)
