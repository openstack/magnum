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

from webtest.app import AppError

from magnum.tests.unit.api import base as api_base
from magnum.tests.unit.objects import utils as obj_utils


class TestStatsController(api_base.FunctionalTest):

    def setUp(self):
        self.base_headers = {
            "X-Roles": "reader",
            "OpenStack-API-Version": "container-infra 1.4"
        }
        self.base_admin_headers = {
            "X-Roles": "admin",
            "OpenStack-API-Version": "container-infra 1.4"
        }
        super(TestStatsController, self).setUp()
        obj_utils.create_test_cluster_template(self.context)

    def test_empty(self):
        response = self.get_json('/stats', headers=self.base_headers)
        expected = {u'clusters': 0, u'nodes': 0}
        self.assertEqual(expected, response)

    @mock.patch("magnum.common.policy.enforce")
    @mock.patch("magnum.common.context.make_context")
    def test_admin_get_all_stats(self, mock_context, mock_policy):
        obj_utils.create_test_cluster(self.context,
                                      project_id=123,
                                      uuid='uuid1')
        obj_utils.create_test_cluster(self.context,
                                      project_id=234,
                                      uuid='uuid2')
        response = self.get_json('/stats', headers=self.base_admin_headers)
        expected = {u'clusters': 2, u'nodes': 12}
        self.assertEqual(expected, response)

    @mock.patch("magnum.common.policy.enforce")
    @mock.patch("magnum.common.context.make_context")
    def test_admin_get_tenant_stats(self, mock_context, mock_policy):
        obj_utils.create_test_cluster(self.context,
                                      project_id=123,
                                      uuid='uuid1')
        obj_utils.create_test_cluster(self.context,
                                      project_id=234,
                                      uuid='uuid2')
        self.context.is_admin = True
        response = self.get_json('/stats?project_id=234',
                                 headers=self.base_admin_headers)
        expected = {u'clusters': 1, u'nodes': 6}
        self.assertEqual(expected, response)

    @mock.patch("magnum.common.policy.enforce")
    @mock.patch("magnum.common.context.make_context")
    def test_admin_get_invalid_tenant_stats(self, mock_context, mock_policy):
        obj_utils.create_test_cluster(self.context,
                                      project_id=123,
                                      uuid='uuid1')
        obj_utils.create_test_cluster(self.context,
                                      project_id=234,
                                      uuid='uuid2')
        self.context.is_admin = True
        response = self.get_json('/stats?project_id=34',
                                 headers=self.base_admin_headers)
        expected = {u'clusters': 0, u'nodes': 0}
        self.assertEqual(expected, response)

    def test_get_self_stats(self):
        obj_utils.create_test_cluster(self.context,
                                      project_id=123,
                                      uuid='uuid1')
        obj_utils.create_test_cluster(self.context,
                                      project_id=234,
                                      uuid='uuid2',
                                      node_count=5,
                                      master_count=1)
        headers = self.base_headers.copy()
        headers['X-Project-Id'] = '234'
        response = self.get_json('/stats',
                                 headers=headers)
        expected = {u'clusters': 1, u'nodes': 6}
        self.assertEqual(expected, response)

    def test_get_self_stats_without_param(self):
        obj_utils.create_test_cluster(self.context,
                                      project_id=123,
                                      uuid='uuid1')
        obj_utils.create_test_cluster(self.context,
                                      project_id=234,
                                      uuid='uuid2',
                                      node_count=5,
                                      master_count=1)
        headers = self.base_headers.copy()
        headers['X-Project-Id'] = '234'
        response = self.get_json('/stats',
                                 headers=headers)
        expected = {u'clusters': 1, u'nodes': 6}
        self.assertEqual(expected, response)

    def test_get_some_other_user_stats(self):
        obj_utils.create_test_cluster(self.context,
                                      project_id=123,
                                      uuid='uuid1')
        obj_utils.create_test_cluster(self.context,
                                      project_id=234,
                                      uuid='uuid2',
                                      node_count=5)
        headers = self.base_headers.copy()
        headers['X-Project-Id'] = '234'
        self.assertRaises(AppError,
                          self.get_json,
                          '/stats?project_id=123',
                          headers=headers)

    def test_get_invalid_type_stats(self):
        obj_utils.create_test_cluster(self.context,
                                      project_id=123,
                                      uuid='uuid1')
        self.assertRaises(AppError,
                          self.get_json,
                          '/stats?project_id=123&type=invalid',
                          headers=self.base_headers)
