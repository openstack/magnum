# Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import mock
from webob import exc

from magnum.api.controllers import base
from magnum.tests import base as test_base


class TestVersion(test_base.TestCase):

    def setUp(self):
        super(TestVersion, self).setUp()
        self.a = base.Version(
            {base.Version.string: "magnum 2.0"}, "magnum 2.0", "magnum 2.1")
        self.b = base.Version(
            {base.Version.string: "magnum 2.0"}, "magnum 2.0", "magnum 2.1")

    def test__lt__with_higher_major_version(self):
        self.a.major = 2
        self.b.major = 1

        self.assertEqual(2 < 1, self.a < self.b)

    def test__lt__with_lower_major_version(self):
        self.a.major = 1
        self.b.major = 2

        self.assertEqual(1 < 2, self.a < self.b)

    def test__lt__with_higher_minor_version(self):
        self.a.minor = 2
        self.b.minor = 1

        self.assertEqual(self.a.major, self.b.major)
        self.assertEqual(2 < 1, self.a < self.b)

    def test__lt__with_lower_minor_version(self):
        self.a.minor = 1
        self.b.minor = 2

        self.assertEqual(self.a.major, self.b.major)
        self.assertEqual(1 < 2, self.a < self.b)

    def test__gt__with_higher_major_version(self):
        self.a.major = 2
        self.b.major = 1

        self.assertEqual(2 > 1, self.a > self.b)

    def test__gt__with_lower_major_version(self):
        self.a.major = 1
        self.b.major = 2

        self.assertEqual(1 > 2, self.a > self.b)

    def test__gt__with_higher_minor_version(self):
        self.a.minor = 2
        self.b.minor = 1

        self.assertEqual(self.a.major, self.b.major)
        self.assertEqual(2 > 1, self.a > self.b)

    def test__gt__with_lower_minor_version(self):
        self.a.minor = 1
        self.b.minor = 2

        self.assertEqual(self.a.major, self.b.major)
        self.assertEqual(1 > 2, self.a > self.b)

    @mock.patch('magnum.api.controllers.base.Version.parse_headers')
    def test_init(self, mock_parse):
        a = mock.Mock()
        b = mock.Mock()
        mock_parse.return_value = (a, b)
        v = base.Version('test', 'foo', 'bar')

        mock_parse.assert_called_with('test', 'foo', 'bar')
        self.assertEqual(a, v.major)
        self.assertEqual(b, v.minor)

    @mock.patch('magnum.api.controllers.base.Version.parse_headers')
    def test_repr(self, mock_parse):
        mock_parse.return_value = (123, 456)
        v = base.Version('test', mock.ANY, mock.ANY)
        result = "%s" % v
        self.assertEqual('123.456', result)

    @mock.patch('magnum.api.controllers.base.Version.parse_headers')
    def test_repr_with_strings(self, mock_parse):
        mock_parse.return_value = ('abc', 'def')
        v = base.Version('test', mock.ANY, mock.ANY)
        result = "%s" % v
        self.assertEqual('abc.def', result)

    def test_parse_headers_ok(self):
        version = base.Version.parse_headers(
            {base.Version.string: 'magnum 123.456'}, mock.ANY, mock.ANY)
        self.assertEqual((123, 456), version)

    def test_parse_headers_latest(self):
        for s in ['magnum latest', 'magnum LATEST']:
            version = base.Version.parse_headers(
                {base.Version.string: s}, mock.ANY, 'magnum 1.9')
            self.assertEqual((1, 9), version)

    def test_parse_headers_bad_length(self):
        self.assertRaises(
            exc.HTTPNotAcceptable,
            base.Version.parse_headers,
            {base.Version.string: 'magnum 1'},
            mock.ANY,
            mock.ANY)
        self.assertRaises(
            exc.HTTPNotAcceptable,
            base.Version.parse_headers,
            {base.Version.string: 'magnum 1.2.3'},
            mock.ANY,
            mock.ANY)

    def test_parse_no_header(self):
        # this asserts that the minimum version string is applied
        version = base.Version.parse_headers({}, 'magnum 1.1', 'magnum 1.5')
        self.assertEqual((1, 1), version)

    def test_parse_incorrect_service_type(self):
        self.assertRaises(
            exc.HTTPNotAcceptable,
            base.Version.parse_headers,
            {base.Version.string: '1.1'},
            'magnum 1.1',
            'magnum 1.1')
        self.assertRaises(
            exc.HTTPNotAcceptable,
            base.Version.parse_headers,
            {base.Version.string: 'nova 1.1'},
            'magnum 1.1',
            'magnum 1.1')
