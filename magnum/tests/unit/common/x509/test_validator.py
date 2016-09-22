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

import unittest

from cryptography import x509 as c_x509

from magnum.common.exception import CertificateValidationError
from magnum.common.x509 import validator as v


class TestValidators(unittest.TestCase):
    def _build_key_usage(self, critical=False):
        # Digital Signature and Key Encipherment are enabled
        key_usage = c_x509.KeyUsage(
            True, False, True, False, False, False, False, False, False)
        return c_x509.Extension(key_usage.oid, critical, key_usage)

    def _build_basic_constraints(self, ca=False, critical=False):
        bc = c_x509.BasicConstraints(ca, None)
        return c_x509.Extension(bc.oid, critical, bc)

    def test_filter_allowed_extensions(self):
        key_usage = self._build_key_usage(critical=True)

        actual = [e for e in v.filter_allowed_extensions([key_usage],
                                                         ['keyUsage'])]
        self.assertEqual([key_usage], actual)

    def test_filter_allowed_extensions_disallowed_but_not_critical(self):
        key_usage = self._build_key_usage()

        actual = [e for e in v.filter_allowed_extensions([key_usage],
                                                         ['subjectAltName'])]

        self.assertEqual([], actual)

    def test_filter_allowed_extensions_disallowed(self):
        key_usage = self._build_key_usage(critical=True)

        with self.assertRaises(CertificateValidationError):
            next(v.filter_allowed_extensions([key_usage], ['subjectAltName']))

    def test_merge_key_usage(self):
        key_usage = self._build_key_usage(critical=True)

        self.assertEqual(key_usage,
                         v._merge_key_usage(key_usage,
                                            ['Digital Signature',
                                             'Key Encipherment']))

    def test_merge_key_usage_disallowed_but_not_critical(self):
        key_usage = self._build_key_usage()
        expected = c_x509.KeyUsage(
            True, False, False, False, False, False, False, False, False)
        expected = c_x509.Extension(expected.oid, False, expected)

        self.assertEqual(expected,
                         v._merge_key_usage(key_usage,
                                            ['Digital Signature']))

    def test_merge_key_usage_disallowed(self):
        key_usage = self._build_key_usage(critical=True)

        with self.assertRaises(CertificateValidationError):
            v._merge_key_usage(key_usage, ['Digital Signature'])

    def test_disallow_ca_in_basic_constraints_not_critical(self):
        bc = self._build_basic_constraints(ca=True)
        expected = self._build_basic_constraints(ca=False)

        self.assertEqual(expected, v._disallow_ca_in_basic_constraints(bc))

    def test_disallow_ca_in_basic_constraints(self):
        bc = self._build_basic_constraints(ca=True, critical=True)

        with self.assertRaises(CertificateValidationError):
            v._disallow_ca_in_basic_constraints(bc)

    def test_disallow_ca_in_basic_constraints_with_non_ca(self):
        bc = self._build_basic_constraints(ca=False)

        self.assertEqual(bc, v._disallow_ca_in_basic_constraints(bc))

    def test_remove_ca_key_usage(self):
        contains_ca_key_usage = set([
            "Digital Signature", "Certificate Sign", "CRL Sign"])

        self.assertEqual(set(["Digital Signature"]),
                         v._remove_ca_key_usage(contains_ca_key_usage))

    def test_remove_ca_key_usage_cert_sign(self):
        contains_ca_key_usage = set(["Digital Signature", "Certificate Sign"])

        self.assertEqual(set(["Digital Signature"]),
                         v._remove_ca_key_usage(contains_ca_key_usage))

    def test_remove_ca_key_usage_crl_sign(self):
        contains_ca_key_usage = set(["Digital Signature", "CRL Sign"])

        self.assertEqual(set(["Digital Signature"]),
                         v._remove_ca_key_usage(contains_ca_key_usage))

    def test_remove_ca_key_usage_without_ca_usage(self):
        contains_ca_key_usage = set(["Digital Signature"])

        self.assertEqual(set(["Digital Signature"]),
                         v._remove_ca_key_usage(contains_ca_key_usage))
