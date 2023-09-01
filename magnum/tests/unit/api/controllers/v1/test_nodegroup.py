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

import datetime
from unittest import mock

from oslo_utils import timeutils
from oslo_utils import uuidutils

from magnum.api.controllers.v1 import nodegroup as api_nodegroup
from magnum.conductor import api as rpcapi
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
        self.assertEqual(0, nodegroup.min_node_count)
        self.assertIsNone(nodegroup.max_node_count)


class NodeGroupControllerTest(api_base.FunctionalTest):
    headers = {"Openstack-Api-Version": "container-infra latest"}

    def _add_headers(self, kwargs, roles=None):
        if 'headers' not in kwargs:
            kwargs['headers'] = self.headers
            if roles:
                kwargs['headers']['X-Roles'] = ",".join(roles)

    def get_json(self, *args, **kwargs):
        self._add_headers(kwargs, roles=['reader'])
        return super(NodeGroupControllerTest, self).get_json(*args, **kwargs)

    def post_json(self, *args, **kwargs):
        self._add_headers(kwargs, roles=['member'])
        return super(NodeGroupControllerTest, self).post_json(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self._add_headers(kwargs, roles=['member'])
        return super(NodeGroupControllerTest, self).delete(*args, **kwargs)

    def patch_json(self, *args, **kwargs):
        self._add_headers(kwargs, roles=['member'])
        return super(NodeGroupControllerTest, self).patch_json(*args, **kwargs)


class TestListNodegroups(NodeGroupControllerTest):
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

    def test_get_all_with_pagination_marker(self):
        worker_ng_uuid = self.cluster.default_ng_worker.uuid
        master_ng_uuid = self.cluster.default_ng_master.uuid
        # First make sure that the api returns 1 ng and since they
        # are sorted by id, the ng should be the default-worker
        url = '/clusters/%s/nodegroups?limit=1' % (self.cluster_uuid)
        response = self.get_json(url)
        self.assertEqual(1, len(response['nodegroups']))
        self.assertEqual(worker_ng_uuid, response['nodegroups'][0]['uuid'])
        marker = "marker=%s" % worker_ng_uuid
        self.assertIn(marker, response['next'])
        # Now using the next url make sure that we get the default-master
        next_url = response['next'].split('v1')[1]
        response = self.get_json(next_url)
        self.assertEqual(1, len(response['nodegroups']))
        self.assertEqual(master_ng_uuid, response['nodegroups'][0]['uuid'])
        marker = "marker=%s" % master_ng_uuid
        self.assertIn(marker, response['next'])
        # Now we should not get any other entry since the cluster only has two
        # nodegroups and the marker is set at the default-master.
        next_url = response['next'].split('v1')[1]
        response = self.get_json(next_url)
        self.assertEqual(0, len(response['nodegroups']))
        self.assertNotIn('next', response)

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
        self.assertEqual({}, response['labels_overridden'])
        self.assertEqual({}, response['labels_skipped'])
        self.assertEqual({}, response['labels_added'])

    def test_get_one_non_default(self):
        self.cluster.labels = {'label1': 'value1', 'label2': 'value2'}
        self.cluster.save()
        ng_name = 'non_default_ng'
        ng_labels = {
            'label1': 'value3', 'label2': 'value2', 'label4': 'value4'
        }
        db_utils.create_test_nodegroup(cluster_id=self.cluster.uuid,
                                       name=ng_name, labels=ng_labels)
        url = '/clusters/%s/nodegroups/%s' % (self.cluster.uuid, ng_name)
        response = self.get_json(url)
        self._verify_attrs(self._nodegroup_attrs, response)
        self._verify_attrs(self._expanded_attrs, response)
        self.assertEqual(ng_labels, response['labels'])
        overridden_labels = {'label1': 'value1'}
        self.assertEqual(overridden_labels, response['labels_overridden'])
        self.assertEqual({'label4': 'value4'}, response['labels_added'])
        self.assertEqual({}, response['labels_skipped'])

    def test_get_one_non_default_skipped_labels(self):
        self.cluster.labels = {'label1': 'value1', 'label2': 'value2'}
        self.cluster.save()
        ng_name = 'non_default_ng'
        ng_labels = {'label1': 'value3', 'label4': 'value4'}
        db_utils.create_test_nodegroup(cluster_id=self.cluster.uuid,
                                       name=ng_name, labels=ng_labels)
        url = '/clusters/%s/nodegroups/%s' % (self.cluster.uuid, ng_name)
        response = self.get_json(url)
        self._verify_attrs(self._nodegroup_attrs, response)
        self._verify_attrs(self._expanded_attrs, response)
        self.assertEqual(ng_labels, response['labels'])
        overridden_labels = {'label1': 'value1'}
        self.assertEqual(overridden_labels, response['labels_overridden'])
        self.assertEqual({'label4': 'value4'}, response['labels_added'])
        self.assertEqual({'label2': 'value2'}, response['labels_skipped'])

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

    def test_get_one_wrong_microversion(self):
        headers = {"Openstack-Api-Version": "container-infra 1.8"}
        worker = self.cluster.default_ng_worker
        url = '/clusters/%s/nodegroups/%s' % (self.cluster.uuid, worker.uuid)
        response = self.get_json(url, headers=headers, expect_errors=True)
        self.assertEqual(406, response.status_code)

    def test_get_all_wrong_microversion(self):
        headers = {"Openstack-Api-Version": "container-infra 1.8"}
        url = '/clusters/%s/nodegroups/' % (self.cluster.uuid)
        response = self.get_json(url, headers=headers, expect_errors=True)
        self.assertEqual(406, response.status_code)


class TestPost(NodeGroupControllerTest):
    def setUp(self):
        super(TestPost, self).setUp()
        self.cluster_template = obj_utils.create_test_cluster_template(
            self.context)
        self.cluster = obj_utils.create_test_cluster(self.context)
        self.cluster.refresh()
        p = mock.patch.object(rpcapi.API, 'nodegroup_create_async')
        self.mock_ng_create = p.start()
        self.mock_ng_create.side_effect = self._simulate_nodegroup_create
        self.addCleanup(p.stop)
        self.url = "/clusters/%s/nodegroups" % self.cluster.uuid

    def _simulate_nodegroup_create(self, cluster, nodegroup):
        nodegroup.create()
        return nodegroup

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_nodegroup(self, mock_utcnow):
        ng_dict = apiutils.nodegroup_post_data()
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.post_json(self.url, ng_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        self.assertTrue(uuidutils.is_uuid_like(response.json['uuid']))
        self.assertFalse(response.json['is_default'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_nodegroup_without_node_count(self, mock_utcnow):
        ng_dict = apiutils.nodegroup_post_data()
        del ng_dict['node_count']
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.post_json(self.url, ng_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        # Verify node_count defaults to 1
        self.assertEqual(1, response.json['node_count'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_nodegroup_with_zero_nodes(self, mock_utcnow):
        ng_dict = apiutils.nodegroup_post_data()
        ng_dict['node_count'] = 0
        ng_dict['min_node_count'] = 0
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.post_json(self.url, ng_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        # Verify node_count is set to zero
        self.assertEqual(0, response.json['node_count'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_nodegroup_with_max_node_count(self, mock_utcnow):
        ng_dict = apiutils.nodegroup_post_data(max_node_count=5)
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.post_json(self.url, ng_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        self.assertEqual(5, response.json['max_node_count'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_nodegroup_with_role(self, mock_utcnow):
        ng_dict = apiutils.nodegroup_post_data(role='test-role')
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.post_json(self.url, ng_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        self.assertEqual('test-role', response.json['role'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_nodegroup_with_labels(self, mock_utcnow):
        labels = {'label1': 'value1'}
        ng_dict = apiutils.nodegroup_post_data(labels=labels)
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.post_json(self.url, ng_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        self.assertEqual(labels, response.json['labels'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_nodegroup_with_image_id(self, mock_utcnow):
        ng_dict = apiutils.nodegroup_post_data(image_id='test_image')
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.post_json(self.url, ng_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        self.assertEqual('test_image', response.json['image_id'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_nodegroup_with_flavor(self, mock_utcnow):
        ng_dict = apiutils.nodegroup_post_data(flavor_id='test_flavor')
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.post_json(self.url, ng_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        self.assertEqual('test_flavor', response.json['flavor_id'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_nodegroup_only_name(self, mock_utcnow):
        ng_dict = {'name': 'test_ng'}
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.post_json(self.url, ng_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        self.assertEqual('worker', response.json['role'])
        self.assertEqual(self.cluster_template.image_id,
                         response.json['image_id'])
        self.assertEqual(self.cluster.flavor_id, response.json['flavor_id'])
        self.assertEqual(self.cluster.uuid, response.json['cluster_id'])
        self.assertEqual(self.cluster.project_id, response.json['project_id'])
        self.assertEqual(self.cluster.labels, response.json['labels'])
        self.assertEqual('worker', response.json['role'])
        self.assertEqual(0, response.json['min_node_count'])
        self.assertEqual(1, response.json['node_count'])
        self.assertIsNone(response.json['max_node_count'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_nodegroup_invalid_node_count(self, mock_utcnow):
        ng_dict = apiutils.nodegroup_post_data(node_count=7, max_node_count=5)
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.post_json(self.url, ng_dict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(409, response.status_int)

        ng_dict = apiutils.nodegroup_post_data(node_count=2, min_node_count=3)

        response = self.post_json(self.url, ng_dict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(409, response.status_int)

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_master_ng(self, mock_utcnow):
        ng_dict = apiutils.nodegroup_post_data(role='master')
        response = self.post_json(self.url, ng_dict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_ng_same_name(self, mock_utcnow):
        existing_name = self.cluster.default_ng_master.name
        ng_dict = apiutils.nodegroup_post_data(name=existing_name)
        response = self.post_json(self.url, ng_dict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(409, response.status_int)

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_ng_wrong_microversion(self, mock_utcnow):
        headers = {"Openstack-Api-Version": "container-infra 1.8"}
        ng_dict = apiutils.nodegroup_post_data(name="new_ng")
        response = self.post_json(self.url, ng_dict, headers=headers,
                                  expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(406, response.status_int)

    def test_create_ng_cluster_no_api_address(self):
        # Remove the api address from the cluster and make sure
        # that the request is not accepted.
        self.cluster.api_address = None
        self.cluster.save()
        ng_dict = apiutils.nodegroup_post_data()
        response = self.post_json(self.url, ng_dict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(409, response.status_int)

    def test_create_ng_with_labels(self):
        cluster_labels = {'label1': 'value1', 'label2': 'value2'}
        self.cluster.labels = cluster_labels
        self.cluster.save()
        ng_labels = {'label3': 'value3'}
        ng_dict = apiutils.nodegroup_post_data(labels=ng_labels)
        response = self.post_json(self.url, ng_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        (cluster, ng), _ = self.mock_ng_create.call_args
        self.assertEqual(ng_labels, ng.labels)

    def test_create_ng_with_merge_labels(self):
        cluster_labels = {'label1': 'value1', 'label2': 'value2'}
        self.cluster.labels = cluster_labels
        self.cluster.save()
        ng_labels = {'label1': 'value3', 'label4': 'value4'}
        ng_dict = apiutils.nodegroup_post_data(labels=ng_labels,
                                               merge_labels=True)
        response = self.post_json(self.url, ng_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        (cluster, ng), _ = self.mock_ng_create.call_args
        expected_labels = cluster.labels
        expected_labels.update(ng_labels)
        self.assertEqual(expected_labels, ng.labels)

    def test_create_ng_with_merge_labels_no_labels(self):
        cluster_labels = {'label1': 'value1', 'label2': 'value2'}
        self.cluster.labels = cluster_labels
        self.cluster.save()
        ng_dict = apiutils.nodegroup_post_data(merge_labels=True)
        ng_dict.pop('labels')
        response = self.post_json(self.url, ng_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        (cluster, ng), _ = self.mock_ng_create.call_args
        self.assertEqual(cluster.labels, ng.labels)


class TestDelete(NodeGroupControllerTest):

    def setUp(self):
        super(TestDelete, self).setUp()
        self.cluster_template = obj_utils.create_test_cluster_template(
            self.context)
        self.cluster = obj_utils.create_test_cluster(self.context)
        self.cluster.refresh()
        self.nodegroup = obj_utils.create_test_nodegroup(
            self.context, cluster_id=self.cluster.uuid, is_default=False)
        p = mock.patch.object(rpcapi.API, 'nodegroup_delete_async')
        self.mock_ng_delete = p.start()
        self.mock_ng_delete.side_effect = self._simulate_nodegroup_delete
        self.addCleanup(p.stop)
        self.url = "/clusters/%s/nodegroups/" % self.cluster.uuid

    def _simulate_nodegroup_delete(self, cluster, nodegroup):
        nodegroup.destroy()

    def test_delete_nodegroup(self):
        response = self.delete(self.url + self.nodegroup.uuid)
        self.assertEqual(204, response.status_int)
        response = self.get_json(self.url + self.nodegroup.uuid,
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertIsNotNone(response.json['errors'])

    def test_delete_nodegroup_by_name(self):
        response = self.delete(self.url + self.nodegroup.name)
        self.assertEqual(204, response.status_int)
        response = self.get_json(self.url + self.nodegroup.name,
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertIsNotNone(response.json['errors'])

    def test_delete_not_found(self):
        uuid = uuidutils.generate_uuid()
        response = self.delete(self.url + uuid, expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertIsNotNone(response.json['errors'])

    def test_delete_by_name_not_found(self):
        response = self.delete(self.url + "not-there", expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertIsNotNone(response.json['errors'])

    def test_delete_default_nodegroup(self):
        response = self.delete(self.url + self.cluster.default_ng_master.uuid,
                               expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertIsNotNone(response.json['errors'])

    @mock.patch("magnum.common.policy.enforce")
    @mock.patch("magnum.common.context.make_context")
    def test_delete_nodegroup_as_admin(self, mock_context, mock_policy):
        cluster_uuid = uuidutils.generate_uuid()
        obj_utils.create_test_cluster(self.context, uuid=cluster_uuid,
                                      project_id='fake', name='test-fake')
        ng_uuid = uuidutils.generate_uuid()
        obj_utils.create_test_nodegroup(self.context, uuid=ng_uuid,
                                        cluster_id=cluster_uuid,
                                        is_default=False,
                                        project_id='fake', id=50)
        self.context.is_admin = True
        url = '/clusters/%s/nodegroups/%s' % (cluster_uuid, ng_uuid)
        response = self.delete(url)
        self.assertEqual(204, response.status_int)

    def test_delete_wrong_microversion(self):
        headers = {"Openstack-Api-Version": "container-infra 1.8"}
        response = self.delete(self.url + self.nodegroup.uuid, headers=headers,
                               expect_errors=True)
        self.assertEqual(406, response.status_int)


class TestPatch(NodeGroupControllerTest):
    def setUp(self):
        super(TestPatch, self).setUp()
        self.cluster_template = obj_utils.create_test_cluster_template(
            self.context)
        self.cluster = obj_utils.create_test_cluster(self.context)
        self.cluster.refresh()
        self.nodegroup = obj_utils.create_test_nodegroup(
            self.context, cluster_id=self.cluster.uuid, is_default=False,
            min_node_count=2, max_node_count=5, node_count=2)
        p = mock.patch.object(rpcapi.API, 'nodegroup_update_async')
        self.mock_ng_update = p.start()
        self.mock_ng_update.side_effect = self._simulate_nodegroup_update
        self.addCleanup(p.stop)
        self.url = "/clusters/%s/nodegroups/" % self.cluster.uuid

    def _simulate_nodegroup_update(self, cluster, nodegroup):
        nodegroup.save()
        return nodegroup

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok(self, mock_utcnow):
        max_node_count = 4
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json(self.url + self.nodegroup.uuid,
                                   [{'path': '/max_node_count',
                                     'value': max_node_count,
                                     'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_code)

        response = self.get_json(self.url + self.nodegroup.uuid)
        self.assertEqual(max_node_count, response['max_node_count'])
        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_name(self, mock_utcnow):
        max_node_count = 4
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json(self.url + self.nodegroup.name,
                                   [{'path': '/max_node_count',
                                     'value': max_node_count,
                                     'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_code)

        response = self.get_json(self.url + self.nodegroup.uuid)
        self.assertEqual(max_node_count, response['max_node_count'])
        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)

    def test_replace_node_count_failed(self):
        response = self.patch_json(self.url + self.nodegroup.name,
                                   [{'path': '/node_count',
                                     'value': 3,
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertIsNotNone(response.json['errors'])

    def test_replace_max_node_count_failed(self):
        # min_node_count equals to 2. Verify that if the max_node_count
        # is less than the min the patch fails
        response = self.patch_json(self.url + self.nodegroup.name,
                                   [{'path': '/max_node_count',
                                     'value': 1,
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(409, response.status_code)
        self.assertIsNotNone(response.json['errors'])

    def test_replace_min_node_count_failed(self):
        # min_node_count equals to 2. Verify that if the max_node_count
        # is less than the min the patch fails
        response = self.patch_json(self.url + self.nodegroup.name,
                                   [{'path': '/min_node_count',
                                     'value': 3,
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(409, response.status_code)
        self.assertIsNotNone(response.json['errors'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_remove_ok(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json(self.url + self.nodegroup.name,
                                   [{'path': '/max_node_count',
                                     'op': 'remove'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_code)

        response = self.get_json(self.url + self.nodegroup.uuid)
        self.assertIsNone(response['max_node_count'])
        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_remove_min_node_count(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json(self.url + self.nodegroup.name,
                                   [{'path': '/min_node_count',
                                     'op': 'remove'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_code)

        response = self.get_json(self.url + self.nodegroup.uuid)
        # Removing the min_node_count just restores the default value
        self.assertEqual(0, response['min_node_count'])
        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_remove_internal_attr(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json(self.url + self.nodegroup.name,
                                   [{'path': '/node_count',
                                     'op': 'remove'}], expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertIsNotNone(response.json['errors'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_remove_non_existent_property(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json(self.url + self.nodegroup.name,
                                   [{'path': '/not_there',
                                     'op': 'remove'}], expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertIsNotNone(response.json['errors'])

    @mock.patch("magnum.common.policy.enforce")
    @mock.patch("magnum.common.context.make_context")
    def test_update_nodegroup_as_admin(self, mock_context, mock_policy):
        cluster_uuid = uuidutils.generate_uuid()
        obj_utils.create_test_cluster(self.context, uuid=cluster_uuid,
                                      project_id='fake', name='test-fake')
        ng_uuid = uuidutils.generate_uuid()
        obj_utils.create_test_nodegroup(self.context, uuid=ng_uuid,
                                        cluster_id=cluster_uuid,
                                        is_default=False,
                                        project_id='fake', id=50)
        self.context.is_admin = True
        url = '/clusters/%s/nodegroups/%s' % (cluster_uuid, ng_uuid)
        response = self.patch_json(url,
                                   [{'path': '/max_node_count',
                                     'value': 4,
                                     'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_code)

    def test_replace_wrong_microversion(self):
        headers = {"Openstack-Api-Version": "container-infra 1.8"}
        response = self.patch_json(self.url + self.nodegroup.name,
                                   [{'path': '/max_node_count',
                                     'value': 4,
                                     'op': 'replace'}], headers=headers,
                                   expect_errors=True)
        self.assertEqual(406, response.status_code)


class TestNodeGroupPolicyEnforcement(NodeGroupControllerTest):
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
