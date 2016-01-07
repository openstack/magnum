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
import json

import mock
from oslo_config import cfg
from six.moves.urllib import parse as urlparse
from wsme import types as wtypes

from magnum.api.controllers.v1 import replicationcontroller as api_rc
from magnum.common.pythonk8sclient.swagger_client import rest
from magnum.common import utils
from magnum.conductor import api as rpcapi
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
        obj_utils.create_test_bay(self.context, coe='kubernetes')
        self.rc = obj_utils.create_test_rc(self.context)

    @mock.patch.object(rpcapi.API, 'rc_list')
    def test_empty(self, mock_rc_list):
        mock_rc_list.return_value = []
        response = self.get_json('/rcs?bay_ident=5d12f6fd-a196-4bf0-ae4c-'
                                 '1f639a523a52')
        self.assertEqual([], response['rcs'])

    def _assert_rc_fields(self, rc):
        rc_fields = ['name', 'bay_uuid', 'name', 'images', 'labels',
                     'replicas']
        for field in rc_fields:
            self.assertIn(field, rc)

    @mock.patch.object(rpcapi.API, 'rc_show')
    def test_get_one(self, mock_rc_show):
        rc = obj_utils.create_test_rc(self.context)
        mock_rc_show.return_value = rc
        response = self.get_json('/rcs/%s/%s' % (rc['uuid'], rc['bay_uuid']))
        self.assertEqual(rc.uuid, response['uuid'])
        self._assert_rc_fields(response)

    @mock.patch.object(rpcapi.API, 'rc_show')
    def test_get_one_by_name(self, mock_rc_show):
        rc = obj_utils.create_test_rc(self.context)
        mock_rc_show.return_value = rc
        response = self.get_json('/rcs/%s/%s' % (rc['name'], rc['bay_uuid']))
        self.assertEqual(rc.uuid, response['uuid'])
        self._assert_rc_fields(response)

    @mock.patch.object(rpcapi.API, 'rc_show')
    def test_get_one_by_name_not_found(self, mock_rc_show):
        err = rest.ApiException(status=404)
        mock_rc_show.side_effect = err
        response = self.get_json(
            '/rcs/not_found/5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            expect_errors=True)
        self.assertEqual(500, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(rpcapi.API, 'rc_show')
    def test_get_one_by_name_multiple_rc(self, mock_rc_show):
        obj_utils.create_test_rc(
            self.context, name='test_rc',
            uuid=utils.generate_uuid())
        obj_utils.create_test_rc(
            self.context, name='test_rc',
            uuid=utils.generate_uuid())
        err = rest.ApiException(status=500)
        mock_rc_show.side_effect = err
        response = self.get_json(
            '/rcs/test_rc/5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            expect_errors=True)
        self.assertEqual(500, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(rpcapi.API, 'rc_list')
    def test_get_all_with_pagination_marker(self, mock_rc_list):
        rc_list = []
        for id_ in range(4):
            rc = obj_utils.create_test_rc(self.context, id=id_,
                                          uuid=utils.generate_uuid())
            rc_list.append(rc.uuid)

        mock_rc_list.return_value = [rc]
        response = self.get_json('/rcs?limit=3&marker=%s&bay_ident=5d12f6fd-'
                                 'a196-4bf0-ae4c-1f639a523a52' % rc_list[2])
        self.assertEqual(1, len(response['rcs']))
        self.assertEqual(rc_list[-1], response['rcs'][0]['uuid'])

    @mock.patch.object(rpcapi.API, 'rc_list')
    def test_detail(self, mock_rc_list):
        rc = obj_utils.create_test_rc(self.context)
        mock_rc_list.return_value = [rc]
        response = self.get_json('/rcs/detail?bay_ident=5d12f6fd-a196-4bf0-'
                                 'ae4c-1f639a523a52')
        self.assertEqual(rc.uuid, response['rcs'][0]["uuid"])
        self._assert_rc_fields(response['rcs'][0])

    @mock.patch.object(rpcapi.API, 'rc_list')
    def test_detail_with_pagination_marker(self, mock_rc_list):
        rc_list = []
        for id_ in range(4):
            rc = obj_utils.create_test_rc(self.context, id=id_,
                                          uuid=utils.generate_uuid())
            rc_list.append(rc.uuid)

        mock_rc_list.return_value = [rc]
        response = self.get_json('/rcs/detail?limit=3&marker=%s&bay_ident='
                                 '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'
                                 % (rc_list[2]))

        self.assertEqual(1, len(response['rcs']))
        self.assertEqual(rc_list[-1], response['rcs'][0]['uuid'])
        self._assert_rc_fields(response['rcs'][0])

    def test_detail_against_single(self):
        rc = obj_utils.create_test_rc(self.context)
        response = self.get_json('/rcs/%s/detail' % rc['uuid'],
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)

    @mock.patch.object(rpcapi.API, 'rc_list')
    def test_many(self, mock_rc_list):
        rc_list = []
        for id_ in range(1):
            rc = obj_utils.create_test_rc(self.context, id=id_,
                                          uuid=utils.generate_uuid())
            rc_list.append(rc.uuid)
        mock_rc_list.return_value = [rc]
        response = self.get_json('/rcs?bay_ident=5d12f6fd-a196-4bf0-ae4c-'
                                 '1f639a523a52')
        self.assertEqual(len(rc_list), len(response['rcs']))
        uuids = [r['uuid'] for r in response['rcs']]
        self.assertEqual(sorted(rc_list), sorted(uuids))

    @mock.patch.object(rpcapi.API, 'rc_show')
    def test_links(self, mock_rc_show):
        uuid = utils.generate_uuid()
        rc = obj_utils.create_test_rc(self.context, id=1, uuid=uuid)
        mock_rc_show.return_value = rc
        response = self.get_json('/rcs/%s/%s' % (uuid, rc.bay_uuid))
        self.assertIn('links', response.keys())
        self.assertEqual(2, len(response['links']))
        self.assertIn(uuid, response['links'][0]['href'])

    @mock.patch.object(rpcapi.API, 'rc_list')
    def test_collection_links(self, mock_rc_list):
        for id_ in range(5):
            rc = obj_utils.create_test_rc(self.context, id=id_,
                                          uuid=utils.generate_uuid())
        mock_rc_list.return_value = [rc]
        response = self.get_json('/rcs/?limit=1&bay_ident=5d12f6fd-a196-4bf0'
                                 '-ae4c-1f639a523a52')
        self.assertEqual(1, len(response['rcs']))

    @mock.patch.object(rpcapi.API, 'rc_list')
    def test_collection_links_default_limit(self, mock_rc_list):
        cfg.CONF.set_override('max_limit', 3, 'api')
        for id_ in range(5):
            rc = obj_utils.create_test_rc(self.context, id=id_,
                                          uuid=utils.generate_uuid())
        mock_rc_list.return_value = [rc]
        response = self.get_json('/rcs?bay_ident=5d12f6fd-a196-4bf0-ae4c-'
                                 '1f639a523a52')
        self.assertEqual(1, len(response['rcs']))


class TestPatch(api_base.FunctionalTest):

    def setUp(self):
        super(TestPatch, self).setUp()
        obj_utils.create_test_bay(self.context, coe='kubernetes')
        self.rc = obj_utils.create_test_rc(self.context,
                                           images=['rc_example_A_image'])
        self.another_bay = obj_utils.create_test_bay(
            self.context,
            uuid=utils.generate_uuid())
        self.manifest = '''{
            "metadata": {
                "name": "name_of_rc"
                },
            "spec":{
                "replicas":2,
                "selector":{
                    "name":"frontend"
                },
                "template":{
                    "metadata":{
                        "labels":{
                            "name":"frontend"
                        }
                    },
                    "spec":{
                        "containers":[
                             {
                                 "name":"test-redis",
                                 "image":"steak/for-dinner",
                                 "ports":[
                                     {
                                          "containerPort":80,
                                          "protocol":"TCP"
                                     }
                                 ]
                             }
                        ]
                    }
                }
            }
        }'''

    def test_replace_bay_uuid(self):
        self.rc.manifest = '{"bay_uuid": "self.rc.bay_uuid"}'
        response = self.patch_json(
            '/rcs/%s/%s' % (self.rc.uuid, self.rc.bay_uuid),
            [{'path': '/bay_uuid',
              'value': self.another_bay.uuid,
              'op': 'replace'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)

    def test_replace_non_existent_bay_uuid(self):
        self.rc.manifest = '{"key": "value"}'
        response = self.patch_json(
            '/rcs/%s/%s' % (self.rc.uuid, self.rc.bay_uuid),
            [{'path': '/bay_uuid',
              'value': utils.generate_uuid(),
              'op': 'replace'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['error_message'])

    def test_replace_internal_field(self):
        response = self.patch_json(
            '/rcs/%s/%s' % (self.rc.uuid, self.rc.bay_uuid),
            [{'path': '/labels', 'value': {}, 'op': 'replace'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['error_message'])

    def test_replace_non_existent_rc(self):
        response = self.patch_json(
            '/rcs/%s/%s' % (utils.generate_uuid(),
                            '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'),
            [{'path': '/images/0',
              'value': 'rc_example_B_image',
              'op': 'replace'}],
            expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(rpcapi.API, 'rc_update')
    @mock.patch.object(api_rc.ReplicationController, 'parse_manifest')
    def test_replace_with_manifest(self, parse_manifest, rc_update):
        rc_update.return_value = self.rc
        response = self.patch_json(
            '/rcs/%s/%s' % (self.rc.uuid, self.rc.bay_uuid),
            [{'path': '/manifest',
              'value': '{"foo": "bar"}',
              'op': 'replace'}])
        self.assertEqual(200, response.status_int)
        self.assertEqual('application/json', response.content_type)
        parse_manifest.assert_called_once_with()
        self.assertTrue(rc_update.is_called)

    def test_add_non_existent_property(self):
        response = self.patch_json(
            '/rcs/%s/%s' % (self.rc.uuid, self.rc.bay_uuid),
            [{'path': '/foo', 'value': 'bar', 'op': 'add'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(rpcapi.API, 'rc_update')
    @mock.patch.object(rpcapi.API, 'rc_show')
    def test_remove_ok(self, mock_rc_show, mock_rc_update):
        mock_rc_show.return_value = self.rc
        response = self.get_json(
            '/rcs/%s/%s' % (self.rc.uuid, self.rc.bay_uuid))
        self.assertNotEqual(len(response['images']), 0)

        mock_rc_update.return_value = self.rc
        response = self.patch_json(
            '/rcs/%s/%s' % (self.rc.uuid, self.rc.bay_uuid),
            [{'path': '/manifest',
              'op': 'remove'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        mock_rc_show.return_value = self.rc
        response = self.get_json(
            '/rcs/%s/%s' % (self.rc.uuid, self.rc.bay_uuid))
        self.assertEqual(len(response['images']), 1)

    def test_remove_uuid(self):
        response = self.patch_json(
            '/rcs/%s/%s' % (self.rc.uuid, self.rc.bay_uuid),
            [{'path': '/uuid', 'op': 'remove'}],
            expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_remove_bay_uuid(self):
        response = self.patch_json('/rcs/%s/%s' % (self.rc.uuid,
                                                   self.rc.bay_uuid),
                                   [{'path': '/bay_uuid', 'op': 'remove'}],
                                   expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_remove_internal_field(self):
        response = self.patch_json('/rcs/%s/%s' % (self.rc.uuid,
                                                   self.rc.bay_uuid),
                                   [{'path': '/labels', 'op': 'remove'}],
                                   expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_remove_non_existent_property(self):
        response = self.patch_json(
            '/rcs/%s/%s' % (self.rc.uuid, self.rc.bay_uuid),
            [{'path': '/non-existent', 'op': 'remove'}],
            expect_errors=True)
        self.assertEqual(400, response.status_code)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(rpcapi.API, 'rc_show')
    @mock.patch.object(rpcapi.API, 'rc_update')
    @mock.patch.object(api_rc.ReplicationController, 'parse_manifest')
    def test_replace_ok_by_name(self, parse_manifest,
                                mock_rc_update,
                                mock_rc_show):
        mock_rc_update.return_value = self.rc
        response = self.patch_json(
            '/rcs/%s/%s' % (self.rc.name, self.rc.bay_uuid),
            [{'path': '/manifest',
              'value': '{"foo": "bar"}',
              'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)
        parse_manifest.assert_called_once_with()
        self.assertTrue(mock_rc_update.is_called)

        mock_rc_show.return_value = self.rc
        response = self.get_json(
            '/rcs/%s/%s' % (self.rc.uuid,
                            self.rc.bay_uuid),
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_name_not_found(self, mock_utcnow):
        new_image = 'rc_example_B_image'
        name = 'not_found'
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json(
            '/rcs/%s/%s' % (name, self.rc.bay_uuid),
            [{'path': '/images/0',
              'value': new_image,
              'op': 'replace'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_name_multiple_rc(self, mock_utcnow):
        new_image = 'rc_example_B_image'
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        obj_utils.create_test_rc(self.context, name='test_rc',
                                 uuid=utils.generate_uuid())
        obj_utils.create_test_rc(self.context, name='test_rc',
                                 uuid=utils.generate_uuid())

        response = self.patch_json(
            '/rcs/test_rc/5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            [{'path': '/images/0',
              'value': new_image,
              'op': 'replace'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)


class TestPost(api_base.FunctionalTest):

    def setUp(self):
        super(TestPost, self).setUp()
        self.test_bay = obj_utils.create_test_bay(self.context,
                                                  coe='kubernetes')
        self.rc_obj = obj_utils.create_test_rc(self.context)
        p = mock.patch.object(rpcapi.API, 'rc_create')
        self.mock_rc_create = p.start()
        self.mock_rc_create.return_value = self.rc_obj
        self.addCleanup(p.stop)
        p = mock.patch('magnum.objects.BayModel.get_by_uuid')
        self.mock_baymodel_get_by_uuid = obj_utils.get_test_baymodel(
            self.context,
            uuid=self.test_bay.baymodel_id,
            coe='kubernetes')

    @mock.patch('oslo_utils.timeutils.utcnow')
    @mock.patch.object(rpcapi.API, 'rc_create')
    def test_create_rc(self, mock_rc_create, mock_utcnow):
        rc_dict = apiutils.rc_post_data()
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        mock_rc_create.return_value = self.rc_obj
        response = self.post_json('/rcs', rc_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        # Check location header
        self.assertIsNotNone(response.location)
        expected_location = '/v1/rcs/%s' % rc_dict['uuid']
        self.assertEqual(expected_location,
                         urlparse.urlparse(response.location).path)
        self.assertEqual(rc_dict['uuid'], response.json['uuid'])

    def test_create_rc_set_project_id_and_user_id(self):
        rc_dict = apiutils.rc_post_data()

        def _simulate_rpc_rc_create(rc):
            self.assertEqual(rc.project_id, self.context.project_id)
            self.assertEqual(rc.user_id, self.context.user_id)
            return rc
        self.mock_rc_create.side_effect = _simulate_rpc_rc_create

        self.post_json('/rcs', rc_dict)

    @mock.patch.object(rpcapi.API, 'rc_create')
    def test_create_rc_generate_uuid(self, mock_rc_create):
        rc_dict = apiutils.rc_post_data()
        del rc_dict['uuid']
        mock_rc_create.return_value = self.rc_obj
        response = self.post_json('/rcs', rc_dict, expect_errors=True)
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
        obj_utils.create_test_bay(self.context, coe='kubernetes')
        self.rc = obj_utils.create_test_rc(self.context)

    @mock.patch.object(rpcapi.API, 'rc_delete')
    @mock.patch.object(rpcapi.API, 'rc_show')
    def test_delete_rc(self, mock_rc_show, mock_rc_delete):
        self.delete('/rcs/%s/%s' % (self.rc.uuid, self.rc.bay_uuid))
        err = rest.ApiException(status=404)
        mock_rc_show.side_effect = err
        response = self.get_json(
            '/rcs/%s/%s' % (self.rc.uuid, self.rc.bay_uuid),
            expect_errors=True)
        self.assertEqual(500, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(rpcapi.API, 'rc_delete')
    def test_delete_rc_not_found(self, mock_rc_delete):
        uuid = utils.generate_uuid()
        err = rest.ApiException(status=404)
        mock_rc_delete.side_effect = err
        response = self.delete('/rcs/%s/%s' % (uuid, self.rc.bay_uuid),
                               expect_errors=True)
        self.assertEqual(500, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(rpcapi.API, 'rc_delete')
    def test_delete_rc_with_name_not_found(self, mock_rc_delete):
        err = rest.ApiException(status=404)
        mock_rc_delete.side_effect = err
        response = self.delete(
            '/rcs/not_found/5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            expect_errors=True)
        self.assertEqual(500, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(rpcapi.API, 'rc_delete')
    def test_delete_rc_with_name(self, mock_rc_delete):
        response = self.delete('/rcs/%s/%s' % (self.rc.name, self.rc.bay_uuid),
                               expect_errors=True)
        self.assertEqual(204, response.status_int)

    @mock.patch.object(rpcapi.API, 'rc_delete')
    def test_delete_multiple_rc_by_name(self, mock_rc_delete):
        err = rest.ApiException(status=409)
        mock_rc_delete.side_effect = err
        obj_utils.create_test_rc(self.context, name='test_rc',
                                 uuid=utils.generate_uuid())
        obj_utils.create_test_rc(self.context, name='test_rc',
                                 uuid=utils.generate_uuid())
        response = self.delete(
            '/rcs/test_rc/5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            expect_errors=True)
        self.assertEqual(500, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


class TestRCEnforcement(api_base.FunctionalTest):

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules({rule: 'project:non_fake'})
        response = func(*arg, **kwarg)
        self.assertEqual(403, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(
            "Policy doesn't allow %s to be performed." % rule,
            json.loads(response.json['error_message'])['faultstring'])

    def test_policy_disallow_get_all(self):
        self._common_policy_check(
            'rc:get_all', self.get_json, '/rcs', expect_errors=True)

    def test_policy_disallow_get_one(self):
        self._common_policy_check(
            'rc:get', self.get_json,
            '/rcs/?bay_ident=%s' % utils.generate_uuid(),
            expect_errors=True)

    def test_policy_disallow_detail(self):
        self._common_policy_check(
            'rc:detail', self.get_json,
            '/rcs/detail?bay_ident=%s' % utils.generate_uuid(),
            expect_errors=True)

    def test_policy_disallow_update(self):
        rc = obj_utils.create_test_rc(self.context,
                                      desc='test rc',
                                      uuid=utils.generate_uuid())

        new_image = 'rc_example_B_image'
        self._common_policy_check(
            'rc:update', self.patch_json,
            '/rcs/%s/%s' % (rc.uuid, utils.generate_uuid()),
            [{'path': '/images/0', 'value': new_image, 'op': 'replace'}],
            expect_errors=True)

    def test_policy_disallow_create(self):
        bay = obj_utils.create_test_bay(self.context)
        pdict = apiutils.rc_post_data(bay_uuid=bay.uuid)
        self._common_policy_check(
            'rc:create', self.post_json, '/rcs', pdict, expect_errors=True)

    def test_policy_disallow_delete(self):
        rc = obj_utils.create_test_rc(self.context,
                                      name='test_rc',
                                      uuid=utils.generate_uuid())
        self._common_policy_check(
            'rc:delete', self.delete,
            '/rcs/%s/%s' % (rc.uuid, utils.generate_uuid()),
            expect_errors=True)
