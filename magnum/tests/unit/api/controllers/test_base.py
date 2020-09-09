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

from unittest import mock

from webob import exc

from magnum.api.controllers import base
from magnum.api.controllers import versions
from magnum.api import versioned_method
from magnum.tests import base as test_base


class TestVersion(test_base.TestCase):
    def setUp(self):
        super(TestVersion, self).setUp()
        self.a = versions.Version(
            {versions.Version.string: "container-infra 2.0"},
            "container-infra 2.0", "container-infra 2.1")
        self.b = versions.Version(
            {versions.Version.string: "container-infra 2.0"},
            "container-infra 2.0", "container-infra 2.1")
        self.c = versions.Version(
            {versions.Version.string: "container-infra 2.2"},
            "container-infra 2.0", "container-infra 2.2")

    def test_is_null_true(self):
        self.a.major = 0
        self.a.minor = 0
        self.assertEqual(0 == 0, self.a.is_null())

    def test_is_null_false(self):
        self.assertEqual(2 == 0, self.a.is_null())

    def test__eq__with_equal(self):
        self.assertEqual(2 == 2, self.a == self.b)

    def test__eq__with_unequal(self):
        self.a.major = 1
        self.assertEqual(1 == 2, self.a == self.b)

    def test__ne__with_equal(self):
        self.assertEqual(2 != 2, self.a != self.b)

    def test__ne__with_unequal(self):
        self.a.major = 1
        self.assertEqual(1 != 2, self.a != self.b)

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

    def test__le__with_equal(self):
        self.assertEqual(2 == 2, self.a <= self.b)

    def test__le__with_higher_version(self):
        self.a.major = 3
        self.assertEqual(3 <= 2, self.a <= self.b)

    def test__le__with_lower_version(self):
        self.a.major = 1
        self.assertEqual(1 <= 2, self.a <= self.b)

    def test__ge__with_equal(self):
        self.assertEqual(2 >= 2, self.a >= self.b)

    def test__ge__with_higher_version(self):
        self.a.major = 3
        self.assertEqual(3 >= 2, self.a >= self.b)

    def test__ge__with_lower_version(self):
        self.a.major = 1
        self.assertEqual(1 >= 2, self.a >= self.b)

    def test_matches_start_version(self):
        self.assertEqual(0 >= 0, self.a.matches(self.b, self.c))

    def test_matches_end_version(self):
        self.a.minor = 2
        self.assertEqual(2 <= 2, self.a.matches(self.b, self.c))

    def test_matches_valid_version(self):
        self.a.minor = 1
        self.assertEqual(0 <= 1 <= 2, self.a.matches(self.b, self.c))

    def test_matches_version_too_high(self):
        self.a.minor = 3
        self.assertEqual(0 <= 3 <= 2, self.a.matches(self.b, self.c))

    def test_matches_version_too_low(self):
        self.a.major = 1
        self.assertEqual(2 <= 1 <= 2, self.a.matches(self.b, self.c))

    def test_matches_null_version(self):
        self.a.major = 0
        self.a.minor = 0
        self.assertRaises(ValueError, self.a.matches, self.b, self.c)

    @mock.patch('magnum.api.controllers.versions.Version.parse_headers')
    def test_init(self, mock_parse):
        a = mock.Mock()
        b = mock.Mock()
        mock_parse.return_value = (a, b)
        v = versions.Version('test', 'foo', 'bar')

        mock_parse.assert_called_with('test', 'foo', 'bar')
        self.assertEqual(a, v.major)
        self.assertEqual(b, v.minor)

    @mock.patch('magnum.api.controllers.versions.Version.parse_headers')
    def test_repr(self, mock_parse):
        mock_parse.return_value = (123, 456)
        v = versions.Version('test', mock.ANY, mock.ANY)
        result = "%s" % v
        self.assertEqual('123.456', result)

    @mock.patch('magnum.api.controllers.versions.Version.parse_headers')
    def test_repr_with_strings(self, mock_parse):
        mock_parse.return_value = ('abc', 'def')
        v = versions.Version('test', mock.ANY, mock.ANY)
        result = "%s" % v
        self.assertEqual('abc.def', result)

    def test_parse_headers_ok(self):
        version = versions.Version.parse_headers(
            {versions.Version.string: 'container-infra 123.456'},
            mock.ANY, mock.ANY)
        self.assertEqual((123, 456), version)

    def test_parse_headers_latest(self):
        for s in ['magnum latest', 'magnum LATEST']:
            version = versions.Version.parse_headers(
                {versions.Version.string: s}, mock.ANY, 'container-infra 1.9')
            self.assertEqual((1, 9), version)

    def test_parse_headers_bad_length(self):
        self.assertRaises(
            exc.HTTPNotAcceptable,
            versions.Version.parse_headers,
            {versions.Version.string: 'container-infra 1'},
            mock.ANY,
            mock.ANY)
        self.assertRaises(
            exc.HTTPNotAcceptable,
            versions.Version.parse_headers,
            {versions.Version.string: 'container-infra 1.2.3'},
            mock.ANY,
            mock.ANY)

    def test_parse_no_header(self):
        # this asserts that the minimum version string is applied
        version = versions.Version.parse_headers({}, 'container-infra 1.1',
                                                 'container-infra 1.5')
        self.assertEqual((1, 1), version)

    def test_parse_incorrect_service_type(self):
        self.assertRaises(
            exc.HTTPNotAcceptable,
            versions.Version.parse_headers,
            {versions.Version.string: '1.1'},
            'container-infra 1.1',
            'container-infra 1.1')
        self.assertRaises(
            exc.HTTPNotAcceptable,
            versions.Version.parse_headers,
            {versions.Version.string: 'nova 1.1'},
            'container-infra 1.1',
            'container-infra 1.1')


