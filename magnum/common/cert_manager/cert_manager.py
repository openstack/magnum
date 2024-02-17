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

"""
Certificate manager API
"""
import abc

from magnum.common.x509 import operations


class Cert(object, metaclass=abc.ABCMeta):
    """Base class to represent all certificates."""

    @abc.abstractmethod
    def get_certificate(self):
        """Returns the certificate."""
        pass

    @abc.abstractmethod
    def get_intermediates(self):
        """Returns the intermediate certificates."""
        pass

    @abc.abstractmethod
    def get_private_key(self):
        """Returns the private key for the certificate."""
        pass

    def get_decrypted_private_key(self):
        """Returns the decrypted private key for the certificate."""
        return operations.decrypt_key(self.get_private_key(),
                                      self.get_private_key_passphrase())

    @abc.abstractmethod
    def get_private_key_passphrase(self):
        """Returns the passphrase for the private key."""
        pass


class CertManager(object, metaclass=abc.ABCMeta):
    """Base Cert Manager Interface

    A Cert Manager is responsible for managing certificates for TLS.
    """

    @abc.abstractmethod
    def store_cert(self, certificate, private_key, intermediates=None,
                   private_key_passphrase=None, expiration=None,
                   name='Magnum TLS Cert', **kwargs):
        """Stores (i.e., registers) a cert with the cert manager.

        This method stores the specified cert and returns its UUID that
        identifies it within the cert manager.
        If storage of the certificate data fails, a CertificateStorageException
        should be raised.
        """
        pass

    @abc.abstractmethod
    def get_cert(self, cert_uuid, check_only=False, **kwargs):
        """Retrieves the specified cert.

        If check_only is True, don't perform any sort of registration.
        If the specified cert does not exist, a CertificateStorageException
        should be raised.
        """
        pass

    @abc.abstractmethod
    def delete_cert(self, cert_uuid, **kwargs):
        """Deletes the specified cert.

        If the specified cert does not exist, a CertificateStorageException
        should be raised.
        """
        pass
