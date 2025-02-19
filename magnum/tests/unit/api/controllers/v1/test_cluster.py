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

import datetime
from unittest import mock

from oslo_config import cfg
from oslo_serialization import jsonutils
from oslo_utils import timeutils
from oslo_utils import uuidutils
from wsme import types as wtypes

from magnum.api import attr_validator
from magnum.api.controllers.v1 import cluster as api_cluster
from magnum.common import exception
from magnum.conductor import api as rpcapi
import magnum.conf
from magnum import objects
from magnum.tests import base
from magnum.tests.unit.api import base as api_base
from magnum.tests.unit.api import utils as apiutils
from magnum.tests.unit.db import utils as db_utils
from magnum.tests.unit.objects import utils as obj_utils

CONF = magnum.conf.CONF


class TestClusterObject(base.TestCase):
    def test_cluster_init(self):
        cluster_dict = apiutils.cluster_post_data(cluster_template_id=None)
        del cluster_dict['node_count']
        del cluster_dict['master_count']
        del cluster_dict['create_timeout']
        cluster = api_cluster.Cluster(**cluster_dict)
        self.assertEqual(1, cluster.node_count)
        self.assertEqual(1, cluster.master_count)
        self.assertEqual(60, cluster.create_timeout)

        # test unset value for cluster_template_id
        cluster.cluster_template_id = wtypes.Unset
        self.assertEqual(wtypes.Unset, cluster.cluster_template_id)

        # test backwards compatibility of cluster fields with new objects
        cluster_dict['create_timeout'] = 15
        cluster = api_cluster.Cluster(**cluster_dict)
        self.assertEqual(15, cluster.create_timeout)