class TestController(test_base.TestCase):
    def test_check_for_versions_intersection_negative(self):
        func_list = \
            [versioned_method.VersionedMethod('foo',
                                              versions.Version('', '', '',
                                                               '2.1'),
                                              versions.Version('', '', '',
                                                               '2.4'),
                                              None),
             versioned_method.VersionedMethod('foo',
                                              versions.Version('', '', '',
                                                               '2.11'),
                                              versions.Version('', '', '',
                                                               '3.1'),
                                              None),
             versioned_method.VersionedMethod('foo',
                                              versions.Version('', '', '',
                                                               '2.8'),
                                              versions.Version('', '', '',
                                                               '2.9'),
                                              None),
             ]

        result = base.Controller.check_for_versions_intersection(
            func_list=func_list)
        self.assertFalse(result)

        func_list = \
            [versioned_method.VersionedMethod('foo',
                                              versions.Version('', '', '',
                                                               '2.12'),
                                              versions.Version('', '', '',
                                                               '2.14'),
                                              None),
             versioned_method.VersionedMethod('foo',
                                              versions.Version('', '', '',
                                                               '3.0'),
                                              versions.Version('', '', '',
                                                               '3.4'),
                                              None)
             ]

        result = base.Controller.check_for_versions_intersection(
            func_list=func_list)
        self.assertFalse(result)

    def test_check_for_versions_intersection_positive(self):
        func_list = \
            [versioned_method.VersionedMethod('foo',
                                              versions.Version('', '', '',
                                                               '2.1'),
                                              versions.Version('', '', '',
                                                               '2.4'),
                                              None),
             versioned_method.VersionedMethod('foo',
                                              versions.Version('', '', '',
                                                               '2.3'),
                                              versions.Version('', '', '',
                                                               '3.1'),
                                              None),
             versioned_method.VersionedMethod('foo',
                                              versions.Version('', '', '',
                                                               '2.9'),
                                              versions.Version('', '', '',
                                                               '3.4'),
                                              None)
             ]

        result = base.Controller.check_for_versions_intersection(
            func_list=func_list)
        self.assertTrue(result)

    def test_check_for_versions_intersection_shared_start_end(self):
        func_list = \
            [versioned_method.VersionedMethod('foo',
                                              versions.Version('', '', '',
                                                               '1.1'),
                                              versions.Version('', '', '',
                                                               '1.1'),
                                              None),
             versioned_method.VersionedMethod('foo',
                                              versions.Version('', '', '',
                                                               '1.1'),
                                              versions.Version('', '', '',
                                                               '1.2'),
                                              None)
             ]

        result = base.Controller.check_for_versions_intersection(
            func_list=func_list)
        self.assertTrue(result)

    def test_api_version_decorator(self):

        class MyController(base.Controller):
            @base.Controller.api_version('1.0', '1.1')
            def testapi1(self):
                return 'API1_1.0_1.1'

            @base.Controller.api_version('1.2', '1.3')  # noqa
            def testapi1(self):   # noqa
                return 'API1_1.2_1.3'

            @base.Controller.api_version('2.1', '2.2')
            def testapi2(self):
                return 'API2_2.1_2.2'

            @base.Controller.api_version('1.0', '2.0')  # noqa
            def testapi2(self):  # noqa
                return 'API2_1.0_2.0'

        controller = MyController()
        # verify list was added to controller
        self.assertIsNotNone(controller.versioned_methods)

        api1_list = controller.versioned_methods['testapi1']
        api2_list = controller.versioned_methods['testapi2']

        # verify versioned_methods reordered correctly
        self.assertEqual('1.2', str(api1_list[0].start_version))
        self.assertEqual('1.3', str(api1_list[0].end_version))
        self.assertEqual('1.0', str(api1_list[1].start_version))
        self.assertEqual('1.1', str(api1_list[1].end_version))

        # verify stored methods can be called
        result = api1_list[0].func(controller)
        self.assertEqual('API1_1.2_1.3', result)
        result = api1_list[1].func(controller)
        self.assertEqual('API1_1.0_1.1', result)

        # verify versioned_methods reordered correctly
        self.assertEqual('2.1', str(api2_list[0].start_version))
        self.assertEqual('2.2', str(api2_list[0].end_version))
        self.assertEqual('1.0', str(api2_list[1].start_version))
        self.assertEqual('2.0', str(api2_list[1].end_version))

        # Verify stored methods can be called
        result = api2_list[0].func(controller)
        self.assertEqual('API2_2.1_2.2', result)
        result = api2_list[1].func(controller)
        self.assertEqual('API2_1.0_2.0', result)

    @mock.patch('pecan.request')
    def test_controller_get_attribute(self, mock_pecan_request):

        class MyController(base.Controller):
            @base.Controller.api_version('1.0', '1.1')
            def testapi1(self):
                return 'API1_1.0_1.1'

            @base.Controller.api_version('1.2', '1.3')  # noqa
            def testapi1(self):  # noqa
                return 'API1_1.2_1.3'

        controller = MyController()
        mock_pecan_request.version = versions.Version("", "",
                                                      "", "1.2")
        controller.request = mock_pecan_request

        method = controller.__getattribute__('testapi1')
        result = method()
        self.assertEqual('API1_1.2_1.3', result)

    @mock.patch('pecan.request')
    def test_controller_get_attr_version_not_found(self,
                                                   mock_pecan_request):

        class MyController(base.Controller):
            @base.Controller.api_version('1.0', '1.1')
            def testapi1(self):
                return 'API1_1.0_1.1'

            @base.Controller.api_version('1.3', '1.4')  # noqa
            def testapi1(self):  # noqa
                return 'API1_1.3_1.4'

        controller = MyController()
        mock_pecan_request.version = versions.Version("", "",
                                                      "", "1.2")
        controller.request = mock_pecan_request

        self.assertRaises(exc.HTTPNotAcceptable,
                          controller.__getattribute__, 'testapi1')
