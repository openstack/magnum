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

import mock
from oslo_config import cfg
from oslo_policy import policy
from oslo_utils import timeutils
from six.moves.urllib import parse as urlparse
from wsme import types as wtypes

from magnum.api.controllers.v1 import replicationcontroller as api_rc
from magnum.common import utils
from magnum.conductor import api as rpcapi
from magnum import objects
from magnum.tests import base
from magnum.tests.unit.api import base as api_base
from magnum.tests.unit.api import utils as apiutils
from magnum.tests.unit.objects import utils as obj_utils


class TestRCObject(base.TestCase):

    def test_rc_init(self):
        rc_dict = apiutils.rc_post_data(bay_uuid=None)
        del rc_dict['images']
        rc = api_rc.ReplicationController(**rc_dict)
        self.assertEqual(wtypes.Unset, rc.images)


class TestListRC(api_base.FunctionalTest):

    def setUp(self):
        super(TestListRC, self).setUp()
        obj_utils.create_test_bay(self.context)

    def test_empty(self):
        response = self.get_json('/rcs')
        self.assertEqual([], response['rcs'])

    def _assert_rc_fields(self, rc):
        rc_fields = ['name', 'bay_uuid', 'name', 'images', 'labels',
                     'replicas']
        for field in rc_fields:
            self.assertIn(field, rc)

    def test_one(self):
        rc = obj_utils.create_test_rc(self.context)
        response = self.get_json('/rcs')
        self.assertEqual(rc.uuid, response['rcs'][0]["uuid"])
        self._assert_rc_fields(response['rcs'][0])

    def test_get_one(self):
        rc = obj_utils.create_test_rc(self.context)
        response = self.get_json('/rcs/%s' % rc['uuid'])
        self.assertEqual(rc.uuid, response['uuid'])
        self._assert_rc_fields(response)

    def test_get_one_by_name(self):
        rc = obj_utils.create_test_rc(self.context)
        response = self.get_json('/rcs/%s' % rc['name'])
        self.assertEqual(rc.uuid, response['uuid'])
        self._assert_rc_fields(response)

    def test_get_one_by_name_not_found(self):
        response = self.get_json(
            '/rcs/not_found',
            expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_get_one_by_name_multiple_rc(self):
        obj_utils.create_test_rc(
            self.context, name='test_rc',
            uuid=utils.generate_uuid())
        obj_utils.create_test_rc(
            self.context, name='test_rc',
            uuid=utils.generate_uuid())
        response = self.get_json('/rcs/test_rc', expect_errors=True)
        self.assertEqual(409, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_get_all_with_pagination_marker(self):
        rc_list = []
        for id_ in range(4):
            rc = obj_utils.create_test_rc(self.context, id=id_,
                                          uuid=utils.generate_uuid())
            rc_list.append(rc.uuid)

        response = self.get_json('/rcs?limit=3&marker=%s' % rc_list[2])
        self.assertEqual(1, len(response['rcs']))
        self.assertEqual(rc_list[-1], response['rcs'][0]['uuid'])

    def test_detail(self):
        rc = obj_utils.create_test_rc(self.context)
        response = self.get_json('/rcs/detail')
        self.assertEqual(rc.uuid, response['rcs'][0]["uuid"])
        self._assert_rc_fields(response['rcs'][0])

    def test_detail_with_pagination_marker(self):
        rc_list = []
        for id_ in range(4):
            rc = obj_utils.create_test_rc(self.context, id=id_,
                                          uuid=utils.generate_uuid())
            rc_list.append(rc.uuid)

        response = self.get_json('/rcs/detail?limit=3&marker=%s'
                                 % rc_list[2])
        self.assertEqual(1, len(response['rcs']))
        self.assertEqual(rc_list[-1], response['rcs'][0]['uuid'])
        self._assert_rc_fields(response['rcs'][0])

    def test_detail_against_single(self):
        rc = obj_utils.create_test_rc(self.context)
        response = self.get_json('/rcs/%s/detail' % rc['uuid'],
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_many(self):
        rc_list = []
        for id_ in range(5):
            rc = obj_utils.create_test_rc(self.context, id=id_,
                                          uuid=utils.generate_uuid())
            rc_list.append(rc.uuid)
        response = self.get_json('/rcs')
        self.assertEqual(len(rc_list), len(response['rcs']))
        uuids = [r['uuid'] for r in response['rcs']]
        self.assertEqual(sorted(rc_list), sorted(uuids))

    def test_links(self):
        uuid = utils.generate_uuid()
        obj_utils.create_test_rc(self.context, id=1, uuid=uuid)
        response = self.get_json('/rcs/%s' % uuid)
        self.assertIn('links', response.keys())
        self.assertEqual(2, len(response['links']))
        self.assertIn(uuid, response['links'][0]['href'])
        for l in response['links']:
            bookmark = l['rel'] == 'bookmark'
            self.assertTrue(self.validate_link(l['href'], bookmark=bookmark))

    def test_collection_links(self):
        for id_ in range(5):
            obj_utils.create_test_rc(self.context, id=id_,
                                     uuid=utils.generate_uuid())
        response = self.get_json('/rcs/?limit=3')
        self.assertEqual(3, len(response['rcs']))

        next_marker = response['rcs'][-1]['uuid']
        self.assertIn(next_marker, response['next'])

    def test_collection_links_default_limit(self):
        cfg.CONF.set_override('max_limit', 3, 'api')
        for id_ in range(5):
            obj_utils.create_test_rc(self.context, id=id_,
                                     uuid=utils.generate_uuid())
        response = self.get_json('/rcs')
        self.assertEqual(3, len(response['rcs']))

        next_marker = response['rcs'][-1]['uuid']
        self.assertIn(next_marker, response['next'])


class TestPatch(api_base.FunctionalTest):

    def setUp(self):
        super(TestPatch, self).setUp()
        obj_utils.create_test_bay(self.context)
        self.rc = obj_utils.create_test_rc(self.context,
                                           images=['rc_example_A_image'])
        self.another_bay = obj_utils.create_test_bay(
            self.context,
            uuid=utils.generate_uuid())

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        new_image = 'rc_example_B_image'
        response = self.get_json('/rcs/%s' % self.rc.uuid)
        self.assertNotEqual(new_image, response['images'][0])

        response = self.patch_json('/rcs/%s' % self.rc.uuid,
                                   [{'path': '/images/0',
                                     'value': new_image,
                                     'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json('/rcs/%s' % self.rc.uuid)
        self.assertEqual(new_image, response['images'][0])
        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)

    def test_replace_bay_uuid(self):
        response = self.patch_json('/rcs/%s' % self.rc.uuid,
                                   [{'path': '/bay_uuid',
                                     'value': self.another_bay.uuid,
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

    def test_replace_non_existent_bay_uuid(self):
        response = self.patch_json('/rcs/%s' % self.rc.uuid,
                                   [{'path': '/bay_uuid',
                                     'value': utils.generate_uuid(),
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['error_message'])

    def test_replace_internal_field(self):
        response = self.patch_json(
            '/rcs/%s' % self.rc.uuid,
            [{'path': '/labels', 'value': {}, 'op': 'replace'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['error_message'])

    def test_replace_non_existent_rc(self):
        response = self.patch_json('/rcs/%s' % utils.generate_uuid(),
                                   [{'path': '/images/0',
                                     'value': 'rc_example_B_image',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(rpcapi.API, 'rc_update')
    @mock.patch.object(api_rc.ReplicationController, 'parse_manifest')
    def test_replace_with_manifest(self, parse_manifest, rc_update):
        response = self.patch_json('/rcs/%s' % self.rc.uuid,
                                   [{'path': '/manifest',
                                     'value': '{}',
                                     'op': 'replace'}])
        self.assertEqual(200, response.status_int)
        self.assertEqual('application/json', response.content_type)
        parse_manifest.assert_called_once_with()
        self.assertTrue(rc_update.is_called)

    def test_add_ok(self):
        new_image = 'rc_example_B_image'
        response = self.patch_json('/rcs/%s' % self.rc.uuid,
                                   [{'path': '/images/0',
                                     'value': new_image,
                                     'op': 'add'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_int)

        response = self.get_json('/rcs/%s' % self.rc.uuid)
        self.assertEqual(new_image, response['images'][0])

    def test_add_non_existent_property(self):
        response = self.patch_json(
            '/rcs/%s' % self.rc.uuid,
            [{'path': '/foo', 'value': 'bar', 'op': 'add'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_remove_ok(self):
        response = self.get_json('/rcs/%s' % self.rc.uuid)
        self.assertNotEqual(len(response['images']), 0)

        response = self.patch_json('/rcs/%s' % self.rc.uuid,
                                   [{'path': '/images', 'op': 'remove'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json('/rcs/%s' % self.rc.uuid)
        self.assertEqual(len(response['images']), 0)

    def test_remove_uuid(self):
        response = self.patch_json('/rcs/%s' % self.rc.uuid,
                                   [{'path': '/uuid', 'op': 'remove'}],
                                   expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_remove_bay_uuid(self):
        response = self.patch_json('/rcs/%s' % self.rc.uuid,
                                   [{'path': '/bay_uuid', 'op': 'remove'}],
                                   expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_remove_internal_field(self):
        response = self.patch_json('/rcs/%s' % self.rc.uuid,
                                   [{'path': '/labels', 'op': 'remove'}],
                                   expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_remove_non_existent_property(self):
        response = self.patch_json(
            '/rcs/%s' % self.rc.uuid,
            [{'path': '/non-existent', 'op': 'remove'}],
            expect_errors=True)
        self.assertEqual(400, response.status_code)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_name(self, mock_utcnow):
        new_image = 'rc_example_B_image'
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json('/rcs/%s' % self.rc.name,
                                   [{'path': '/images/0',
                                     'value': new_image,
                                     'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json('/rcs/%s' % self.rc.uuid)
        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_name_not_found(self, mock_utcnow):
        new_image = 'rc_example_B_image'
        name = 'not_found'
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json('/rcs/%s' % name,
                                   [{'path': '/images/0',
                                     'value': new_image,
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(404, response.status_code)

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_name_multiple_rc(self, mock_utcnow):
        new_image = 'rc_example_B_image'
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        obj_utils.create_test_rc(self.context, name='test_rc',
                                 uuid=utils.generate_uuid())
        obj_utils.create_test_rc(self.context, name='test_rc',
                                 uuid=utils.generate_uuid())

        response = self.patch_json('/rcs/test_rc',
                                   [{'path': '/images/0',
                                     'value': new_image,
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(409, response.status_code)


class TestPost(api_base.FunctionalTest):

    def setUp(self):
        super(TestPost, self).setUp()
        obj_utils.create_test_bay(self.context)
        p = mock.patch.object(rpcapi.API, 'rc_create')
        self.mock_rc_create = p.start()
        self.mock_rc_create.side_effect = self._simulate_rpc_rc_create
        self.addCleanup(p.stop)
        p = mock.patch('magnum.objects.BayModel.get_by_uuid')
        self.mock_baymodel_get_by_uuid = p.start()
        self.mock_baymodel_get_by_uuid.return_value.coe = 'kubernetes'
        self.addCleanup(p.stop)

    def _simulate_rpc_rc_create(self, rc):
        rc.create(self.context)
        return rc

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_rc(self, mock_utcnow):
        rc_dict = apiutils.rc_post_data()
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.post_json('/rcs', rc_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        # Check location header
        self.assertIsNotNone(response.location)
        expected_location = '/v1/rcs/%s' % rc_dict['uuid']
        self.assertEqual(urlparse.urlparse(response.location).path,
                         expected_location)
        self.assertEqual(rc_dict['uuid'], response.json['uuid'])
        self.assertNotIn('updated_at', response.json.keys)
        return_created_at = timeutils.parse_isotime(
            response.json['created_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_created_at)

    def test_create_rc_set_project_id_and_user_id(self):
        rc_dict = apiutils.rc_post_data()

        def _simulate_rpc_rc_create(rc):
            self.assertEqual(rc.project_id, self.context.project_id)
            self.assertEqual(rc.user_id, self.context.user_id)
            rc.create()
            return rc
        self.mock_rc_create.side_effect = _simulate_rpc_rc_create

        self.post_json('/rcs', rc_dict)

    def test_create_rc_doesnt_contain_id(self):
        with mock.patch.object(self.dbapi, 'create_rc',
                               wraps=self.dbapi.create_rc) as cc_mock:
            rc_dict = apiutils.rc_post_data()
            response = self.post_json('/rcs', rc_dict)
            self.assertEqual(rc_dict['images'], response.json['images'])
            cc_mock.assert_called_once_with(mock.ANY)
            # Check that 'id' is not in first arg of positional args
            self.assertNotIn('id', cc_mock.call_args[0][0])

    def test_create_rc_generate_uuid(self):
        rc_dict = apiutils.rc_post_data()
        del rc_dict['uuid']

        response = self.post_json('/rcs', rc_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(rc_dict['images'], response.json['images'])
        self.assertTrue(utils.is_uuid_like(response.json['uuid']))

    def test_create_rc_no_bay_uuid(self):
        rc_dict = apiutils.rc_post_data()
        del rc_dict['bay_uuid']
        response = self.post_json('/rcs', rc_dict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)

    def test_create_rc_with_non_existent_bay_uuid(self):
        rc_dict = apiutils.rc_post_data(bay_uuid=utils.generate_uuid())
        response = self.post_json('/rcs', rc_dict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_create_rc_with_invalid_manifest(self):
        rc_dict = apiutils.rc_post_data()
        rc_dict['manifest'] = 'wrong_manifest'
        response = self.post_json('/rcs', rc_dict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_create_rc_no_manifest(self):
        rc_dict = apiutils.rc_post_data()
        del rc_dict['manifest']
        response = self.post_json('/rcs', rc_dict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_create_rc_no_id_in_manifest(self):
        rc_dict = apiutils.rc_post_data()
        rc_dict['manifest'] = {}
        response = self.post_json('/rcs', rc_dict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])


class TestDelete(api_base.FunctionalTest):

    def setUp(self):
        super(TestDelete, self).setUp()
        obj_utils.create_test_bay(self.context)
        self.rc = obj_utils.create_test_rc(self.context)
        p = mock.patch.object(rpcapi.API, 'rc_delete')
        self.mock_rc_delete = p.start()
        self.mock_rc_delete.side_effect = self._simulate_rpc_rc_delete
        self.addCleanup(p.stop)

    def _simulate_rpc_rc_delete(self, rc_uuid):
        rc = objects.ReplicationController.get_by_uuid(self.context, rc_uuid)
        rc.destroy()

    def test_delete_rc(self):
        self.delete('/rcs/%s' % self.rc.uuid)
        response = self.get_json('/rcs/%s' % self.rc.uuid,
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_delete_rc_not_found(self):
        uuid = utils.generate_uuid()
        response = self.delete('/rcs/%s' % uuid, expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_delete_rc_with_name_not_found(self):
        response = self.delete('/rcs/not_found', expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_delete_rc_with_name(self):
        response = self.delete('/rcs/%s' % self.rc.name,
                               expect_errors=True)
        self.assertEqual(204, response.status_int)

    def test_delete_multiple_rc_by_name(self):
        obj_utils.create_test_rc(self.context, name='test_rc',
                                 uuid=utils.generate_uuid())
        obj_utils.create_test_rc(self.context, name='test_rc',
                                 uuid=utils.generate_uuid())
        response = self.delete('/rcs/test_rc', expect_errors=True)
        self.assertEqual(409, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


class TestRCEnforcement(api_base.FunctionalTest):

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules({rule: 'project:non_fake'})
        exc = self.assertRaises(policy.PolicyNotAuthorized,
                                func, *arg, **kwarg)
        self.assertTrue(exc.message.startswith(rule))
        self.assertTrue(exc.message.endswith('disallowed by policy'))

    def test_policy_disallow_get_all(self):
        self._common_policy_check(
            'rc:get_all', self.get_json, '/rcs')

    def test_policy_disallow_get_one(self):
        self._common_policy_check(
            'rc:get', self.get_json, '/rcs/111-222-333')

    def test_policy_disallow_detail(self):
        self._common_policy_check(
            'rc:detail', self.get_json, '/rcs/111-222-333/detail')

    def test_policy_disallow_update(self):
        rc = obj_utils.create_test_rc(self.context,
                                      desc='test rc',
                                      uuid=utils.generate_uuid())

        new_image = 'rc_example_B_image'
        self._common_policy_check(
            'rc:update', self.patch_json,
            '/rcs/%s' % rc.uuid,
            [{'path': '/images/0', 'value': new_image, 'op': 'replace'}])

    def test_policy_disallow_create(self):
        pdict = apiutils.rc_post_data()
        self._common_policy_check(
            'rc:create', self.post_json, '/rcs', pdict)

    def test_policy_disallow_delete(self):
        rc = obj_utils.create_test_rc(self.context,
                                      name='test_rc',
                                      uuid=utils.generate_uuid())
        self._common_policy_check(
            'rc:delete', self.delete,
            '/rcs/%s' % rc.uuid)