class TestListCluster(api_base.FunctionalTest):
    _cluster_attrs = ("name", "cluster_template_id", "node_count", "status",
                      "master_count", "stack_id", "create_timeout")

    _expand_cluster_attrs = ("name", "cluster_template_id", "node_count",
                             "status", "api_address", "discovery_url",
                             "node_addresses", "master_count",
                             "master_addresses", "stack_id",
                             "create_timeout", "status_reason")

    def setUp(self):
        super(TestListCluster, self).setUp()
        obj_utils.create_test_cluster_template(self.context)

    def test_empty(self):
        response = self.get_json('/clusters')
        self.assertEqual([], response['clusters'])

    def test_one(self):
        cluster = obj_utils.create_test_cluster(self.context)
        response = self.get_json('/clusters')
        self.assertEqual(cluster.uuid, response['clusters'][0]["uuid"])
        self._verify_attrs(self._cluster_attrs, response['clusters'][0])

        # Verify attrs do not appear from cluster's get_all response
        none_attrs = \
            set(self._expand_cluster_attrs) - set(self._cluster_attrs)
        self._verify_attrs(none_attrs, response['clusters'][0],
                           positive=False)

    def test_get_one(self):
        cluster = obj_utils.create_test_cluster(self.context)
        response = self.get_json('/clusters/%s' % cluster['uuid'])
        self.assertEqual(cluster.uuid, response['uuid'])
        self._verify_attrs(self._expand_cluster_attrs, response)

    def test_get_one_failed_cluster(self):
        cluster = obj_utils.create_test_cluster(self.context,
                                                status='CREATE_FAILED',
                                                master_status='CREATE_FAILED',
                                                master_reason='fake_reason')
        response = self.get_json('/clusters/%s' % cluster['uuid'])
        expected_faults = {cluster.default_ng_master.name: 'fake_reason'}
        self.assertEqual(cluster.uuid, response['uuid'])
        self.assertEqual(expected_faults, response['faults'])

    def test_get_one_by_name(self):
        cluster = obj_utils.create_test_cluster(self.context)
        response = self.get_json('/clusters/%s' % cluster['name'])
        self.assertEqual(cluster.uuid, response['uuid'])
        self._verify_attrs(self._expand_cluster_attrs, response)

    def test_get_one_by_name_not_found(self):
        response = self.get_json(
            '/clusters/not_found',
            expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_get_one_by_uuid(self):
        temp_uuid = uuidutils.generate_uuid()
        obj_utils.create_test_cluster(self.context, uuid=temp_uuid)
        response = self.get_json('/clusters/%s' % temp_uuid)
        self.assertEqual(temp_uuid, response['uuid'])
        self.assertIn('labels_overridden', response)
        self.assertIn('labels_added', response)
        self.assertIn('labels_skipped', response)

    def test_get_one_merged_labels(self):
        ct_uuid = uuidutils.generate_uuid()
        ct_labels = {'label1': 'value1', 'label2': 'value2'}
        obj_utils.create_test_cluster_template(self.context, uuid=ct_uuid,
                                               labels=ct_labels)
        c_uuid = uuidutils.generate_uuid()
        c_labels = {'label1': 'value3', 'label4': 'value4'}
        obj_utils.create_test_cluster(self.context, uuid=c_uuid,
                                      labels=c_labels,
                                      cluster_template_id=ct_uuid)
        response = self.get_json('/clusters/%s' % c_uuid)
        self.assertEqual(c_labels, response['labels'])
        self.assertEqual({'label1': 'value1'}, response['labels_overridden'])
        self.assertEqual({'label2': 'value2'}, response['labels_skipped'])
        self.assertEqual({'label4': 'value4'}, response['labels_added'])

    def test_get_one_by_uuid_not_found(self):
        temp_uuid = uuidutils.generate_uuid()
        response = self.get_json(
            '/clusters/%s' % temp_uuid,
            expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    @mock.patch("magnum.common.policy.enforce")
    @mock.patch("magnum.common.context.make_context")
    def test_get_one_by_uuid_admin(self, mock_context, mock_policy):
        temp_uuid = uuidutils.generate_uuid()
        obj_utils.create_test_cluster(self.context, uuid=temp_uuid,
                                      project_id=temp_uuid)
        self.context.is_admin = True
        response = self.get_json(
            '/clusters/%s' % temp_uuid)
        self.assertEqual(temp_uuid, response['uuid'])

    def test_get_one_by_name_multiple_cluster(self):
        obj_utils.create_test_cluster(self.context, name='test_cluster',
                                      uuid=uuidutils.generate_uuid())
        obj_utils.create_test_cluster(self.context, name='test_cluster',
                                      uuid=uuidutils.generate_uuid())
        response = self.get_json('/clusters/test_cluster',
                                 expect_errors=True)
        self.assertEqual(409, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_get_all_with_pagination_marker(self):
        cluster_list = []
        for id_ in range(4):
            temp_uuid = uuidutils.generate_uuid()
            cluster = obj_utils.create_test_cluster(self.context, id=id_,
                                                    uuid=temp_uuid)
            cluster_list.append(cluster)

        response = self.get_json('/clusters?limit=3&marker=%s'
                                 % cluster_list[2].uuid)
        self.assertEqual(1, len(response['clusters']))
        self.assertEqual(cluster_list[-1].uuid,
                         response['clusters'][0]['uuid'])

    @mock.patch("magnum.common.policy.enforce")
    @mock.patch("magnum.common.context.make_context")
    @mock.patch("magnum.objects.Cluster.obj_load_attr")
    @mock.patch("magnum.objects.Cluster.cluster_template")
    def test_get_all_with_all_projects(self, mock_context, mock_policy,
                                       mock_load, mock_template):
        for id_ in range(4):
            temp_uuid = uuidutils.generate_uuid()
            obj_utils.create_test_cluster(self.context, id=id_,
                                          uuid=temp_uuid,
                                          project_id=id_)

        self.context.is_admin = True
        response = self.get_json('/clusters')
        self.assertEqual(4, len(response['clusters']))

    def test_detail(self):
        cluster = obj_utils.create_test_cluster(self.context)
        response = self.get_json('/clusters/detail')
        self.assertEqual(cluster.uuid, response['clusters'][0]["uuid"])
        self._verify_attrs(self._expand_cluster_attrs,
                           response['clusters'][0])

    def test_detail_with_pagination_marker(self):
        cluster_list = []
        for id_ in range(4):
            temp_uuid = uuidutils.generate_uuid()
            cluster = obj_utils.create_test_cluster(self.context, id=id_,
                                                    uuid=temp_uuid)
            cluster_list.append(cluster)

        response = self.get_json('/clusters/detail?limit=3&marker=%s'
                                 % cluster_list[2].uuid)
        self.assertEqual(1, len(response['clusters']))
        self.assertEqual(cluster_list[-1].uuid,
                         response['clusters'][0]['uuid'])
        self._verify_attrs(self._expand_cluster_attrs,
                           response['clusters'][0])

    def test_detail_against_single(self):
        cluster = obj_utils.create_test_cluster(self.context)
        response = self.get_json('/clusters/%s/detail' % cluster['uuid'],
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_many(self):
        bm_list = []
        for id_ in range(5):
            temp_uuid = uuidutils.generate_uuid()
            cluster = obj_utils.create_test_cluster(self.context, id=id_,
                                                    uuid=temp_uuid)
            bm_list.append(cluster.uuid)
        response = self.get_json('/clusters')
        self.assertEqual(len(bm_list), len(response['clusters']))
        uuids = [b['uuid'] for b in response['clusters']]
        self.assertEqual(sorted(bm_list), sorted(uuids))

    def test_links(self):
        uuid = uuidutils.generate_uuid()
        obj_utils.create_test_cluster(self.context, id=1, uuid=uuid)
        response = self.get_json('/clusters/%s' % uuid)
        self.assertIn('links', response.keys())
        self.assertEqual(2, len(response['links']))
        self.assertIn(uuid, response['links'][0]['href'])
        for link in response['links']:
            bookmark = link['rel'] == 'bookmark'
            self.assertTrue(self.validate_link(link['href'],
                                               bookmark=bookmark))

    def test_collection_links(self):
        for id_ in range(5):
            obj_utils.create_test_cluster(self.context, id=id_,
                                          uuid=uuidutils.generate_uuid())
        response = self.get_json('/clusters/?limit=3')
        self.assertEqual(3, len(response['clusters']))

        next_marker = response['clusters'][-1]['uuid']
        self.assertIn(next_marker, response['next'])

    def test_collection_links_default_limit(self):
        cfg.CONF.set_override('max_limit', 3, 'api')
        for id_ in range(5):
            obj_utils.create_test_cluster(self.context, id=id_,
                                          uuid=uuidutils.generate_uuid())
        response = self.get_json('/clusters')
        self.assertEqual(3, len(response['clusters']))

        next_marker = response['clusters'][-1]['uuid']
        self.assertIn(next_marker, response['next'])


class TestPatch(api_base.FunctionalTest):
    def setUp(self):
        super(TestPatch, self).setUp()
        self.cluster_template_obj = obj_utils.create_test_cluster_template(
            self.context)
        self.cluster_obj = obj_utils.create_test_cluster(
            self.context, name='cluster_example_A', node_count=3,
            health_status='UNKNOWN', health_status_reason={})
        p = mock.patch.object(rpcapi.API, 'cluster_update_async')
        self.mock_cluster_update = p.start()
        self.mock_cluster_update.side_effect = self._sim_rpc_cluster_update
        self.addCleanup(p.stop)

    def _sim_rpc_cluster_update(self, cluster, node_count, health_status,
                                health_status_reason, rollback=False):
        cluster.status = 'UPDATE_IN_PROGRESS'
        cluster.health_status = health_status
        cluster.health_status_reason = health_status_reason
        default_ng_worker = cluster.default_ng_worker
        default_ng_worker.node_count = node_count
        default_ng_worker.save()
        cluster.save()
        return cluster

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok(self, mock_utcnow):
        new_node_count = 4
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json('/clusters/%s' % self.cluster_obj.uuid,
                                   [{'path': '/node_count',
                                     'value': new_node_count,
                                     'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_code)

        response = self.get_json('/clusters/%s' % self.cluster_obj.uuid)
        self.assertEqual(new_node_count, response['node_count'])
        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)
        # Assert nothing else was changed
        self.assertEqual(self.cluster_obj.uuid, response['uuid'])
        self.assertEqual(self.cluster_obj.cluster_template_id,
                         response['cluster_template_id'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_health_status_ok(self, mock_utcnow):
        new_health_status = 'HEALTHY'
        new_health_status_reason = {'api': 'ok'}
        health_status_reason_dumps = jsonutils.dumps(new_health_status_reason)
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time
        old_node_count = self.cluster_obj.default_ng_worker.node_count
        db_utils.create_test_nodegroup(cluster_id=self.cluster_obj.uuid,
                                       name='non_default_ng')
        response = self.patch_json('/clusters/%s' % self.cluster_obj.uuid,
                                   [{'path': '/health_status',
                                     'value': new_health_status,
                                     'op': 'replace'},
                                    {'path': '/health_status_reason',
                                     'value': health_status_reason_dumps,
                                     'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_code)

        response = self.get_json('/clusters/%s' % self.cluster_obj.uuid)
        self.assertEqual(new_health_status, response['health_status'])
        self.assertEqual(new_health_status_reason,
                         response['health_status_reason'])

        new_node_count = self.cluster_obj.default_ng_worker.node_count
        self.assertEqual(old_node_count, new_node_count)

        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)
        # Assert nothing else was changed
        self.assertEqual(self.cluster_obj.uuid, response['uuid'])
        self.assertEqual(self.cluster_obj.cluster_template_id,
                         response['cluster_template_id'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_name(self, mock_utcnow):
        new_node_count = 4
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json('/clusters/%s' % self.cluster_obj.name,
                                   [{'path': '/node_count',
                                     'value': new_node_count,
                                     'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_code)

        response = self.get_json('/clusters/%s' % self.cluster_obj.uuid)
        self.assertEqual(new_node_count, response['node_count'])
        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)
        # Assert nothing else was changed
        self.assertEqual(self.cluster_obj.uuid, response['uuid'])
        self.assertEqual(self.cluster_obj.cluster_template_id,
                         response['cluster_template_id'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_name_not_found(self, mock_utcnow):
        name = 'not_found'
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json('/clusters/%s' % name,
                                   [{'path': '/name', 'value': name,
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(404, response.status_code)

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_uuid_not_found(self, mock_utcnow):
        uuid = uuidutils.generate_uuid()
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json('/clusters/%s' % uuid,
                                   [{'path': '/cluster_id', 'value': uuid,
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(404, response.status_code)

    def test_replace_cluster_template_id_failed(self):
        cluster_template = obj_utils.create_test_cluster_template(
            self.context,
            uuid=uuidutils.generate_uuid())
        response = self.patch_json('/clusters/%s' % self.cluster_obj.uuid,
                                   [{'path': '/cluster_template_id',
                                     'value': cluster_template.uuid,
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['errors'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_name_multiple_cluster(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        obj_utils.create_test_cluster(self.context, name='test_cluster',
                                      uuid=uuidutils.generate_uuid())
        obj_utils.create_test_cluster(self.context, name='test_cluster',
                                      uuid=uuidutils.generate_uuid())

        response = self.patch_json('/clusters/test_cluster',
                                   [{'path': '/name',
                                     'value': 'test_cluster',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(409, response.status_code)

    def test_replace_non_existent_cluster_template_id(self):
        response = self.patch_json('/clusters/%s' % self.cluster_obj.uuid,
                                   [{'path': '/cluster_template_id',
                                     'value': uuidutils.generate_uuid(),
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['errors'])

    def test_replace_invalid_node_count(self):
        response = self.patch_json('/clusters/%s' % self.cluster_obj.uuid,
                                   [{'path': '/node_count', 'value': -1,
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['errors'])

    def test_replace_non_existent_cluster(self):
        response = self.patch_json('/clusters/%s' %
                                   uuidutils.generate_uuid(),
                                   [{'path': '/name',
                                     'value': 'cluster_example_B',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_replace_cluster_name_failed(self):
        response = self.patch_json('/clusters/%s' % self.cluster_obj.uuid,
                                   [{'path': '/name',
                                     'value': 'cluster_example_B',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_add_non_existent_property(self):
        response = self.patch_json(
            '/clusters/%s' % self.cluster_obj.uuid,
            [{'path': '/foo', 'value': 'bar', 'op': 'add'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_update_cluster_with_rollback_enabled(self):
        node_count = 4
        response = self.patch_json(
            '/clusters/%s/?rollback=True' % self.cluster_obj.uuid,
            [{'path': '/node_count', 'value': node_count,
              'op': 'replace'}],
            headers={'OpenStack-API-Version': 'container-infra 1.3',
                     "X-Roles": "member"
                     })

        self.mock_cluster_update.assert_called_once_with(
            mock.ANY, node_count, self.cluster_obj.health_status,
            self.cluster_obj.health_status_reason, True)
        self.assertEqual(202, response.status_code)

    def test_update_cluster_with_rollback_disabled(self):
        node_count = 4
        response = self.patch_json(
            '/clusters/%s/?rollback=False' % self.cluster_obj.uuid,
            [{'path': '/node_count', 'value': node_count,
              'op': 'replace'}],
            headers={'OpenStack-API-Version': 'container-infra 1.3',
                     "X-Roles": "member"
                     })

        self.mock_cluster_update.assert_called_once_with(
            mock.ANY, node_count, self.cluster_obj.health_status,
            self.cluster_obj.health_status_reason, False)
        self.assertEqual(202, response.status_code)

    def test_update_cluster_with_zero_node_count_fail(self):
        node_count = 0
        response = self.patch_json(
            '/clusters/%s' % self.cluster_obj.uuid,
            [{'path': '/node_count', 'value': node_count,
              'op': 'replace'}],
            headers={'OpenStack-API-Version': 'container-infra 1.9',
                     "X-Roles": "member"
                     },
            expect_errors=True)

        self.assertEqual(400, response.status_code)

    def test_update_cluster_with_zero_node_count(self):
        node_count = 0
        response = self.patch_json(
            '/clusters/%s' % self.cluster_obj.uuid,
            [{'path': '/node_count', 'value': node_count,
              'op': 'replace'}],
            headers={'OpenStack-API-Version': 'container-infra 1.10',
                     "X-Roles": "member"
                     })

        self.mock_cluster_update.assert_called_once_with(
            mock.ANY, node_count, self.cluster_obj.health_status,
            self.cluster_obj.health_status_reason, False)
        self.assertEqual(202, response.status_code)

    def test_remove_ok(self):
        response = self.get_json('/clusters/%s' % self.cluster_obj.uuid)
        self.assertIsNotNone(response['name'])

        response = self.patch_json('/clusters/%s' % self.cluster_obj.uuid,
                                   [{'path': '/node_count',
                                     'op': 'remove'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_code)

        response = self.get_json('/clusters/%s' % self.cluster_obj.uuid)
        # only allow node_count for cluster, and default value is 1
        self.assertEqual(1, response['node_count'])
        # Assert nothing else was changed
        self.assertEqual(self.cluster_obj.uuid, response['uuid'])
        self.assertEqual(self.cluster_obj.cluster_template_id,
                         response['cluster_template_id'])
        self.assertEqual(self.cluster_obj.name, response['name'])
        self.assertEqual(self.cluster_obj.master_count,
                         response['master_count'])

    def test_remove_mandatory_property_fail(self):
        mandatory_properties = ('/uuid', '/cluster_template_id')
        for p in mandatory_properties:
            response = self.patch_json('/clusters/%s' % self.cluster_obj.uuid,
                                       [{'path': p, 'op': 'remove'}],
                                       expect_errors=True)
            self.assertEqual(400, response.status_int)
            self.assertEqual('application/json', response.content_type)
            self.assertTrue(response.json['errors'])

    def test_remove_non_existent_property(self):
        response = self.patch_json(
            '/clusters/%s' % self.cluster_obj.uuid,
            [{'path': '/non-existent', 'op': 'remove'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['errors'])

    @mock.patch("magnum.common.policy.enforce")
    @mock.patch("magnum.common.context.make_context")
    def test_update_cluster_as_admin(self, mock_context, mock_policy):
        temp_uuid = uuidutils.generate_uuid()
        obj_utils.create_test_cluster(self.context, uuid=temp_uuid)
        self.context.is_admin = True
        response = self.patch_json('/clusters/%s' % temp_uuid,
                                   [{'path': '/node_count',
                                     'value': 4,
                                     'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_code)


class TestPost(api_base.FunctionalTest):
    def setUp(self):
        super(TestPost, self).setUp()
        self.cluster_template = obj_utils.create_test_cluster_template(
            self.context)
        p = mock.patch.object(rpcapi.API, 'cluster_create_async')
        self.mock_cluster_create = p.start()
        self.mock_cluster_create.side_effect = self._simulate_cluster_create
        self.addCleanup(p.stop)
        p = mock.patch.object(attr_validator, 'validate_os_resources')
        self.mock_valid_os_res = p.start()
        self.addCleanup(p.stop)

    def _simulate_cluster_create(self, cluster, master_count, node_count,
                                 create_timeout):
        cluster.create()
        return cluster

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_cluster(self, mock_utcnow):
        bdict = apiutils.cluster_post_data()
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        self.assertTrue(uuidutils.is_uuid_like(response.json['uuid']))

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_cluster_resource_limit_reached(self, mock_utcnow):
        # override max_cluster_per_project to 1
        CONF.set_override('max_clusters_per_project', 1, group='quotas')

        bdict = apiutils.cluster_post_data()
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        # create first cluster
        response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        self.assertTrue(uuidutils.is_uuid_like(response.json['uuid']))

        # now try to create second cluster and make sure it fails
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(403, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_set_project_id_and_user_id(self):
        bdict = apiutils.cluster_post_data()

        def _simulate_rpc_cluster_create(cluster, master_count, node_count,
                                         create_timeout):
            self.assertEqual(self.context.project_id, cluster.project_id)
            self.assertEqual(self.context.user_id, cluster.user_id)
            cluster.create()
            return cluster

        self.mock_cluster_create.side_effect = _simulate_rpc_cluster_create

        self.post_json('/clusters', bdict)

    def test_create_cluster_doesnt_contain_id(self):
        with mock.patch.object(self.dbapi, 'create_cluster',
                               wraps=self.dbapi.create_cluster) as cc_mock:
            bdict = apiutils.cluster_post_data(name='cluster_example_A')
            response = self.post_json('/clusters', bdict)
            cc_mock.assert_called_once_with(mock.ANY)
            # Check that 'id' is not in first arg of positional args
            self.assertNotIn('id', cc_mock.call_args[0][0])
            self.assertTrue(uuidutils.is_uuid_like(response.json['uuid']))

    def test_create_cluster_generate_uuid(self):
        bdict = apiutils.cluster_post_data()
        del bdict['uuid']

        response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        self.assertTrue(uuidutils.is_uuid_like(response.json['uuid']))

    def test_create_cluster_no_cluster_template_id(self):
        bdict = apiutils.cluster_post_data()
        del bdict['cluster_template_id']
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)

    def test_create_cluster_with_non_existent_cluster_template_id(self):
        temp_uuid = uuidutils.generate_uuid()
        bdict = apiutils.cluster_post_data(cluster_template_id=temp_uuid)
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_with_non_existent_cluster_template_name(self):
        modelname = 'notfound'
        bdict = apiutils.cluster_post_data(cluster_template_id=modelname)
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_with_cluster_template_name(self):
        modelname = self.cluster_template.name
        bdict = apiutils.cluster_post_data(name=modelname)
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_zero_node_count_fail(self):
        bdict = apiutils.cluster_post_data()
        bdict['node_count'] = 0
        response = self.post_json(
            '/clusters', bdict, expect_errors=True,
            headers={
                "Openstack-Api-Version": "container-infra 1.9",
                "X-Roles": "member"
            })
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)

    def test_create_cluster_with_zero_node_count(self):
        bdict = apiutils.cluster_post_data()
        bdict['node_count'] = 0
        response = self.post_json(
            '/clusters', bdict,
            headers={
                "Openstack-Api-Version": "container-infra 1.10",
                "X-Roles": "member"
            })
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_node_count_negative(self):
        bdict = apiutils.cluster_post_data()
        bdict['node_count'] = -1
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_with_no_node_count(self):
        bdict = apiutils.cluster_post_data()
        del bdict['node_count']
        response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_master_count_zero(self):
        bdict = apiutils.cluster_post_data()
        bdict['master_count'] = 0
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_with_no_master_count(self):
        bdict = apiutils.cluster_post_data()
        del bdict['master_count']
        response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_even_master_count_oldmicroversion(self):
        bdict = apiutils.cluster_post_data()
        bdict['master_count'] = 2
        response = self.post_json(
            '/clusters',
            bdict,
            expect_errors=True,
            headers={"Openstack-Api-Version": "container-infra 1.9"}
        )
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_with_even_master_count(self):
        bdict = apiutils.cluster_post_data()
        bdict['master_count'] = 2
        response = self.post_json(
            '/clusters',
            bdict,
            expect_errors=True,
            headers={"Openstack-Api-Version": "container-infra 1.10"}
        )
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_with_negative_master_count(self):
        bdict = apiutils.cluster_post_data()
        bdict['master_count'] = -1
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_with_invalid_name(self):
        invalid_names = ['x' * 243, '123456', '123456test_cluster',
                         '-test_cluster', '.test_cluster', '_test_cluster', '']
        for value in invalid_names:
            bdict = apiutils.cluster_post_data(name=value)
            response = self.post_json('/clusters', bdict, expect_errors=True)
            self.assertEqual('application/json', response.content_type)
            self.assertEqual(400, response.status_int)
            self.assertTrue(response.json['errors'])

    def test_create_cluster_with_valid_name(self):
        valid_names = ['test_cluster123456', 'test-cluster', 'test.cluster',
                       'testcluster.', 'testcluster-', 'testcluster_',
                       'test.-_cluster', 'Testcluster']
        for value in valid_names:
            bdict = apiutils.cluster_post_data(name=value)
            response = self.post_json('/clusters', bdict, expect_errors=True)
            self.assertEqual('application/json', response.content_type)
            self.assertEqual(202, response.status_int)

    def test_create_cluster_without_name(self):
        bdict = apiutils.cluster_post_data()
        del bdict['name']
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_timeout_none(self):
        bdict = apiutils.cluster_post_data()
        bdict['create_timeout'] = None
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_no_timeout(self):
        def _simulate_rpc_cluster_create(cluster, master_count, node_count,
                                         create_timeout):
            self.assertEqual(60, create_timeout)
            cluster.create()
            return cluster

        self.mock_cluster_create.side_effect = _simulate_rpc_cluster_create
        bdict = apiutils.cluster_post_data()
        del bdict['create_timeout']
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_timeout_negative(self):
        bdict = apiutils.cluster_post_data()
        bdict['create_timeout'] = -1
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_with_timeout_zero(self):
        bdict = apiutils.cluster_post_data()
        bdict['create_timeout'] = 0
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_invalid_flavor(self):
        bdict = apiutils.cluster_post_data()
        self.mock_valid_os_res.side_effect = exception.FlavorNotFound(
            'test-flavor')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(self.mock_valid_os_res.called)
        self.assertEqual(400, response.status_int)

    def test_create_cluster_with_invalid_ext_network(self):
        bdict = apiutils.cluster_post_data()
        self.mock_valid_os_res.side_effect = \
            exception.ExternalNetworkNotFound('test-net')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(self.mock_valid_os_res.called)
        self.assertEqual(400, response.status_int)

    def test_create_cluster_with_invalid_keypair(self):
        bdict = apiutils.cluster_post_data()
        self.mock_valid_os_res.side_effect = exception.KeyPairNotFound(
            'test-key')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(self.mock_valid_os_res.called)
        self.assertEqual(404, response.status_int)

    def test_create_cluster_with_nonexist_image(self):
        bdict = apiutils.cluster_post_data()
        self.mock_valid_os_res.side_effect = exception.ImageNotFound(
            'test-img')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(self.mock_valid_os_res.called)
        self.assertEqual(400, response.status_int)

    def test_create_cluster_with_multi_images_same_name(self):
        bdict = apiutils.cluster_post_data()
        self.mock_valid_os_res.side_effect = exception.Conflict('test-img')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(self.mock_valid_os_res.called)
        self.assertEqual(409, response.status_int)

    def test_create_cluster_with_no_os_distro_image(self):
        bdict = apiutils.cluster_post_data()
        self.mock_valid_os_res.side_effect = \
            exception.OSDistroFieldNotFound('img')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(self.mock_valid_os_res.called)
        self.assertEqual(400, response.status_int)

    def test_create_cluster_with_no_lb_one_node(self):
        cluster_template = obj_utils.create_test_cluster_template(
            self.context, name='foo', uuid='foo', master_lb_enabled=False)
        bdict = apiutils.cluster_post_data(
            cluster_template_id=cluster_template.name, master_count=1)
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_no_lb_multi_node(self):
        cluster_template = obj_utils.create_test_cluster_template(
            self.context, name='foo', uuid='foo', master_lb_enabled=False)
        bdict = apiutils.cluster_post_data(
            cluster_template_id=cluster_template.name, master_count=3,
            master_lb_enabled=False)
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)

    def test_create_cluster_with_keypair(self):
        bdict = apiutils.cluster_post_data()
        bdict['keypair'] = 'keypair2'
        response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        cluster, timeout = self.mock_cluster_create.call_args
        self.assertEqual('keypair2', cluster[0].keypair)

    def test_create_cluster_without_keypair(self):
        bdict = apiutils.cluster_post_data()
        response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        cluster, timeout = self.mock_cluster_create.call_args
        # Verify keypair from ClusterTemplate is used
        self.assertEqual('keypair1', cluster[0].keypair)

    def test_create_cluster_with_multi_keypair_same_name(self):
        bdict = apiutils.cluster_post_data()
        self.mock_valid_os_res.side_effect = exception.Conflict('keypair2')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(self.mock_valid_os_res.called)
        self.assertEqual(409, response.status_int)

    def test_create_cluster_with_docker_volume_size(self):
        bdict = apiutils.cluster_post_data()
        bdict['docker_volume_size'] = 3
        response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        cluster, timeout = self.mock_cluster_create.call_args
        self.assertEqual(3, cluster[0].docker_volume_size)

    def test_create_cluster_with_labels(self):
        bdict = apiutils.cluster_post_data()
        bdict['labels'] = {'key': 'value'}
        response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        cluster, timeout = self.mock_cluster_create.call_args
        self.assertEqual({'key': 'value'}, cluster[0].labels)

    def test_create_cluster_without_docker_volume_size(self):
        bdict = apiutils.cluster_post_data()
        # Remove the default docker_volume_size from the cluster dict.
        del bdict['docker_volume_size']
        response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        cluster, timeout = self.mock_cluster_create.call_args
        # Verify docker_volume_size from ClusterTemplate is used
        self.assertEqual(20, cluster[0].docker_volume_size)

    def test_create_cluster_without_labels(self):
        bdict = apiutils.cluster_post_data()
        bdict.pop('labels')
        response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        cluster, timeout = self.mock_cluster_create.call_args
        # Verify labels from ClusterTemplate is used
        self.assertEqual({'key1': u'val1', 'key2': u'val2'}, cluster[0].labels)

    def test_create_cluster_with_invalid_docker_volume_size(self):
        invalid_values = [(-1, None), ('notanint', None),
                          (1, 'devicemapper'), (2, 'devicemapper')]
        for value in invalid_values:
            bdict = apiutils.cluster_post_data(docker_volume_size=value[0],
                                               docker_storage_driver=value[1])
            response = self.post_json('/clusters', bdict, expect_errors=True)
            self.assertEqual('application/json', response.content_type)
            self.assertEqual(400, response.status_int)
            self.assertTrue(response.json['errors'])

    def test_create_cluster_with_invalid_labels(self):
        bdict = apiutils.cluster_post_data(labels='invalid')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_with_master_flavor_id(self):
        bdict = apiutils.cluster_post_data()
        bdict['master_flavor_id'] = 'm2.small'
        response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        cluster, timeout = self.mock_cluster_create.call_args
        self.assertEqual('m2.small', cluster[0].master_flavor_id)

    def test_create_cluster_without_master_flavor_id(self):
        bdict = apiutils.cluster_post_data()
        response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        cluster, timeout = self.mock_cluster_create.call_args
        # Verify master_flavor_id from ClusterTemplate is used
        self.assertEqual('m1.small', cluster[0].master_flavor_id)

    def test_create_cluster_with_flavor_id(self):
        bdict = apiutils.cluster_post_data()
        bdict['flavor_id'] = 'm2.small'
        response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        cluster, timeout = self.mock_cluster_create.call_args
        self.assertEqual('m2.small', cluster[0].flavor_id)

    def test_create_cluster_without_flavor_id(self):
        bdict = apiutils.cluster_post_data()
        response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        cluster, timeout = self.mock_cluster_create.call_args
        # Verify flavor_id from ClusterTemplate is used
        self.assertEqual('m1.small', cluster[0].flavor_id)

    def test_create_cluster_with_cinder_csi_disabled(self):
        self.cluster_template.volume_driver = 'cinder'
        self.cluster_template.save()
        cluster_labels = {'cinder_csi_enabled': 'false'}
        bdict = apiutils.cluster_post_data(labels=cluster_labels)
        note = 'in-tree Cinder volume driver is deprecated'
        with self.assertWarnsRegex(DeprecationWarning, note):
            response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_without_merge_labels(self):
        self.cluster_template.labels = {'label1': 'value1', 'label2': 'value2'}
        self.cluster_template.save()
        cluster_labels = {'label2': 'value3', 'label4': 'value4'}
        bdict = apiutils.cluster_post_data(labels=cluster_labels)
        response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        cluster, timeout = self.mock_cluster_create.call_args
        self.assertEqual(cluster_labels, cluster[0].labels)

    def test_create_cluster_with_merge_labels(self):
        self.cluster_template.labels = {'label1': 'value1', 'label2': 'value2'}
        self.cluster_template.save()
        cluster_labels = {'label2': 'value3', 'label4': 'value4'}
        bdict = apiutils.cluster_post_data(labels=cluster_labels,
                                           merge_labels=True)
        response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        cluster, timeout = self.mock_cluster_create.call_args
        expected = self.cluster_template.labels
        expected.update(cluster_labels)
        self.assertEqual(expected, cluster[0].labels)

    def test_create_cluster_with_merge_labels_no_labels(self):
        self.cluster_template.labels = {'label1': 'value1', 'label2': 'value2'}
        self.cluster_template.save()
        bdict = apiutils.cluster_post_data(merge_labels=True)
        del bdict['labels']
        response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        cluster, timeout = self.mock_cluster_create.call_args
        self.assertEqual(self.cluster_template.labels, cluster[0].labels)


class TestDelete(api_base.FunctionalTest):
    def setUp(self):
        super(TestDelete, self).setUp()
        self.cluster_template = obj_utils.create_test_cluster_template(
            self.context)
        self.cluster = obj_utils.create_test_cluster(self.context)
        p = mock.patch.object(rpcapi.API, 'cluster_delete_async')
        self.mock_cluster_delete = p.start()
        self.mock_cluster_delete.side_effect = self._simulate_cluster_delete
        self.addCleanup(p.stop)

    def _simulate_cluster_delete(self, cluster_uuid):
        cluster = objects.Cluster.get_by_uuid(self.context, cluster_uuid)
        cluster.destroy()

    def test_delete_cluster(self):
        self.delete('/clusters/%s' % self.cluster.uuid)
        response = self.get_json('/clusters/%s' % self.cluster.uuid,
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_delete_cluster_not_found(self):
        uuid = uuidutils.generate_uuid()
        response = self.delete('/clusters/%s' % uuid, expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_delete_cluster_with_name_not_found(self):
        response = self.delete('/clusters/not_found', expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_delete_cluster_with_name(self):
        response = self.delete('/clusters/%s' % self.cluster.name,
                               expect_errors=True)
        self.assertEqual(204, response.status_int)

    def test_delete_multiple_cluster_by_name(self):
        obj_utils.create_test_cluster(self.context, name='test_cluster',
                                      uuid=uuidutils.generate_uuid())
        obj_utils.create_test_cluster(self.context, name='test_cluster',
                                      uuid=uuidutils.generate_uuid())
        response = self.delete('/clusters/test_cluster', expect_errors=True)
        self.assertEqual(409, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    @mock.patch("magnum.common.policy.enforce")
    @mock.patch("magnum.common.context.make_context")
    def test_delete_cluster_as_admin(self, mock_context, mock_policy):
        temp_uuid = uuidutils.generate_uuid()
        obj_utils.create_test_cluster(self.context, uuid=temp_uuid)
        self.context.is_admin = True
        response = self.delete('/clusters/%s' % temp_uuid,
                               expect_errors=True)
        self.assertEqual(204, response.status_int)


class TestClusterPolicyEnforcement(api_base.FunctionalTest):
    def setUp(self):
        super(TestClusterPolicyEnforcement, self).setUp()
        obj_utils.create_test_cluster_template(self.context)

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
            "cluster:get_all", self.get_json, '/clusters', expect_errors=True)

    def test_policy_disallow_get_one(self):
        self.cluster = obj_utils.create_test_cluster(self.context)
        self._common_policy_check(
            "cluster:get", self.get_json, '/clusters/%s' % self.cluster.uuid,
            expect_errors=True)

    def test_policy_disallow_detail(self):
        self._common_policy_check(
            "cluster:detail", self.get_json,
            '/clusters/%s/detail' % uuidutils.generate_uuid(),
            expect_errors=True)

    def test_policy_disallow_update(self):
        self.cluster = obj_utils.create_test_cluster(self.context,
                                                     name='cluster_example_A',
                                                     node_count=3)
        self._common_policy_check(
            "cluster:update", self.patch_json, '/clusters/%s' %
                                               self.cluster.name,
            [{'path': '/name', 'value': "new_name", 'op': 'replace'}],
            expect_errors=True)

    def test_policy_disallow_create(self):
        bdict = apiutils.cluster_post_data(name='cluster_example_A')
        self._common_policy_check(
            "cluster:create", self.post_json, '/clusters', bdict,
            expect_errors=True)

    def _simulate_cluster_delete(self, cluster_uuid):
        cluster = objects.Cluster.get_by_uuid(self.context, cluster_uuid)
        cluster.destroy()
        ngs = objects.NodeGroup.list(self.context, cluster_uuid)
        for ng in ngs:
            ng.destroy()

    def test_policy_disallow_delete(self):
        p = mock.patch.object(rpcapi.API, 'cluster_delete')
        self.mock_cluster_delete = p.start()
        self.mock_cluster_delete.side_effect = self._simulate_cluster_delete
        self.addCleanup(p.stop)
        self.cluster = obj_utils.create_test_cluster(self.context)
        self._common_policy_check(
            "cluster:delete", self.delete, '/clusters/%s' %
                                           self.cluster.uuid,
            expect_errors=True)

    def _owner_check(self, rule, func, *args, **kwargs):
        self.policy.set_rules({rule: "user_id:%(user_id)s"})
        response = func(*args, **kwargs)
        self.assertEqual(403, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(
            "Policy doesn't allow %s to be performed." % rule,
            response.json['errors'][0]['detail'])

    def test_policy_only_owner_get_one(self):
        cluster = obj_utils.create_test_cluster(self.context,
                                                user_id='another')
        self._owner_check("cluster:get", self.get_json,
                          '/clusters/%s' % cluster.uuid,
                          expect_errors=True)

    def test_policy_only_owner_update(self):
        cluster = obj_utils.create_test_cluster(self.context,
                                                user_id='another')
        self._owner_check(
            "cluster:update", self.patch_json,
            '/clusters/%s' % cluster.uuid,
            [{'path': '/name', 'value': "new_name", 'op': 'replace'}],
            expect_errors=True)

    def test_policy_only_owner_delete(self):
        cluster = obj_utils.create_test_cluster(self.context,
                                                user_id='another')
        self._owner_check("cluster:delete", self.delete,
                          '/clusters/%s' % cluster.uuid,
                          expect_errors=True)
