# Copyright (c) 2018 European Organization for Nuclear Research.
# All Rights Reserved.
#
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

import mock

from oslo_utils import uuidutils

from magnum.api.controllers.v1 import nodegroup as api_nodegroup
import magnum.conf
from magnum import objects
from magnum.tests import base
from magnum.tests.unit.api import base as api_base
from magnum.tests.unit.api import utils as apiutils
from magnum.tests.unit.db import utils as db_utils
from magnum.tests.unit.objects import utils as obj_utils

CONF = magnum.conf.CONF


class TestNodegroupObject(base.TestCase):
    def test_nodegroup_init(self):
        nodegroup_dict = apiutils.nodegroup_post_data()
        del nodegroup_dict['node_count']
        del nodegroup_dict['min_node_count']
        del nodegroup_dict['max_node_count']
        nodegroup = api_nodegroup.NodeGroup(**nodegroup_dict)
        self.assertEqual(1, nodegroup.node_count)
        self.assertEqual(1, nodegroup.min_node_count)
        self.assertIsNone(nodegroup.max_node_count)


class TestListNodegroups(api_base.FunctionalTest):
    _expanded_attrs = ["id", "project_id", "docker_volume_size", "labels",
                       "node_addresses", "links"]

    _nodegroup_attrs = ["uuid", "name", "flavor_id", "node_count", "role",
                        "is_default", "image_id", "min_node_count",
                        "max_node_count"]

    def setUp(self):
        super(TestListNodegroups, self).setUp()
        obj_utils.create_test_cluster_template(self.context)
        self.cluster_uuid = uuidutils.generate_uuid()
        obj_utils.create_test_cluster(
            self.context, uuid=self.cluster_uuid)
        self.cluster = objects.Cluster.get_by_uuid(self.context,
                                                   self.cluster_uuid)

    def _test_list_nodegroups(self, cluster_id, filters=None, expected=None):
        url = '/clusters/%s/nodegroups' % cluster_id
        if filters is not None:
            filter_list = ['%s=%s' % (k, v) for k, v in filters.items()]
            url += '?' + '&'.join(f for f in filter_list)
        response = self.get_json(url)
        if expected is None:
            expected = []
        ng_uuids = [ng['uuid'] for ng in response['nodegroups']]
        self.assertEqual(expected, ng_uuids)
        for ng in response['nodegroups']:
            self._verify_attrs(self._nodegroup_attrs, ng)
            self._verify_attrs(self._expanded_attrs, ng, positive=False)

    def test_get_all(self):
        expected = [ng.uuid for ng in self.cluster.nodegroups]
        self._test_list_nodegroups(self.cluster_uuid, expected=expected)

    def test_get_all_by_name(self):
        expected = [ng.uuid for ng in self.cluster.nodegroups]
        self._test_list_nodegroups(self.cluster.name, expected=expected)

    def test_get_all_by_name_non_default_ngs(self):
        db_utils.create_test_nodegroup(cluster_id=self.cluster_uuid,
                                       name='non_default_ng')
        expected = [ng.uuid for ng in self.cluster.nodegroups]
        self._test_list_nodegroups(self.cluster.name, expected=expected)

    def test_get_all_by_role(self):
        filters = {'role': 'master'}
        expected = [self.cluster.default_ng_master.uuid]
        self._test_list_nodegroups(self.cluster.name, filters=filters,
                                   expected=expected)
        filters = {'role': 'worker'}
        expected = [self.cluster.default_ng_worker.uuid]
        self._test_list_nodegroups(self.cluster.name, filters=filters,
                                   expected=expected)

    def test_get_all_by_non_existent_role(self):
        filters = {'role': 'non-existent'}
        self._test_list_nodegroups(self.cluster.name, filters=filters)

    @mock.patch("magnum.common.policy.enforce")
    @mock.patch("magnum.common.context.make_context")
    def test_get_all_as_admin(self, mock_context, mock_policy):
        temp_uuid = uuidutils.generate_uuid()
        obj_utils.create_test_cluster(self.context, uuid=temp_uuid,
                                      project_id=temp_uuid)
        self.context.is_admin = True
        self.context.all_tenants = True
        cluster = objects.Cluster.get_by_uuid(self.context, temp_uuid)
        expected = [ng.uuid for ng in cluster.nodegroups]
        self._test_list_nodegroups(cluster.uuid, expected=expected)

    def test_get_all_non_existent_cluster(self):
        response = self.get_json('/clusters/not-here/nodegroups',
                                 expect_errors=True)
        self.assertEqual(404, response.status_code)

    def test_get_one(self):
        worker = self.cluster.default_ng_worker
        url = '/clusters/%s/nodegroups/%s' % (self.cluster.uuid, worker.uuid)
        response = self.get_json(url)
        self.assertEqual(worker.name, response['name'])
        self._verify_attrs(self._nodegroup_attrs, response)
        self._verify_attrs(self._expanded_attrs, response)

    def test_get_one_non_existent_ng(self):
        url = '/clusters/%s/nodegroups/not-here' % self.cluster.uuid
        response = self.get_json(url, expect_errors=True)
        self.assertEqual(404, response.status_code)

    @mock.patch("magnum.common.policy.enforce")
    @mock.patch("magnum.common.context.make_context")
    def test_get_one_as_admin(self, mock_context, mock_policy):
        temp_uuid = uuidutils.generate_uuid()
        obj_utils.create_test_cluster(self.context, uuid=temp_uuid,
                                      project_id=temp_uuid)
        self.context.is_admin = True
        self.context.all_tenants = True
        cluster = objects.Cluster.get_by_uuid(self.context, temp_uuid)
        worker = cluster.default_ng_worker
        url = '/clusters/%s/nodegroups/%s' % (cluster.uuid, worker.uuid)
        response = self.get_json(url)
        self.assertEqual(worker.name, response['name'])
        self._verify_attrs(self._nodegroup_attrs, response)
        self._verify_attrs(self._expanded_attrs, response)


class TestNodeGroupPolicyEnforcement(api_base.FunctionalTest):
    def setUp(self):
        super(TestNodeGroupPolicyEnforcement, self).setUp()
        obj_utils.create_test_cluster_template(self.context)
        self.cluster_uuid = uuidutils.generate_uuid()
        obj_utils.create_test_cluster(
            self.context, uuid=self.cluster_uuid)
        self.cluster = objects.Cluster.get_by_uuid(self.context,
                                                   self.cluster_uuid)

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules({rule: "project:non_fake"})
        response = func(*arg, **kwarg)
        self.assertEqual(403, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(
            "Policy doesn't allow %s to be performed." % rule,
            response.json['errors'][0]['detail'])

    def test_policy_disallow_get_all(self):
        self._common_policy_check(
            "nodegroup:get_all", self.get_json,
            '/clusters/%s/nodegroups' % self.cluster_uuid, expect_errors=True)

    def test_policy_disallow_get_one(self):
        worker = self.cluster.default_ng_worker
        self._common_policy_check(
            "nodegroup:get", self.get_json,
            '/clusters/%s/nodegroups/%s' % (self.cluster.uuid, worker.uuid),
            expect_errors=True)
