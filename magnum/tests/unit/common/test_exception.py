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

import inspect
import mock

from magnum.common import exception
from magnum.i18n import _
from magnum.tests import base


class TestMagnumException(exception.MagnumException):
    message = _("templated %(name)s")


class TestWrapException(base.BaseTestCase):
    def test_wrap_exception_good_return(self):
        def good_function(self, context):
            return 99

        wrapped = exception.wrap_exception()
        self.assertEqual(99, wrapped(good_function)(1, 2))

    def test_wrap_exception_with_notifier(self):
        test_exc = TestMagnumException(name="NAME")

        def bad_function(self, context, extra, blah="a", boo="b", zoo=None):
            raise test_exc

        expected_context = 'context'
        expected_event_type = 'bad_function'
        expected_payload = {
            'exception': test_exc, 'private': {'args': {
                'self': None, 'context': expected_context, 'extra': 1,
                'blah': 'a', 'boo': 'b', 'zoo': 3}}}

        notifier = mock.MagicMock()
        wrapped = exception.wrap_exception(notifier)

        self.assertRaises(
            TestMagnumException, wrapped(bad_function), None,
            expected_context, 1, zoo=3)

        notifier.error.assert_called_once_with(
            expected_context, expected_event_type, expected_payload)


class TestException(base.BaseTestCase):

    def raise_(self, ex):
        raise ex

    def test_message_is_templated(self):
        ex = TestMagnumException(name="NAME")
        self.assertEqual(ex.message, "templated NAME")

    def test_custom_message_is_templated(self):
        ex = TestMagnumException(_("custom templated %(name)s"), name="NAME")
        self.assertEqual(ex.message, "custom templated NAME")

    def test_all_exceptions(self):
        for name, obj in inspect.getmembers(exception):
            if inspect.isclass(obj) and issubclass(obj, Exception):
                self.assertRaises(obj, self.raise_, obj())
