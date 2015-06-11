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

from magnum.api.controllers import base
from magnum.tests import base as test_base


class TestVersion(test_base.TestCase):

    def setUp(self):
        super(TestVersion, self).setUp()
        self.a = base.Version({base.Version.string: "2.0"}, "2.0", "2.1")
        self.b = base.Version({base.Version.string: "2.0"}, "2.0", "2.1")

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
