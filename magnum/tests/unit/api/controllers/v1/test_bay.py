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
from oslo_utils import timeutils
from oslo_utils import uuidutils
from wsme import types as wtypes

from magnum.api import attr_validator
from magnum.api.controllers.v1 import bay as api_bay
from magnum.common import exception
from magnum.conductor import api as rpcapi
from magnum import objects
from magnum.tests import base
from magnum.tests.unit.api import base as api_base
from magnum.tests.unit.api import utils as apiutils
from magnum.tests.unit.db import utils as db_utils
from magnum.tests.unit.objects import utils as obj_utils


class TestBayObject(base.TestCase):

    def test_bay_init(self):
        bay_dict = apiutils.bay_post_data(baymodel_id=None)
        del bay_dict['node_count']
        del bay_dict['master_count']
        del bay_dict['bay_create_timeout']
        bay = api_bay.Bay(**bay_dict)
        self.assertEqual(1, bay.node_count)
        self.assertEqual(1, bay.master_count)
        self.assertEqual(60, bay.bay_create_timeout)

        # test unset value for baymodel_id
        bay.baymodel_id = wtypes.Unset
        self.assertEqual(wtypes.Unset, bay.baymodel_id)

        # test backwards compatibility of bay fields with new objects
        bay_dict['bay_create_timeout'] = 15
        bay_dict['bay_faults'] = {'testfault': 'fault'}
        bay = api_bay.Bay(**bay_dict)
        self.assertEqual(15, bay.bay_create_timeout)
        self.assertEqual(15, bay.create_timeout)
        self.assertIn('testfault', bay.bay_faults)
        self.assertIn('testfault', bay.faults)

    def test_as_dict_faults(self):
        bay_dict = apiutils.bay_post_data(baymodel_id=None)
        del bay_dict['node_count']
        del bay_dict['master_count']
        del bay_dict['bay_create_timeout']
        bay = api_bay.Bay(**bay_dict)
        bay.bay_faults = {'testfault': 'fault'}
        dict = bay.as_dict()
        self.assertEqual({'testfault': 'fault'}, dict['faults'])


