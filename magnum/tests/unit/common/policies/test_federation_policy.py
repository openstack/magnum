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

from oslo_utils import uuidutils
from webtest.app import AppError

from magnum.tests.unit.common.policies import base
from magnum.tests.unit.objects import utils as obj_utils


class TestFederationPolicy(base.PolicyFunctionalTest):
    def setUp(self):
        super(TestFederationPolicy, self).setUp()
        self.create_frederation()

    def create_frederation(self):
        self.fake_uuid = uuidutils.generate_uuid()
        self.federation = obj_utils.create_test_federation(
            self.context, uuid=self.fake_uuid)

    def test_get_no_permission(self):
        exc = self.assertRaises(
            AppError, self.get_json, '/federations',
            headers=self.member_headers)
        self.assertIn("403 Forbidden", str(exc))

    def test_get_reader(self):
        response = self.get_json('/federations')
        self.assertEqual(self.fake_uuid, response['federations'][0]['uuid'])

    def test_create_no_permission(self):
        exc = self.assertRaises(
            AppError, self.post_json, '/federations', {},
            headers=self.reader_headers)
        self.assertIn("403 Forbidden", str(exc))

    def test_update_no_permission(self):
        new_member = obj_utils.create_test_cluster(self.context)
        exc = self.assertRaises(
            AppError, self.patch_json, '/federations/%s' % self.fake_uuid,
            [{'path': '/member_ids', 'value': new_member.uuid, 'op': 'add'}],
            headers=self.reader_headers)
        self.assertIn("403 Forbidden", str(exc))

    def test_delete_no_permission(self):
        exc = self.assertRaises(
            AppError, self.delete,
            '/federations/%s' % self.fake_uuid,
            headers=self.reader_headers
        )
        self.assertIn("403 Forbidden", str(exc))

    def test_detail_list_no_permission(self):
        exc = self.assertRaises(
            AppError, self.get_json,
            '/federations/detail',
            headers=self.member_headers)
        self.assertIn("403 Forbidden", str(exc))
