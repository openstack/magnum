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

import enum


class Extensions(enum.Enum):
    __order__ = ('AUTHORITY_KEY_IDENTIFIER SUBJECT_KEY_IDENTIFIER '
                 'AUTHORITY_INFORMATION_ACCESS BASIC_CONSTRAINTS '
                 'CRL_DISTRIBUTION_POINTS CERTIFICATE_POLICIES '
                 'EXTENDED_KEY_USAGE OCSP_NO_CHECK INHIBIT_ANY_POLICY '
                 'KEY_USAGE NAME_CONSTRAINTS SUBJECT_ALTERNATIVE_NAME '
                 'ISSUER_ALTERNATIVE_NAME')

    AUTHORITY_KEY_IDENTIFIER = "authorityKeyIdentifier"
    SUBJECT_KEY_IDENTIFIER = "subjectKeyIdentifier"
    AUTHORITY_INFORMATION_ACCESS = "authorityInfoAccess"
    BASIC_CONSTRAINTS = "basicConstraints"
    CRL_DISTRIBUTION_POINTS = "cRLDistributionPoints"
    CERTIFICATE_POLICIES = "certificatePolicies"
    EXTENDED_KEY_USAGE = "extendedKeyUsage"
    OCSP_NO_CHECK = "OCSPNoCheck"
    INHIBIT_ANY_POLICY = "inhibitAnyPolicy"
    KEY_USAGE = "keyUsage"
    NAME_CONSTRAINTS = "nameConstraints"
    SUBJECT_ALTERNATIVE_NAME = "subjectAltName"
    ISSUER_ALTERNATIVE_NAME = "issuerAltName"


class KeyUsages(enum.Enum):
    __order__ = ('DIGITAL_SIGNATURE CONTENT_COMMITMENT KEY_ENCIPHERMENT '
                 'DATA_ENCIPHERMENT KEY_AGREEMENT KEY_CERT_SIGN '
                 'CRL_SIGN ENCIPHER_ONLY DECIPHER_ONLY')

    DIGITAL_SIGNATURE = ("Digital Signature", "digital_signature")
    CONTENT_COMMITMENT = ("Non Repudiation", "content_commitment")
    KEY_ENCIPHERMENT = ("Key Encipherment", "key_encipherment")
    DATA_ENCIPHERMENT = ("Data Encipherment", "data_encipherment")
    KEY_AGREEMENT = ("Key Agreement", "key_agreement")
    KEY_CERT_SIGN = ("Certificate Sign", "key_cert_sign")
    CRL_SIGN = ("CRL Sign", "crl_sign")
    ENCIPHER_ONLY = ("Encipher Only", "encipher_only")
    DECIPHER_ONLY = ("Decipher Only", "decipher_only")
