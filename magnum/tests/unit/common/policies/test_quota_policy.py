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

from unittest import mock
from webtest.app import AppError

from magnum.common import clients
from magnum.tests.unit.api import utils as apiutils
from magnum.tests.unit.common.policies import base
from magnum.tests.unit.objects import utils as obj_utils


class TestQuotaPolicy(base.PolicyFunctionalTest):
    def setUp(self):
        super(TestQuotaPolicy, self).setUp()

    def test_get_all_no_permission(self):
        exc = self.assertRaises(
            AppError, self.get_json, '/quotas',
            headers=self.reader_headers)
        self.assertIn("403 Forbidden", str(exc))

    def test_get_no_permission(self):
        quota = obj_utils.create_test_quota(self.context)
        exc = self.assertRaises(
            AppError,
            self.get_json,
            f"/quotas/{quota['project_id']}/{quota['resource']}",
            headers=self.member_headers)
        self.assertIn("403 Forbidden", str(exc))

    @mock.patch.object(clients.OpenStackClients, 'keystone')
    def test_create_no_permission(self, mock_keystone):
        exc = self.assertRaises(
            AppError, self.post_json,
            '/quotas', apiutils.quota_post_data(),
            headers=self.reader_headers)
        self.assertIn("403 Forbidden", str(exc))

    @mock.patch.object(clients.OpenStackClients, 'keystone')
    def test_update_no_permission(self, mock_keystone):
        with mock.patch("magnum.common.policy.enforce"):
            quota_dict = apiutils.quota_post_data(hard_limit=5)
            self.post_json('/quotas', quota_dict)
        quota_dict['hard_limit'] = 20
        exc = self.assertRaises(
            AppError, self.patch_json, '/quotas', quota_dict,
            headers=self.reader_headers)
        self.assertIn("403 Forbidden", str(exc))

    @mock.patch.object(clients.OpenStackClients, 'keystone')
    def test_delete_no_permission(self, mock_keystone):
        with mock.patch("magnum.common.policy.enforce"):
            quota_dict = apiutils.quota_post_data()
            response = self.post_json('/quotas', quota_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)

        project_id = quota_dict['project_id']
        resource = quota_dict['resource']
        # delete quota
        exc = self.assertRaises(
            AppError, self.delete, f"/quotas/{project_id}/{resource}",
            headers=self.reader_headers)
        self.assertIn("403 Forbidden", str(exc))