class TestListBay(api_base.FunctionalTest):

    _bay_attrs = ("name", "baymodel_id", "node_count", "status",
                  "master_count", "stack_id", "bay_create_timeout")

    _expand_bay_attrs = ("name", "baymodel_id", "node_count", "status",
                         "api_address", "discovery_url", "node_addresses",
                         "master_count", "master_addresses", "stack_id",
                         "bay_create_timeout", "status_reason")

    def setUp(self):
        super(TestListBay, self).setUp()
        obj_utils.create_test_cluster_template(self.context)

    def test_empty(self):
        response = self.get_json('/bays')
        self.assertEqual([], response['bays'])

    def test_one(self):
        bay = obj_utils.create_test_cluster(self.context)
        response = self.get_json('/bays')
        self.assertEqual(bay.uuid, response['bays'][0]["uuid"])
        self._verify_attrs(self._bay_attrs, response['bays'][0])

        # Verify atts that should not appear from bay's get_all response
        none_attrs = set(self._expand_bay_attrs) - set(self._bay_attrs)
        self._verify_attrs(none_attrs, response['bays'][0], positive=False)

    def test_get_one(self):
        bay = obj_utils.create_test_cluster(self.context)
        response = self.get_json('/bays/%s' % bay['uuid'])
        self.assertEqual(bay.uuid, response['uuid'])
        self._verify_attrs(self._expand_bay_attrs, response)

    @mock.patch('magnum.common.clients.OpenStackClients.heat')
    def test_get_one_failed_bay(self, mock_heat):
        fake_resources = mock.MagicMock()
        fake_resources.resource_name = 'fake_name'
        fake_resources.resource_status_reason = 'fake_reason'

        ht = mock.MagicMock()
        ht.resources.list.return_value = [fake_resources]
        mock_heat.return_value = ht

        bay = obj_utils.create_test_cluster(self.context,
                                            status='CREATE_FAILED')
        response = self.get_json('/bays/%s' % bay['uuid'])
        self.assertEqual(bay.uuid, response['uuid'])
        self.assertEqual({'fake_name': 'fake_reason'}, response['bay_faults'])

    @mock.patch('magnum.common.clients.OpenStackClients.heat')
    def test_get_one_failed_bay_heatclient_exception(self, mock_heat):
        mock_heat.resources.list.side_effect = Exception('fake')
        bay = obj_utils.create_test_cluster(self.context,
                                            status='CREATE_FAILED')
        response = self.get_json('/bays/%s' % bay['uuid'])
        self.assertEqual(bay.uuid, response['uuid'])
        self.assertEqual({}, response['bay_faults'])

    def test_get_one_by_name(self):
        bay = obj_utils.create_test_cluster(self.context)
        response = self.get_json('/bays/%s' % bay['name'])
        self.assertEqual(bay.uuid, response['uuid'])
        self._verify_attrs(self._expand_bay_attrs, response)

    def test_get_one_by_name_not_found(self):
        response = self.get_json(
            '/bays/not_found',
            expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_get_one_by_name_multiple_bay(self):
        obj_utils.create_test_cluster(self.context, name='test_bay',
                                      uuid=uuidutils.generate_uuid())
        obj_utils.create_test_cluster(self.context, name='test_bay',
                                      uuid=uuidutils.generate_uuid())
        response = self.get_json('/bays/test_bay', expect_errors=True)
        self.assertEqual(409, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_get_all_with_pagination_marker(self):
        bay_list = []
        for id_ in range(4):
            bay = obj_utils.create_test_cluster(self.context, id=id_,
                                                uuid=uuidutils.generate_uuid())
            bay_list.append(bay)

        response = self.get_json('/bays?limit=3&marker=%s'
                                 % bay_list[2].uuid)
        self.assertEqual(1, len(response['bays']))
        self.assertEqual(bay_list[-1].uuid, response['bays'][0]['uuid'])

    def test_detail(self):
        bay = obj_utils.create_test_cluster(self.context)
        response = self.get_json('/bays/detail')
        self.assertEqual(bay.uuid, response['bays'][0]["uuid"])
        self._verify_attrs(self._expand_bay_attrs, response['bays'][0])

    def test_detail_with_pagination_marker(self):
        bay_list = []
        for id_ in range(4):
            bay = obj_utils.create_test_cluster(self.context, id=id_,
                                                uuid=uuidutils.generate_uuid())
            bay_list.append(bay)

        response = self.get_json('/bays/detail?limit=3&marker=%s'
                                 % bay_list[2].uuid)
        self.assertEqual(1, len(response['bays']))
        self.assertEqual(bay_list[-1].uuid, response['bays'][0]['uuid'])
        self._verify_attrs(self._expand_bay_attrs, response['bays'][0])

    def test_detail_against_single(self):
        bay = obj_utils.create_test_cluster(self.context)
        response = self.get_json('/bays/%s/detail' % bay['uuid'],
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_many(self):
        bm_list = []
        for id_ in range(5):
            bay = obj_utils.create_test_cluster(self.context, id=id_,
                                                uuid=uuidutils.generate_uuid())
            bm_list.append(bay.uuid)
        response = self.get_json('/bays')
        self.assertEqual(len(bm_list), len(response['bays']))
        uuids = [b['uuid'] for b in response['bays']]
        self.assertEqual(sorted(bm_list), sorted(uuids))

    def test_links(self):
        uuid = uuidutils.generate_uuid()
        obj_utils.create_test_cluster(self.context, id=1, uuid=uuid)
        response = self.get_json('/bays/%s' % uuid)
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
        response = self.get_json('/bays/?limit=3')
        self.assertEqual(3, len(response['bays']))

        next_marker = response['bays'][-1]['uuid']
        self.assertIn(next_marker, response['next'])

    def test_collection_links_default_limit(self):
        cfg.CONF.set_override('max_limit', 3, 'api')
        for id_ in range(5):
            obj_utils.create_test_cluster(self.context, id=id_,
                                          uuid=uuidutils.generate_uuid())
        response = self.get_json('/bays')
        self.assertEqual(3, len(response['bays']))

        next_marker = response['bays'][-1]['uuid']
        self.assertIn(next_marker, response['next'])


class TestPatch(api_base.FunctionalTest):

    def setUp(self):
        super(TestPatch, self).setUp()
        self.cluster_template = obj_utils.create_test_cluster_template(
            self.context)
        self.bay = obj_utils.create_test_cluster(self.context,
                                                 name='bay_example_A',
                                                 node_count=3)
        p = mock.patch.object(rpcapi.API, 'cluster_update')
        self.mock_bay_update = p.start()
        self.mock_bay_update.side_effect = self._simulate_rpc_bay_update
        self.addCleanup(p.stop)

    def _simulate_rpc_bay_update(self, bay, node_count, rollback=False):
        bay.status = 'UPDATE_IN_PROGRESS'
        bay.save()
        default_ng_worker = bay.default_ng_worker
        default_ng_worker.node_count = node_count
        default_ng_worker.save()
        return bay

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok(self, mock_utcnow):
        new_node_count = 4
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json('/bays/%s' % self.bay.uuid,
                                   [{'path': '/node_count',
                                     'value': new_node_count,
                                     'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json('/bays/%s' % self.bay.uuid)
        self.assertEqual(new_node_count, response['node_count'])
        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)
        # Assert nothing else was changed
        self.assertEqual(self.bay.uuid, response['uuid'])
        self.assertEqual(self.bay.cluster_template_id, response['baymodel_id'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_name(self, mock_utcnow):
        new_node_count = 4
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json('/bays/%s' % self.bay.name,
                                   [{'path': '/node_count',
                                     'value': new_node_count,
                                     'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json('/bays/%s' % self.bay.uuid)
        self.assertEqual(new_node_count, response['node_count'])
        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)
        # Assert nothing else was changed
        self.assertEqual(self.bay.uuid, response['uuid'])
        self.assertEqual(self.bay.cluster_template_id, response['baymodel_id'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_name_not_found(self, mock_utcnow):
        name = 'not_found'
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json('/bays/%s' % name,
                                   [{'path': '/name', 'value': name,
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(404, response.status_code)

    def test_replace_baymodel_id_failed(self):
        cluster_template = obj_utils.create_test_cluster_template(
            self.context,
            uuid=uuidutils.generate_uuid())
        response = self.patch_json('/bays/%s' % self.bay.uuid,
                                   [{'path': '/baymodel_id',
                                     'value': cluster_template.uuid,
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['errors'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_name_multiple_bay(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        obj_utils.create_test_cluster(self.context, name='test_bay',
                                      uuid=uuidutils.generate_uuid())
        obj_utils.create_test_cluster(self.context, name='test_bay',
                                      uuid=uuidutils.generate_uuid())

        response = self.patch_json('/bays/test_bay',
                                   [{'path': '/name', 'value': 'test_bay',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(409, response.status_code)

    def test_replace_non_existent_baymodel_id(self):
        response = self.patch_json('/bays/%s' % self.bay.uuid,
                                   [{'path': '/baymodel_id',
                                     'value': uuidutils.generate_uuid(),
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['errors'])

    def test_replace_invalid_node_count(self):
        response = self.patch_json('/bays/%s' % self.bay.uuid,
                                   [{'path': '/node_count', 'value': -1,
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['errors'])

    def test_replace_non_existent_bay(self):
        response = self.patch_json('/bays/%s' % uuidutils.generate_uuid(),
                                   [{'path': '/name',
                                     'value': 'bay_example_B',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_replace_bay_name_failed(self):
        response = self.patch_json('/bays/%s' % self.bay.uuid,
                                   [{'path': '/name',
                                     'value': 'bay_example_B',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_add_non_existent_property(self):
        response = self.patch_json(
            '/bays/%s' % self.bay.uuid,
            [{'path': '/foo', 'value': 'bar', 'op': 'add'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    @mock.patch.object(rpcapi.API, 'cluster_update_async')
    def test_update_bay_async(self, mock_update):
        response = self.patch_json(
            '/bays/%s' % self.bay.name,
            [{'path': '/node_count', 'value': 4,
              'op': 'replace'}],
            headers={'OpenStack-API-Version': 'container-infra 1.2'})

        self.assertEqual(202, response.status_code)

    @mock.patch.object(rpcapi.API, 'cluster_update_async')
    def test_update_bay_with_rollback_enabled(self, mock_update):
        node_count = 4
        response = self.patch_json(
            '/bays/%s/?rollback=True' % self.bay.name,
            [{'path': '/node_count', 'value': node_count,
              'op': 'replace'}],
            headers={'OpenStack-API-Version': 'container-infra 1.3'})

        mock_update.assert_called_once_with(mock.ANY, node_count,
                                            rollback=True)
        self.assertEqual(202, response.status_code)

    def test_remove_ok(self):
        response = self.get_json('/bays/%s' % self.bay.uuid)
        self.assertIsNotNone(response['name'])

        response = self.patch_json('/bays/%s' % self.bay.uuid,
                                   [{'path': '/node_count', 'op': 'remove'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json('/bays/%s' % self.bay.uuid)
        # only allow node_count for bay, and default value is 1
        self.assertEqual(1, response['node_count'])
        # Assert nothing else was changed
        self.assertEqual(self.bay.uuid, response['uuid'])
        self.assertEqual(self.bay.cluster_template_id, response['baymodel_id'])
        self.assertEqual(self.bay.name, response['name'])
        self.assertEqual(self.bay.master_count, response['master_count'])

    def test_remove_mandatory_property_fail(self):
        mandatory_properties = ('/uuid', '/baymodel_id')
        for p in mandatory_properties:
            response = self.patch_json('/bays/%s' % self.bay.uuid,
                                       [{'path': p, 'op': 'remove'}],
                                       expect_errors=True)
            self.assertEqual(400, response.status_int)
            self.assertEqual('application/json', response.content_type)
            self.assertTrue(response.json['errors'])

    def test_remove_non_existent_property(self):
        response = self.patch_json(
            '/bays/%s' % self.bay.uuid,
            [{'path': '/non-existent', 'op': 'remove'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['errors'])


class TestPost(api_base.FunctionalTest):

    def setUp(self):
        super(TestPost, self).setUp()
        self.cluster_template = obj_utils.create_test_cluster_template(
            self.context)
        p = mock.patch.object(rpcapi.API, 'cluster_create')
        self.mock_bay_create = p.start()
        self.mock_bay_create.side_effect = self._simulate_rpc_bay_create
        self.addCleanup(p.stop)
        p = mock.patch.object(attr_validator, 'validate_os_resources')
        self.mock_valid_os_res = p.start()
        self.addCleanup(p.stop)

    def _simulate_rpc_bay_create(self, bay, master_count, node_count,
                                 bay_create_timeout):
        bay.create()
        db_utils.create_nodegroups_for_cluster(
            cluster_id=bay.uuid, node_count=node_count,
            master_count=master_count)
        return bay

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_bay(self, mock_utcnow):
        bdict = apiutils.bay_post_data()
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.post_json('/bays', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        # Check location header
        self.assertIsNotNone(response.location)
        self.assertTrue(uuidutils.is_uuid_like(response.json['uuid']))
        self.assertNotIn('updated_at', response.json.keys)
        return_created_at = timeutils.parse_isotime(
            response.json['created_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_created_at)
        self.assertEqual(bdict['bay_create_timeout'],
                         response.json['bay_create_timeout'])

    def test_create_bay_set_project_id_and_user_id(self):
        bdict = apiutils.bay_post_data()

        def _simulate_rpc_bay_create(bay, node_count, master_count,
                                     bay_create_timeout):
            self.assertEqual(self.context.project_id, bay.project_id)
            self.assertEqual(self.context.user_id, bay.user_id)
            bay.create()
            db_utils.create_nodegroups_for_cluster(
                cluster_id=bay.uuid, node_count=node_count,
                master_count=master_count)
            return bay
        self.mock_bay_create.side_effect = _simulate_rpc_bay_create

        self.post_json('/bays', bdict)

    def test_create_bay_doesnt_contain_id(self):
        with mock.patch.object(self.dbapi, 'create_cluster',
                               wraps=self.dbapi.create_cluster) as cc_mock:
            bdict = apiutils.bay_post_data(name='bay_example_A')
            response = self.post_json('/bays', bdict)
            self.assertEqual(bdict['name'], response.json['name'])
            cc_mock.assert_called_once_with(mock.ANY)
            # Check that 'id' is not in first arg of positional args
            self.assertNotIn('id', cc_mock.call_args[0][0])

    def test_create_bay_generate_uuid(self):
        bdict = apiutils.bay_post_data()
        del bdict['uuid']

        response = self.post_json('/bays', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(bdict['name'], response.json['name'])
        self.assertTrue(uuidutils.is_uuid_like(response.json['uuid']))

    def test_create_bay_no_baymodel_id(self):
        bdict = apiutils.bay_post_data()
        del bdict['baymodel_id']
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)

    def test_create_bay_with_non_existent_baymodel_id(self):
        bdict = apiutils.bay_post_data(baymodel_id=uuidutils.generate_uuid())
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_bay_with_baymodel_name(self):
        bdict = apiutils.bay_post_data(baymodel_id=self.cluster_template.name)
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)

    def test_create_bay_with_node_count_zero(self):
        bdict = apiutils.bay_post_data()
        bdict['node_count'] = 0
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_bay_with_node_count_negative(self):
        bdict = apiutils.bay_post_data()
        bdict['node_count'] = -1
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_bay_with_no_node_count(self):
        bdict = apiutils.bay_post_data()
        del bdict['node_count']
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(1, response.json['node_count'])

    def test_create_bay_with_master_count_zero(self):
        bdict = apiutils.bay_post_data()
        bdict['master_count'] = 0
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_bay_with_no_master_count(self):
        bdict = apiutils.bay_post_data()
        del bdict['master_count']
        response = self.post_json('/bays', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(1, response.json['master_count'])

    def test_create_bay_with_invalid_long_name(self):
        bdict = apiutils.bay_post_data(name='x' * 243)
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_bay_with_invalid_integer_name(self):
        bdict = apiutils.bay_post_data(name='123456')
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_bay_with_invalid_integer_str_name(self):
        bdict = apiutils.bay_post_data(name='123456test_bay')
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_bay_with_hyphen_invalid_at_start_name(self):
        bdict = apiutils.bay_post_data(name='-test_bay')
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_bay_with_period_invalid_at_start_name(self):
        bdict = apiutils.bay_post_data(name='.test_bay')
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_bay_with_underscore_invalid_at_start_name(self):
        bdict = apiutils.bay_post_data(name='_test_bay')
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_bay_with_valid_str_int_name(self):
        bdict = apiutils.bay_post_data(name='test_bay123456')
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(response.json['name'], bdict['name'])

    def test_create_bay_with_hyphen_valid_name(self):
        bdict = apiutils.bay_post_data(name='test-bay')
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(response.json['name'], bdict['name'])

    def test_create_bay_with_period_valid_name(self):
        bdict = apiutils.bay_post_data(name='test.bay')
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(response.json['name'], bdict['name'])

    def test_create_bay_with_period_at_end_valid_name(self):
        bdict = apiutils.bay_post_data(name='testbay.')
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(response.json['name'], bdict['name'])

    def test_create_bay_with_hyphen_at_end_valid_name(self):
        bdict = apiutils.bay_post_data(name='testbay-')
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(response.json['name'], bdict['name'])

    def test_create_bay_with_underscore_at_end_valid_name(self):
        bdict = apiutils.bay_post_data(name='testbay_')
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(response.json['name'], bdict['name'])

    def test_create_bay_with_mix_special_char_valid_name(self):
        bdict = apiutils.bay_post_data(name='test.-_bay')
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(response.json['name'], bdict['name'])

    def test_create_bay_with_capital_letter_start_valid_name(self):
        bdict = apiutils.bay_post_data(name='Testbay')
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(response.json['name'], bdict['name'])

    def test_create_bay_with_invalid_empty_name(self):
        bdict = apiutils.bay_post_data(name='')
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_bay_without_name(self):
        bdict = apiutils.bay_post_data()
        del bdict['name']
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertIsNotNone(response.json['name'])

    def test_create_bay_with_timeout_none(self):
        bdict = apiutils.bay_post_data()
        bdict['bay_create_timeout'] = None
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)

    def test_create_bay_with_no_timeout(self):
        def _simulate_rpc_bay_create(bay, node_count, master_count,
                                     bay_create_timeout):
            self.assertEqual(60, bay_create_timeout)
            bay.create()
            db_utils.create_nodegroups_for_cluster(
                cluster_id=bay.uuid, node_count=node_count,
                master_count=master_count)
            return bay
        self.mock_bay_create.side_effect = _simulate_rpc_bay_create
        bdict = apiutils.bay_post_data()
        del bdict['bay_create_timeout']
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)

    def test_create_bay_with_timeout_negative(self):
        bdict = apiutils.bay_post_data()
        bdict['bay_create_timeout'] = -1
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_bay_with_timeout_zero(self):
        bdict = apiutils.bay_post_data()
        bdict['bay_create_timeout'] = 0
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)

    def test_create_bay_with_invalid_flavor(self):
        bdict = apiutils.bay_post_data()
        self.mock_valid_os_res.side_effect = exception.FlavorNotFound(
            'test-flavor')
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(self.mock_valid_os_res.called)
        self.assertEqual(400, response.status_int)

    def test_create_bay_with_invalid_ext_network(self):
        bdict = apiutils.bay_post_data()
        self.mock_valid_os_res.side_effect = exception.ExternalNetworkNotFound(
            'test-net')
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(self.mock_valid_os_res.called)
        self.assertEqual(400, response.status_int)

    def test_create_bay_with_invalid_keypair(self):
        bdict = apiutils.bay_post_data()
        self.mock_valid_os_res.side_effect = exception.KeyPairNotFound(
            'test-key')
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(self.mock_valid_os_res.called)
        self.assertEqual(404, response.status_int)

    def test_create_bay_with_nonexist_image(self):
        bdict = apiutils.bay_post_data()
        self.mock_valid_os_res.side_effect = exception.ImageNotFound(
            'test-img')
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(self.mock_valid_os_res.called)
        self.assertEqual(400, response.status_int)

    def test_create_bay_with_multi_images_same_name(self):
        bdict = apiutils.bay_post_data()
        self.mock_valid_os_res.side_effect = exception.Conflict('test-img')
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(self.mock_valid_os_res.called)
        self.assertEqual(409, response.status_int)

    def test_create_bay_with_on_os_distro_image(self):
        bdict = apiutils.bay_post_data()
        self.mock_valid_os_res.side_effect = exception.OSDistroFieldNotFound(
            'img')
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(self.mock_valid_os_res.called)
        self.assertEqual(400, response.status_int)

    def test_create_bay_with_no_lb_one_node(self):
        cluster_template = obj_utils.create_test_cluster_template(
            self.context, name='foo', uuid='foo', master_lb_enabled=False)
        bdict = apiutils.bay_post_data(baymodel_id=cluster_template.name,
                                       master_count=1)
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)

    def test_create_bay_with_no_lb_multi_node(self):
        cluster_template = obj_utils.create_test_cluster_template(
            self.context, name='foo', uuid='foo', master_lb_enabled=False)
        bdict = apiutils.bay_post_data(baymodel_id=cluster_template.name,
                                       master_count=3, master_lb_enabled=False)
        response = self.post_json('/bays', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)

    def test_create_bay_with_docker_volume_size(self):
        bdict = apiutils.bay_post_data()
        bdict['docker_volume_size'] = 3
        response = self.post_json('/bays', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        bay, timeout = self.mock_bay_create.call_args
        self.assertEqual(3, bay[0].docker_volume_size)

    def test_create_bay_without_docker_volume_size(self):
        bdict = apiutils.bay_post_data()
        # Remove the default docker_volume_size from the bay dict.
        del bdict['docker_volume_size']
        response = self.post_json('/bays', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        bay, timeout = self.mock_bay_create.call_args
        # Verify docker_volume_size from BayModel is used
        self.assertEqual(20, bay[0].docker_volume_size)


class TestDelete(api_base.FunctionalTest):

    def setUp(self):
        super(TestDelete, self).setUp()
        self.cluster_template = obj_utils.create_test_cluster_template(
            self.context)
        self.bay = obj_utils.create_test_cluster(self.context)
        p = mock.patch.object(rpcapi.API, 'cluster_delete')
        self.mock_bay_delete = p.start()
        self.mock_bay_delete.side_effect = self._simulate_rpc_bay_delete
        self.addCleanup(p.stop)

    def _simulate_rpc_bay_delete(self, bay_uuid):
        bay = objects.Cluster.get_by_uuid(self.context, bay_uuid)
        bay.destroy()
        ngs = objects.NodeGroup.list(self.context, bay_uuid)
        for ng in ngs:
            ng.destroy()

    def test_delete_bay(self):
        self.delete('/bays/%s' % self.bay.uuid)
        response = self.get_json('/bays/%s' % self.bay.uuid,
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_delete_bay_not_found(self):
        uuid = uuidutils.generate_uuid()
        response = self.delete('/bays/%s' % uuid, expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_delete_bay_with_name_not_found(self):
        response = self.delete('/bays/not_found', expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_delete_bay_with_name(self):
        response = self.delete('/bays/%s' % self.bay.name,
                               expect_errors=True)
        self.assertEqual(204, response.status_int)

    def test_delete_multiple_bay_by_name(self):
        obj_utils.create_test_cluster(self.context, name='test_bay',
                                      uuid=uuidutils.generate_uuid())
        obj_utils.create_test_cluster(self.context, name='test_bay',
                                      uuid=uuidutils.generate_uuid())
        response = self.delete('/bays/test_bay', expect_errors=True)
        self.assertEqual(409, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])


class TestBayPolicyEnforcement(api_base.FunctionalTest):

    def setUp(self):
        super(TestBayPolicyEnforcement, self).setUp()
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
            "bay:get_all", self.get_json, '/bays', expect_errors=True)

    def test_policy_disallow_get_one(self):
        self.bay = obj_utils.create_test_cluster(self.context)
        self._common_policy_check(
            "bay:get", self.get_json, '/bays/%s' % self.bay.uuid,
            expect_errors=True)

    def test_policy_disallow_detail(self):
        self._common_policy_check(
            "bay:detail", self.get_json,
            '/bays/%s/detail' % uuidutils.generate_uuid(),
            expect_errors=True)

    def test_policy_disallow_update(self):
        self.bay = obj_utils.create_test_cluster(self.context,
                                                 name='bay_example_A',
                                                 node_count=3)
        self._common_policy_check(
            "bay:update", self.patch_json, '/bays/%s' % self.bay.name,
            [{'path': '/name', 'value': "new_name", 'op': 'replace'}],
            expect_errors=True)

    def test_policy_disallow_create(self):
        bdict = apiutils.bay_post_data(name='bay_example_A')
        self._common_policy_check(
            "bay:create", self.post_json, '/bays', bdict, expect_errors=True)

    def _simulate_rpc_bay_delete(self, bay_uuid):
        bay = objects.Cluster.get_by_uuid(self.context, bay_uuid)
        bay.destroy()

    def test_policy_disallow_delete(self):
        p = mock.patch.object(rpcapi.API, 'cluster_delete')
        self.mock_bay_delete = p.start()
        self.mock_bay_delete.side_effect = self._simulate_rpc_bay_delete
        self.addCleanup(p.stop)
        self.bay = obj_utils.create_test_cluster(self.context)
        self._common_policy_check(
            "bay:delete", self.delete, '/bays/%s' % self.bay.uuid,
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
        bay = obj_utils.create_test_cluster(self.context, user_id='another')
        self._owner_check("bay:get", self.get_json, '/bays/%s' % bay.uuid,
                          expect_errors=True)

    def test_policy_only_owner_update(self):
        bay = obj_utils.create_test_cluster(self.context, user_id='another')
        self._owner_check(
            "bay:update", self.patch_json, '/bays/%s' % bay.uuid,
            [{'path': '/name', 'value': "new_name", 'op': 'replace'}],
            expect_errors=True)

    def test_policy_only_owner_delete(self):
        bay = obj_utils.create_test_cluster(self.context, user_id='another')
        self._owner_check("bay:delete", self.delete, '/bays/%s' % bay.uuid,
                          expect_errors=True)
