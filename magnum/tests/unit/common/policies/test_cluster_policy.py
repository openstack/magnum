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

from magnum.tests.unit.api import utils as apiutils
from magnum.tests.unit.common.policies import base
from magnum.tests.unit.objects import utils as obj_utils


class TestClusterPolicy(base.PolicyFunctionalTest):
    def setUp(self):
        super(TestClusterPolicy, self).setUp()
        self.cluster = obj_utils.create_test_cluster(
            self.context, name='cluster_example_A', node_count=3
        )

    def test_get_all_no_permission(self):
        exc = self.assertRaises(
            AppError, self.get_json, '/clusters',
            headers=self.member_headers)
        self.assertIn("403 Forbidden", str(exc))

    def test_get_no_permission(self):
        exc = self.assertRaises(
            AppError,
            self.get_json,
            f"/clusters/{self.cluster.uuid}",
            headers=self.member_headers)
        self.assertIn("403 Forbidden", str(exc))

    def test_create_no_permission(self):
        exc = self.assertRaises(
            AppError, self.post_json,
            '/clusters', apiutils.cluster_post_data(),
            headers=self.reader_headers)
        self.assertIn("403 Forbidden", str(exc))

    def test_update_no_permission(self):
        cluster_dict = [
            {'path': '/node_count', 'value': 4, 'op': 'replace'}
        ]
        exc = self.assertRaises(
            AppError, self.patch_json,
            f"/clusters/{self.cluster.name}", cluster_dict,
            headers=self.reader_headers
        )
        self.assertIn("403 Forbidden", str(exc))

    def test_delete_no_permission(self):
        # delete cluster
        exc = self.assertRaises(
            AppError, self.delete, f"/clusters/{self.cluster.uuid}",
            headers=self.reader_headers
        )
        self.assertIn("403 Forbidden", str(exc))
