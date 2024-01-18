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

from oslo_utils import uuidutils

from magnum.common import context as magnum_context
from magnum.conductor import api as rpcapi
import magnum.conf
from magnum.tests.unit.api import base as api_base
from magnum.tests.unit.objects import utils as obj_utils

CONF = magnum.conf.CONF


class TestClusterResize(api_base.FunctionalTest):

    def setUp(self):
        super(TestClusterResize, self).setUp()
        self.cluster_obj = obj_utils.create_test_cluster(
            self.context, name='cluster_example_A', node_count=3)
        p = mock.patch.object(rpcapi.API, 'cluster_resize_async')
        self.mock_cluster_resize = p.start()
        self.mock_cluster_resize.side_effect = self._sim_rpc_cluster_resize
        self.addCleanup(p.stop)

    def _sim_rpc_cluster_resize(self, cluster, node_count, nodes_to_remove,
                                nodegroup, rollback=False):
        nodegroup.node_count = node_count
        nodegroup.save()
        return cluster

    def test_resize(self):
        new_node_count = 6
        response = self.post_json('/clusters/%s/actions/resize' %
                                  self.cluster_obj.uuid,
                                  {"node_count": new_node_count},
                                  headers={"Openstack-Api-Version":
                                           "container-infra 1.7",
                                           "X-Roles": "member"})
        self.assertEqual(202, response.status_code)

        response = self.get_json('/clusters/%s' % self.cluster_obj.uuid)
        self.assertEqual(new_node_count, response['node_count'])
        self.assertEqual(self.cluster_obj.uuid, response['uuid'])
        self.assertEqual(self.cluster_obj.cluster_template_id,
                         response['cluster_template_id'])

    def test_resize_with_nodegroup(self):
        new_node_count = 6
        nodegroup = self.cluster_obj.default_ng_worker
        # Verify that the API is ok with maximum allowed
        # node count set to None
        self.assertIsNone(nodegroup.max_node_count)
        cluster_resize_req = {
            "node_count": new_node_count,
            "nodegroup": nodegroup.uuid
        }
        response = self.post_json('/clusters/%s/actions/resize' %
                                  self.cluster_obj.uuid,
                                  cluster_resize_req,
                                  headers={"Openstack-Api-Version":
                                           "container-infra 1.9",
                                           "X-Roles": "member"})
        self.assertEqual(202, response.status_code)

        response = self.get_json('/clusters/%s' % self.cluster_obj.uuid)
        self.assertEqual(new_node_count, response['node_count'])
        self.assertEqual(self.cluster_obj.uuid, response['uuid'])
        self.assertEqual(self.cluster_obj.cluster_template_id,
                         response['cluster_template_id'])

    def test_resize_with_master_nodegroup_even_unsupported(self):
        new_node_count = 4
        nodegroup = self.cluster_obj.default_ng_master
        cluster_resize_req = {
            "node_count": new_node_count,
            "nodegroup": nodegroup.uuid
        }
        response = self.post_json('/clusters/%s/actions/resize' %
                                  self.cluster_obj.uuid,
                                  cluster_resize_req,
                                  headers={"Openstack-Api-Version":
                                           "container-infra 1.9",
                                           "X-Roles": "member"},
                                  expect_errors=True)
        self.assertEqual(400, response.status_code)

    def test_resize_with_master_nodegroup_odd_unsupported(self):
        new_node_count = 3
        nodegroup = self.cluster_obj.default_ng_master
        cluster_resize_req = {
            "node_count": new_node_count,
            "nodegroup": nodegroup.uuid
        }
        response = self.post_json('/clusters/%s/actions/resize' %
                                  self.cluster_obj.uuid,
                                  cluster_resize_req,
                                  headers={"Openstack-Api-Version":
                                           "container-infra 1.9",
                                           "X-Roles": "member"},
                                  expect_errors=True)
        self.assertEqual(400, response.status_code)

    def test_resize_with_node_count_greater_than_max(self):
        new_node_count = 6
        nodegroup = self.cluster_obj.default_ng_worker
        nodegroup.max_node_count = 5
        nodegroup.save()
        cluster_resize_req = {
            "node_count": new_node_count,
            "nodegroup": nodegroup.uuid
        }
        response = self.post_json('/clusters/%s/actions/resize' %
                                  self.cluster_obj.uuid,
                                  cluster_resize_req,
                                  headers={"Openstack-Api-Version":
                                           "container-infra 1.9",
                                           "X-Roles": "member"},
                                  expect_errors=True)
        self.assertEqual(400, response.status_code)

    def test_resize_with_node_count_less_than_min(self):
        new_node_count = 3
        nodegroup = self.cluster_obj.default_ng_worker
        nodegroup.min_node_count = 4
        nodegroup.save()
        cluster_resize_req = {
            "node_count": new_node_count,
            "nodegroup": nodegroup.uuid
        }
        response = self.post_json('/clusters/%s/actions/resize' %
                                  self.cluster_obj.uuid,
                                  cluster_resize_req,
                                  headers={"Openstack-Api-Version":
                                           "container-infra 1.9",
                                           "X-Roles": "member"},
                                  expect_errors=True)
        self.assertEqual(400, response.status_code)

    def test_resize_with_zero_node_count_fail(self):
        new_node_count = 0
        nodegroup = self.cluster_obj.default_ng_worker
        nodegroup.min_node_count = 0
        nodegroup.save()
        cluster_resize_req = {
            "node_count": new_node_count,
            "nodegroup": nodegroup.uuid
        }
        response = self.post_json('/clusters/%s/actions/resize' %
                                  self.cluster_obj.uuid,
                                  cluster_resize_req,
                                  headers={"Openstack-Api-Version":
                                           "container-infra 1.9",
                                           "X-Roles": "member"},
                                  expect_errors=True)
        self.assertEqual(400, response.status_code)

    def test_resize_with_zero_node_count(self):
        new_node_count = 0
        nodegroup = self.cluster_obj.default_ng_worker
        nodegroup.min_node_count = 0
        nodegroup.save()
        cluster_resize_req = {
            "node_count": new_node_count,
            "nodegroup": nodegroup.uuid
        }
        response = self.post_json('/clusters/%s/actions/resize' %
                                  self.cluster_obj.uuid,
                                  cluster_resize_req,
                                  headers={"Openstack-Api-Version":
                                           "container-infra 1.10",
                                           "X-Roles": "member"})
        self.assertEqual(202, response.status_code)


