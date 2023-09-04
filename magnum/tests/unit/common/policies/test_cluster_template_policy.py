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


class TestClusterTemplatePolicy(base.PolicyFunctionalTest):
    def setUp(self):
        super(TestClusterTemplatePolicy, self).setUp()
        self.clustertemplate = obj_utils.create_test_cluster_template(
            self.context
        )

    def test_get_all_no_permission(self):
        exc = self.assertRaises(
            AppError, self.get_json, '/clustertemplates',
            headers=self.member_headers)
        self.assertIn("403 Forbidden", str(exc))

    def test_get_detail_no_permission(self):
        exc = self.assertRaises(
            AppError, self.get_json,
            '/clustertemplates/detail',
            headers=self.member_headers)
        self.assertIn("403 Forbidden", str(exc))

    def test_get_no_permission(self):
        exc = self.assertRaises(
            AppError,
            self.get_json,
            f"/clustertemplates/{self.clustertemplate.uuid}",
            headers=self.member_headers)
        self.assertIn("403 Forbidden", str(exc))

    def test_create_no_permission(self):
        exc = self.assertRaises(
            AppError, self.post_json,
            '/clustertemplates',
            apiutils.cluster_template_post_data(),
            headers=self.reader_headers)
        self.assertIn("403 Forbidden", str(exc))

    def test_update_no_permission(self):
        clustertemplate_data = [
            {'path': '/dns_nameserver', 'op': 'remove'}]
        exc = self.assertRaises(
            AppError,
            self.patch_json,
            f"/clustertemplates/{self.clustertemplate.uuid}",
            clustertemplate_data,
            headers=self.reader_headers
        )
        self.assertIn("403 Forbidden", str(exc))

    def test_delete_no_permission(self):
        # delete clustertemplate
        exc = self.assertRaises(
            AppError, self.delete,
            f"/clustertemplates/{self.clustertemplate.uuid}",
            headers=self.reader_headers)
        self.assertIn("403 Forbidden", str(exc))
