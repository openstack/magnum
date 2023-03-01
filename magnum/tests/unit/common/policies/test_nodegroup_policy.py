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

from magnum import objects
from magnum.tests.unit.api import utils as apiutils
from magnum.tests.unit.common.policies import base
from magnum.tests.unit.objects import utils as obj_utils


class TestNodeGroupPolicy(base.PolicyFunctionalTest):
    def setUp(self):
        super(TestNodeGroupPolicy, self).setUp()
        obj_utils.create_test_cluster_template(self.context)
        self.cluster_uuid = uuidutils.generate_uuid()
        obj_utils.create_test_cluster(
            self.context, uuid=self.cluster_uuid)
        self.cluster = objects.Cluster.get_by_uuid(self.context,
                                                   self.cluster_uuid)
        self.nodegroup = obj_utils.create_test_nodegroup(
            self.context, cluster_id=self.cluster.uuid, is_default=False)
        self.url = f"/clusters/{self.cluster.uuid}/nodegroups/"
        self.member = {"Openstack-Api-Version": "container-infra latest"}
        self.member.update(self.member_headers)
        self.reader = {"Openstack-Api-Version": "container-infra latest"}
        self.reader.update(self.reader_headers)

    def test_get_all_no_permission(self):
        exc = self.assertRaises(AppError,
                                self.get_json, self.url,
                                headers=self.member)
        self.assertIn("403 Forbidden", str(exc))

    def test_get_no_permission(self):
        exc = self.assertRaises(
            AppError,
            self.get_json,
            f"{self.url}foo",
            headers=self.member)
        self.assertIn("403 Forbidden", str(exc))

    def test_create_no_permission(self):
        exc = self.assertRaises(AppError,
                                self.post_json, self.url,
                                apiutils.nodegroup_post_data(),
                                headers=self.reader)
        self.assertIn("403 Forbidden", str(exc))

    def test_update_no_permission(self):
        ng_dict = [
            {'path': '/max_node_count', 'value': 4, 'op': 'replace'}]
        exc = self.assertRaises(
            AppError, self.patch_json,
            self.url + self.nodegroup.uuid, ng_dict,
            headers=self.reader)
        self.assertIn("403 Forbidden", str(exc))

    def test_delete_no_permission(self):
        # delete cluster
        exc = self.assertRaises(
                  AppError, self.delete, self.url + self.nodegroup.uuid,
                  headers=self.reader)
        self.assertIn("403 Forbidden", str(exc))
