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

from cryptography import x509

from magnum.common import exception
from magnum.common.x509 import extensions
import magnum.conf

try:
    # for cryptography >= 35.0.0
    from cryptography.hazmat._oid import _OID_NAMES as OID_NAMES
except ImportError:
    from cryptography.x509.oid import _OID_NAMES as OID_NAMES

_CA_KEY_USAGES = [
    extensions.KeyUsages.KEY_CERT_SIGN.value[0],
    extensions.KeyUsages.CRL_SIGN.value[0]
]

CONF = magnum.conf.CONF


def filter_extensions(extensions):
    filtered_extensions = []
    allowed_key_usage = set(CONF.x509.allowed_key_usage)
    if not CONF.x509.allow_ca:
        allowed_key_usage = _remove_ca_key_usage(allowed_key_usage)

    for ext in filter_allowed_extensions(extensions,
                                         CONF.x509.allowed_extensions):
        if ext.oid == x509.OID_KEY_USAGE:
            ext = _merge_key_usage(ext, allowed_key_usage)
        elif ext.oid == x509.OID_BASIC_CONSTRAINTS:
            if not CONF.x509.allow_ca:
                ext = _disallow_ca_in_basic_constraints(ext)

        filtered_extensions.append(ext)

    return filtered_extensions


def filter_allowed_extensions(extensions, allowed_extensions=None):
    """Ensure only accepted extensions are used."""
    allowed_extensions = allowed_extensions or []

    for ext in extensions:
        ext_name = OID_NAMES.get(ext.oid, None)
        if ext_name in allowed_extensions:
            yield ext
        else:
            if ext.critical:
                raise exception.CertificateValidationError(extension=ext)


def _merge_key_usage(key_usage, allowed_key_usage):
    critical = key_usage.critical
    key_usage_value = key_usage.value

    usages = []
    for usage in extensions.KeyUsages:
        k, v = usage.value
        try:
            value = getattr(key_usage_value, v)
        except ValueError:
            # ValueError is raised when encipher_only/decipher_only is
            # retrieved but key_agreement is False
            value = False
        if value:
            if k not in allowed_key_usage:
                if critical:
                    raise exception.CertificateValidationError(
                        extension=key_usage)
                else:
                    value = False
        usages.append(value)

    rtn = x509.KeyUsage(*usages)
    return x509.Extension(rtn.oid, critical, rtn)


def _remove_ca_key_usage(allowed_key_usage):
    for usage in _CA_KEY_USAGES:
        try:
            allowed_key_usage.remove(usage)
        except KeyError:
            pass
    return allowed_key_usage


def _disallow_ca_in_basic_constraints(basic_constraints):
    if basic_constraints.value.ca:
        if basic_constraints.critical:
            raise exception.CertificateValidationError(
                extension=basic_constraints)

        bc = x509.BasicConstraints(False, None)
        return x509.Extension(bc.oid, False, bc)

    return basic_constraints
