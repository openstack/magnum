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

from magnum.common import exception
from magnum.i18n import _
from magnum.tests import base


class TestMagnumException(exception.MagnumException):
    message = _("templated %(name)s")


class TestException(base.BaseTestCase):

    def raise_(self, ex):
        raise ex

    def test_message_is_templated(self):
        ex = TestMagnumException(name="NAME")
        self.assertEqual("templated NAME", str(ex))

    def test_custom_message_is_templated(self):
        ex = TestMagnumException(_("custom templated %(name)s"), name="NAME")
        self.assertEqual("custom templated NAME", str(ex))

    def test_all_exceptions(self):
        for name, obj in inspect.getmembers(exception):
            if inspect.isclass(obj) and issubclass(obj, Exception):
                self.assertRaises(obj, self.raise_, obj())