class TestClusterUpgrade(api_base.FunctionalTest):
    def setUp(self):
        super(TestClusterUpgrade, self).setUp()
        self.cluster_template1 = obj_utils.create_test_cluster_template(
            self.context, uuid='94889766-e686-11e9-81b4-2a2ae2dbcce4',
            name='test_1', id=1)
        self.cluster_template2 = obj_utils.create_test_cluster_template(
            self.context, uuid='94889aa4-e686-11e9-81b4-2a2ae2dbcce4',
            name='test_2', id=2)
        self.cluster_obj = obj_utils.create_test_cluster(
            self.context, name='cluster_example_A',
            cluster_template_id=self.cluster_template1.uuid)
        self.nodegroup_obj = obj_utils.create_test_nodegroup(
            self.context, name='test_ng', cluster_id=self.cluster_obj.uuid,
            uuid='27e3153e-d5bf-4b7e-b517-fb518e17f34c',
            project_id=self.cluster_obj.project_id,
            is_default=False)
        p = mock.patch.object(rpcapi.API, 'cluster_upgrade')
        self.mock_cluster_upgrade = p.start()
        self.mock_cluster_upgrade.side_effect = self._sim_rpc_cluster_upgrade
        self.addCleanup(p.stop)

    def _sim_rpc_cluster_upgrade(self, cluster, cluster_template, batch_size,
                                 nodegroup):
        return cluster

    def test_upgrade(self):
        cluster_upgrade_req = {
            "cluster_template": "test_2"
        }
        response = self.post_json('/clusters/%s/actions/upgrade' %
                                  self.cluster_obj.uuid,
                                  cluster_upgrade_req,
                                  headers={"Openstack-Api-Version":
                                           "container-infra 1.8",
                                           "X-Roles": "member"})
        self.assertEqual(202, response.status_code)

    def test_upgrade_cluster_as_admin(self):
        token_info = {
            'token': {
                'project': {'id': 'fake_project_1'},
                'user': {'id': 'fake_user_1'}
            }
        }
        user_context = magnum_context.RequestContext(
            auth_token_info=token_info,
            project_id='fake_project_1',
            user_id='fake_user_1',
            is_admin=False)
        cluster_uuid = uuidutils.generate_uuid()
        cluster_template_uuid = uuidutils.generate_uuid()
        obj_utils.create_test_cluster_template(
            user_context,
            public=True, uuid=cluster_template_uuid)
        obj_utils.create_test_cluster(
            user_context,
            uuid=cluster_uuid,
            cluster_template_id=cluster_template_uuid)

        cluster_upgrade_req = {"cluster_template": "test_2"}
        self.context.is_admin = True
        response = self.post_json(
            '/clusters/%s/actions/upgrade' %
            cluster_uuid,
            cluster_upgrade_req,
            headers={"Openstack-Api-Version": "container-infra 1.8",
                     "X-Roles": "member"})

        self.assertEqual(202, response.status_int)

    def test_upgrade_default_worker(self):
        cluster_upgrade_req = {
            "cluster_template": "test_2",
            "nodegroup": self.cluster_obj.default_ng_worker.uuid
        }
        response = self.post_json('/clusters/%s/actions/upgrade' %
                                  self.cluster_obj.uuid,
                                  cluster_upgrade_req,
                                  headers={"Openstack-Api-Version":
                                           "container-infra 1.9",
                                           "X-Roles": "member"})
        self.assertEqual(202, response.status_code)

    def test_upgrade_default_master(self):
        cluster_upgrade_req = {
            "cluster_template": "test_2",
            "nodegroup": self.cluster_obj.default_ng_master.uuid
        }
        response = self.post_json('/clusters/%s/actions/upgrade' %
                                  self.cluster_obj.uuid,
                                  cluster_upgrade_req,
                                  headers={"Openstack-Api-Version":
                                           "container-infra 1.9",
                                           "X-Roles": "member"})
        self.assertEqual(202, response.status_code)

    def test_upgrade_non_default_ng(self):
        cluster_upgrade_req = {
            "cluster_template": "test_1",
            "nodegroup": self.nodegroup_obj.uuid
        }
        response = self.post_json('/clusters/%s/actions/upgrade' %
                                  self.cluster_obj.uuid,
                                  cluster_upgrade_req,
                                  headers={"Openstack-Api-Version":
                                           "container-infra 1.9",
                                           "X-Roles": "member"})
        self.assertEqual(202, response.status_code)

    def test_upgrade_cluster_not_found(self):
        cluster_upgrade_req = {
            "cluster_template": "test_2"
        }
        response = self.post_json('/clusters/not_there/actions/upgrade',
                                  cluster_upgrade_req,
                                  headers={"Openstack-Api-Version":
                                           "container-infra 1.8",
                                           "X-Roles": "member"},
                                  expect_errors=True)
        self.assertEqual(404, response.status_code)

    def test_upgrade_ct_not_found(self):
        cluster_upgrade_req = {
            "cluster_template": "not_there"
        }
        response = self.post_json('/clusters/%s/actions/upgrade' %
                                  self.cluster_obj.uuid,
                                  cluster_upgrade_req,
                                  headers={"Openstack-Api-Version":
                                           "container-infra 1.8",
                                           "X-Roles": "member"},
                                  expect_errors=True)
        self.assertEqual(404, response.status_code)

    def test_upgrade_ng_not_found(self):
        cluster_upgrade_req = {
            "cluster_template": "test_2",
            "nodegroup": "not_there"
        }
        response = self.post_json('/clusters/%s/actions/upgrade' %
                                  self.cluster_obj.uuid,
                                  cluster_upgrade_req,
                                  headers={"Openstack-Api-Version":
                                           "container-infra 1.9",
                                           "X-Roles": "member"},
                                  expect_errors=True)
        self.assertEqual(404, response.status_code)

    def test_upgrade_non_default_ng_invalid_ct(self):
        cluster_upgrade_req = {
            "cluster_template": "test_2",
            "nodegroup": self.nodegroup_obj.uuid
        }
        response = self.post_json('/clusters/%s/actions/upgrade' %
                                  self.cluster_obj.uuid,
                                  cluster_upgrade_req,
                                  headers={"Openstack-Api-Version":
                                           "container-infra 1.9",
                                           "X-Roles": "member"},
                                  expect_errors=True)
        self.assertEqual(409, response.status_code)
