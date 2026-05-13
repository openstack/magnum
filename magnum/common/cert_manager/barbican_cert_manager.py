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

import openstack.exceptions
from openstack.key_manager.v1 import container as _container
from oslo_log import log as logging
from oslo_utils import excutils

from magnum.common.cert_manager import cert_manager
from magnum.common import clients
from magnum.common import context
from magnum.common import exception as magnum_exc
from magnum.i18n import _

LOG = logging.getLogger(__name__)


class Cert(cert_manager.Cert):
    """Representation of a Cert based on the Barbican CertificateContainer."""
    def __init__(self, cert_container, connection=None):
        if not isinstance(cert_container, _container.Container):
            raise TypeError(_(
                "Retrieved Barbican Container is not of the correct type "
                "(certificate)."))
        if cert_container.type != 'certificate':
            raise TypeError(_(
                "Retrieved Barbican Container is not of the correct type "
                "(certificate)."))
        self._cert_container = cert_container
        self._connection = connection
        self._secret_cache = {}

    def _get_payload(self, name):
        if name in self._secret_cache:
            return self._secret_cache[name]
        for sr in (self._cert_container.secret_refs or []):
            if sr.get('name') == name:
                secret_uuid = sr['secret_ref'].split('/')[-1]
                secret = self._connection.get_secret(secret_uuid)
                payload = secret.payload
                self._secret_cache[name] = payload
                return payload
        return None

    def get_certificate(self):
        return self._get_payload('certificate')

    def get_intermediates(self):
        return self._get_payload('intermediates')

    def get_private_key(self):
        return self._get_payload('private_key')

    def get_private_key_passphrase(self):
        return self._get_payload('private_key_passphrase')


_ADMIN_OSC = None


def get_admin_clients():
    global _ADMIN_OSC
    if not _ADMIN_OSC:
        _ADMIN_OSC = clients.OpenStackClients(
            context.RequestContext(is_admin=True))
    return _ADMIN_OSC


class CertManager(cert_manager.CertManager):
    """Certificate Manager that wraps the Barbican client API."""
    @staticmethod
    def store_cert(certificate, private_key, intermediates=None,
                   private_key_passphrase=None, expiration=None,
                   name='Magnum TLS Cert', **kwargs):
        """Stores a certificate in the certificate manager.

        :param certificate: PEM encoded TLS certificate
        :param private_key: private key for the supplied certificate
        :param intermediates: ordered and concatenated intermediate certs
        :param private_key_passphrase: optional passphrase for the supplied key
        :param expiration: the expiration time of the cert in ISO 8601 format
        :param name: a friendly name for the cert

        :returns: the container_ref of the stored cert
        :raises Exception: if certificate storage fails
        """
        connection = get_admin_clients().barbican()

        LOG.info("Storing certificate container '%s' in Barbican.", name)

        created_secrets = []
        try:
            certificate_secret = connection.create_secret(
                payload=certificate,
                expiration=expiration,
                name="Certificate"
            )
            created_secrets.append(certificate_secret)
            private_key_secret = connection.create_secret(
                payload=private_key,
                expiration=expiration,
                name="Private Key"
            )
            created_secrets.append(private_key_secret)

            secret_refs = [
                {"name": "certificate",
                 "secret_ref": certificate_secret.secret_ref},
                {"name": "private_key",
                 "secret_ref": private_key_secret.secret_ref},
            ]

            if intermediates:
                intermediates_secret = connection.create_secret(
                    payload=intermediates,
                    expiration=expiration,
                    name="Intermediates"
                )
                created_secrets.append(intermediates_secret)
                secret_refs.append(
                    {"name": "intermediates",
                     "secret_ref": intermediates_secret.secret_ref})

            if private_key_passphrase:
                pkp_secret = connection.create_secret(
                    payload=private_key_passphrase,
                    expiration=expiration,
                    name="Private Key Passphrase"
                )
                created_secrets.append(pkp_secret)
                secret_refs.append(
                    {"name": "private_key_passphrase",
                     "secret_ref": pkp_secret.secret_ref})

            certificate_container = connection.create_container(
                name=name,
                type="certificate",
                secret_refs=secret_refs,
            )
            return certificate_container.container_ref
        except magnum_exc.CertificateStorageException:
            for secret in created_secrets:
                old_ref = secret.secret_ref
                try:
                    connection.delete_secret(old_ref.split('/')[-1])
                    LOG.info("Deleted secret %s during rollback.", old_ref)
                except Exception:
                    LOG.warning(
                        "Failed to delete %s during rollback. "
                        "This is probably not a problem.",
                        old_ref)
            with excutils.save_and_reraise_exception():
                LOG.exception("Error storing certificate data")

    @staticmethod
    def get_cert(cert_ref, service_name='Magnum', resource_ref=None,
                 check_only=False, **kwargs):
        """Retrieves the specified cert.

        :param cert_ref: the UUID of the cert to retrieve
        :param service_name: Friendly name for the consuming service
        :param resource_ref: Full HATEOAS reference to the consuming resource
        :param check_only: Read Certificate data without registering

        :return: Magnum.certificates.common.Cert representation of the
                 certificate data
        :raises Exception: if certificate retrieval fails
        """
        connection = get_admin_clients().barbican()

        LOG.info("Loading certificate container %s from Barbican.", cert_ref)
        try:
            container_uuid = cert_ref.split('/')[-1]
            cert_container = connection.get_container(container_uuid)
            return Cert(cert_container, connection)
        except openstack.exceptions.HttpException:
            with excutils.save_and_reraise_exception():
                LOG.exception("Error getting %s", cert_ref)

    @staticmethod
    def delete_cert(cert_ref, service_name='Magnum', resource_ref=None,
                    **kwargs):
        """Deletes the specified cert.

        :param cert_ref: the UUID of the cert to delete
        :raises Exception: if certificate deletion fails
        """
        connection = get_admin_clients().barbican()

        LOG.info(
            "Recursively deleting certificate container %s from Barbican.",
            cert_ref)
        try:
            container_uuid = cert_ref.split('/')[-1]
            certificate_container = connection.get_container(container_uuid)
            secret_refs_by_name = {
                sr['name']: sr['secret_ref']
                for sr in (certificate_container.secret_refs or [])
            }
            connection.delete_secret(
                secret_refs_by_name['certificate'].split('/')[-1])
            if 'intermediates' in secret_refs_by_name:
                connection.delete_secret(
                    secret_refs_by_name['intermediates'].split('/')[-1])
            if 'private_key_passphrase' in secret_refs_by_name:
                pkp_ref = secret_refs_by_name['private_key_passphrase']
                connection.delete_secret(pkp_ref.split('/')[-1])
            connection.delete_secret(
                secret_refs_by_name['private_key'].split('/')[-1])
            connection.delete_container(container_uuid)
        except openstack.exceptions.HttpException:
            with excutils.save_and_reraise_exception():
                LOG.exception(
                    "Error recursively deleting certificate container %s",
                    cert_ref)
