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

from barbicanclient import exceptions as barbican_exc
from barbicanclient.v1 import client as barbican_client
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
    def __init__(self, cert_container):
        if not isinstance(cert_container,
                          barbican_client.containers.CertificateContainer):
            raise TypeError(_(
                "Retrieved Barbican Container is not of the correct type "
                "(certificate)."))
        self._cert_container = cert_container

    # Container secrets are accessed upon query and can return as None,
    # don't return the payload if the secret is not available.

    def get_certificate(self):
        if self._cert_container.certificate:
            return self._cert_container.certificate.payload

    def get_intermediates(self):
        if self._cert_container.intermediates:
            return self._cert_container.intermediates.payload

    def get_private_key(self):
        if self._cert_container.private_key:
            return self._cert_container.private_key.payload

    def get_private_key_passphrase(self):
        if self._cert_container.private_key_passphrase:
            return self._cert_container.private_key_passphrase.payload


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

        certificate_secret = None
        private_key_secret = None
        intermediates_secret = None
        pkp_secret = None

        try:
            certificate_secret = connection.secrets.create(
                payload=certificate,
                expiration=expiration,
                name="Certificate"
            )
            private_key_secret = connection.secrets.create(
                payload=private_key,
                expiration=expiration,
                name="Private Key"
            )
            certificate_container = connection.containers.create_certificate(
                name=name,
                certificate=certificate_secret,
                private_key=private_key_secret
            )
            if intermediates:
                intermediates_secret = connection.secrets.create(
                    payload=intermediates,
                    expiration=expiration,
                    name="Intermediates"
                )
                certificate_container.intermediates = intermediates_secret
            if private_key_passphrase:
                pkp_secret = connection.secrets.create(
                    payload=private_key_passphrase,
                    expiration=expiration,
                    name="Private Key Passphrase"
                )
                certificate_container.private_key_passphrase = pkp_secret

            certificate_container.store()
            return certificate_container.container_ref
        #  Barbican (because of Keystone-middleware) sometimes masks
        #  exceptions strangely -- this will catch anything that it raises and
        #  reraise the original exception, while also providing useful
        #  feedback in the logs for debugging
        except magnum_exc.CertificateStorageException:
            for secret in [certificate_secret, private_key_secret,
                           intermediates_secret, pkp_secret]:
                if secret and secret.secret_ref:
                    old_ref = secret.secret_ref
                    try:
                        secret.delete()
                        LOG.info("Deleted secret %s (%s) during rollback.",
                                 secret.name, old_ref)
                    except Exception:
                        LOG.warning(
                            "Failed to delete %s (%s) during rollback. "
                            "This is probably not a problem.",
                            secret.name, old_ref)
            with excutils.save_and_reraise_exception():
                LOG.exception("Error storing certificate data")

    @staticmethod
    def get_cert(cert_ref, service_name='Magnum', resource_ref=None,
                 check_only=False, **kwargs):
        """Retrieves the specified cert and registers as a consumer.

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
            if check_only:
                cert_container = connection.containers.get(
                    container_ref=cert_ref
                )
            else:
                cert_container = connection.containers.register_consumer(
                    container_ref=cert_ref,
                    name=service_name,
                    url=resource_ref
                )
            return Cert(cert_container)
        except barbican_exc.HTTPClientError:
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
            certificate_container = connection.containers.get(cert_ref)
            certificate_container.certificate.delete()
            if certificate_container.intermediates:
                certificate_container.intermediates.delete()
            if certificate_container.private_key_passphrase:
                certificate_container.private_key_passphrase.delete()
            certificate_container.private_key.delete()
            certificate_container.delete()
        except barbican_exc.HTTPClientError:
            with excutils.save_and_reraise_exception():
                LOG.exception(
                    "Error recursively deleting certificate container %s",
                    cert_ref)
