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

from webtest.app import AppError

from magnum.tests.unit.common.policies import base


class TestStatsPolicy(base.PolicyFunctionalTest):
    def test_stat_reader(self):
        response = self.get_json('/stats', headers=self.reader_headers)
        expected = {u'clusters': 0, u'nodes': 0}
        self.assertEqual(expected, response)

    def test_stat_admin(self):
        response = self.get_json('/stats', headers=self.admin_headers)
        expected = {u'clusters': 0, u'nodes': 0}
        self.assertEqual(expected, response)

    def test_stat_no_permission(self):
        exc = self.assertRaises(
            AppError, self.get_json, '/stats',
            headers=self.member_headers)
        self.assertIn("403 Forbidden", str(exc))
