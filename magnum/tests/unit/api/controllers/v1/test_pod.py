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

from magnum.api.controllers.v1 import pod as api_pod
from magnum.common import utils
from magnum.conductor import api as rpcapi
from magnum import objects
from magnum.tests import base
from magnum.tests.unit.api import base as api_base
from magnum.tests.unit.api import utils as apiutils
from magnum.tests.unit.objects import utils as obj_utils


class TestPodObject(base.TestCase):

    def test_pod_init(self):
        pod_dict = apiutils.pod_post_data(bay_uuid=None)
        del pod_dict['desc']
        pod = api_pod.Pod(**pod_dict)
        self.assertEqual(wtypes.Unset, pod.desc)


class TestListPod(api_base.FunctionalTest):

    def setUp(self):
        super(TestListPod, self).setUp()
        obj_utils.create_test_bay(self.context)

    def test_empty(self):
        response = self.get_json('/pods')
        self.assertEqual([], response['pods'])

    def _assert_pod_fields(self, pod):
        pod_fields = ['name', 'bay_uuid', 'desc', 'images', 'labels',
                      'status', 'host']
        for field in pod_fields:
            self.assertIn(field, pod)

    def test_one(self):
        pod = obj_utils.create_test_pod(self.context)
        response = self.get_json('/pods')
        self.assertEqual(pod.uuid, response['pods'][0]["uuid"])
        self._assert_pod_fields(response['pods'][0])

    def test_get_one(self):
        pod = obj_utils.create_test_pod(self.context)
        response = self.get_json(
            '/pods/%s/%s' % (pod['uuid'], pod['bay_uuid']))
        self.assertEqual(pod.uuid, response['uuid'])
        self._assert_pod_fields(response)

    def test_get_one_by_name(self):
        pod = obj_utils.create_test_pod(self.context)
        response = self.get_json(
            '/pods/%s/%s' % (pod['name'], pod['bay_uuid']))
        self.assertEqual(pod.uuid, response['uuid'])
        self._assert_pod_fields(response)

    def test_get_one_by_name_not_found(self):
        response = self.get_json(
            '/pods/not_found/5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_get_one_by_name_multiple_pod(self):
        obj_utils.create_test_pod(self.context, name='test_pod',
                                  uuid=utils.generate_uuid())
        obj_utils.create_test_pod(self.context, name='test_pod',
                                  uuid=utils.generate_uuid())
        response = self.get_json(
            '/pods/test_pod/5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            expect_errors=True)
        self.assertEqual(409, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_get_all_with_pagination_marker(self):
        pod_list = []
        for id_ in range(4):
            pod = obj_utils.create_test_pod(self.context, id=id_,
                                            uuid=utils.generate_uuid())
            pod_list.append(pod.uuid)

        response = self.get_json('/pods?limit=3&marker=%s' % pod_list[2])
        self.assertEqual(1, len(response['pods']))
        self.assertEqual(pod_list[-1], response['pods'][0]['uuid'])

    def test_detail(self):
        pod = obj_utils.create_test_pod(self.context)
        response = self.get_json('/pods/detail')
        self.assertEqual(pod.uuid, response['pods'][0]["uuid"])
        self._assert_pod_fields(response['pods'][0])

    def test_detail_with_pagination_marker(self):
        pod_list = []
        for id_ in range(4):
            pod = obj_utils.create_test_pod(self.context, id=id_,
                                            uuid=utils.generate_uuid())
            pod_list.append(pod.uuid)

        response = self.get_json('/pods/detail?limit=3&marker=%s'
                                 % pod_list[2])
        self.assertEqual(1, len(response['pods']))
        self.assertEqual(pod_list[-1], response['pods'][0]['uuid'])
        self._assert_pod_fields(response['pods'][0])

    def test_detail_against_single(self):
        pod = obj_utils.create_test_pod(self.context)
        response = self.get_json('/pods/%s/detail' % pod['uuid'],
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_many(self):
        pod_list = []
        for id_ in range(5):
            pod = obj_utils.create_test_pod(self.context, id=id_,
                                            uuid=utils.generate_uuid())
            pod_list.append(pod.uuid)
        response = self.get_json('/pods')
        self.assertEqual(len(pod_list), len(response['pods']))
        uuids = [p['uuid'] for p in response['pods']]
        self.assertEqual(sorted(pod_list), sorted(uuids))

    def test_links(self):
        uuid = utils.generate_uuid()
        obj_utils.create_test_pod(self.context, id=1, uuid=uuid)
        response = self.get_json(
            '/pods/%s/%s' % (uuid, '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'))
        self.assertIn('links', response.keys())
        self.assertEqual(2, len(response['links']))
        self.assertIn(uuid, response['links'][0]['href'])

    def test_collection_links(self):
        for id_ in range(5):
            obj_utils.create_test_pod(self.context, id=id_,
                                      uuid=utils.generate_uuid())
        response = self.get_json('/pods/?limit=3')
        self.assertEqual(3, len(response['pods']))

        next_marker = response['pods'][-1]['uuid']
        self.assertIn(next_marker, response['next'])

    def test_collection_links_default_limit(self):
        cfg.CONF.set_override('max_limit', 3, 'api')
        for id_ in range(5):
            obj_utils.create_test_pod(self.context, id=id_,
                                      uuid=utils.generate_uuid())
        response = self.get_json('/pods')
        self.assertEqual(3, len(response['pods']))

        next_marker = response['pods'][-1]['uuid']
        self.assertIn(next_marker, response['next'])


class TestPatch(api_base.FunctionalTest):

    def setUp(self):
        super(TestPatch, self).setUp()
        obj_utils.create_test_bay(self.context)
        self.pod = obj_utils.create_test_pod(self.context,
                                             desc='pod_example_A_desc',
                                             status='Running')

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        new_desc = 'pod_example_B_desc'
        response = self.get_json(
            '/pods/%s/%s' % (self.pod.uuid, self.pod.bay_uuid))
        self.assertNotEqual(new_desc, response['desc'])

        response = self.patch_json(
            '/pods/%s/%s' % (self.pod.uuid, self.pod.bay_uuid),
            [{'path': '/desc', 'value': new_desc,
              'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json(
            '/pods/%s/%s' % (self.pod.uuid, self.pod.bay_uuid))
        self.assertEqual(new_desc, response['desc'])
        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)

    def test_replace_bay_uuid(self):
        another_bay = obj_utils.create_test_bay(self.context,
                                                uuid=utils.generate_uuid())
        response = self.patch_json(
            '/pods/%s/%s' % (self.pod.uuid, self.pod.bay_uuid),
            [{'path': '/bay_uuid',
              'value': another_bay.uuid,
              'op': 'replace'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

    def test_replace_non_existent_bay_uuid(self):
        response = self.patch_json('/pods/%s' % self.pod.uuid,
                                   [{'path': '/bay_uuid',
                                     'value': utils.generate_uuid(),
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['error_message'])

    def test_replace_internal_field(self):
        response = self.patch_json(
            '/pods/%s' % self.pod.uuid,
            [{'path': '/labels', 'value': {}, 'op': 'replace'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['error_message'])

    def test_replace_non_existent_pod(self):
        response = self.patch_json(
            '/pods/%s/%s' % (utils.generate_uuid(), self.pod.bay_uuid),
            [{'path': '/desc',
              'value': 'pod_example_B_desc',
              'op': 'replace'}],
            expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(rpcapi.API, 'pod_update')
    @mock.patch.object(api_pod.Pod, 'parse_manifest')
    def test_replace_with_manifest(self, parse_manifest, pod_update):
        response = self.patch_json(
            '/pods/%s/%s' % (self.pod.uuid, self.pod.bay_uuid),
            [{'path': '/manifest',
              'value': '{}',
              'op': 'replace'}])
        self.assertEqual(200, response.status_int)
        self.assertEqual('application/json', response.content_type)
        parse_manifest.assert_called_once_with()
        self.assertTrue(pod_update.is_called)

    def test_add_non_existent_property(self):
        response = self.patch_json(
            '/pods/%s' % self.pod.uuid,
            [{'path': '/foo', 'value': 'bar', 'op': 'add'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_remove_ok(self):
        response = self.get_json(
            '/pods/%s/%s' % (self.pod.uuid, self.pod.bay_uuid))
        self.assertIsNotNone(response['desc'])

        response = self.patch_json(
            '/pods/%s/%s' % (self.pod.uuid, self.pod.bay_uuid),
            [{'path': '/desc', 'op': 'remove'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json(
            '/pods/%s/%s' % (self.pod.uuid, self.pod.bay_uuid))
        self.assertIsNone(response['desc'])

    def test_remove_uuid(self):
        response = self.patch_json('/pods/%s' % self.pod.uuid,
                                   [{'path': '/uuid', 'op': 'remove'}],
                                   expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_remove_bay_uuid(self):
        response = self.patch_json('/pods/%s' % self.pod.uuid,
                                   [{'path': '/bay_uuid', 'op': 'remove'}],
                                   expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_remove_internal_field(self):
        response = self.patch_json('/pods/%s' % self.pod.uuid,
                                   [{'path': '/labels', 'op': 'remove'}],
                                   expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_remove_non_existent_property(self):
        response = self.patch_json(
            '/pods/%s' % self.pod.uuid,
            [{'path': '/non-existent', 'op': 'remove'}],
            expect_errors=True)
        self.assertEqual(400, response.status_code)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_name(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json(
            '/pods/%s/%s' % (self.pod.name, self.pod.bay_uuid),
            [{'path': '/desc', 'op': 'remove'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json(
            '/pods/%s/%s' % (self.pod.uuid, self.pod.bay_uuid))
        self.assertEqual('pod1', response['name'])
        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_name_not_found(self, mock_utcnow):
        name = 'not_found'
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json('/pods/%s/%s' % (name, self.pod.bay_uuid),
                                   [{'path': '/desc', 'op': 'remove'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(404, response.status_code)

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_name_multiple_pod(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        obj_utils.create_test_pod(self.context, name='test_pod',
                                  uuid=utils.generate_uuid())
        obj_utils.create_test_pod(self.context, name='test_pod',
                                  uuid=utils.generate_uuid())

        response = self.patch_json('/pods/test_pod',
                                   [{'path': '/desc', 'op': 'remove'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)


class TestPost(api_base.FunctionalTest):

    def setUp(self):
        super(TestPost, self).setUp()
        obj_utils.create_test_bay(self.context)
        p = mock.patch.object(rpcapi.API, 'pod_create')
        self.mock_pod_create = p.start()
        self.mock_pod_create.side_effect = self._simulate_rpc_pod_create
        self.addCleanup(p.stop)
        p = mock.patch('magnum.objects.BayModel.get_by_uuid')
        self.mock_baymodel_get_by_uuid = p.start()
        self.mock_baymodel_get_by_uuid.return_value.coe = 'kubernetes'
        self.addCleanup(p.stop)

    def _simulate_rpc_pod_create(self, pod):
        pod.create()
        return pod

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_pod(self, mock_utcnow):
        pdict = apiutils.pod_post_data()
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.post_json('/pods', pdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        # Check location header
        self.assertIsNotNone(response.location)
        expected_location = '/v1/pods/%s' % pdict['uuid']
        self.assertEqual(expected_location,
                         urlparse.urlparse(response.location).path)
        self.assertEqual(pdict['uuid'], response.json['uuid'])
        self.assertNotIn('updated_at', response.json.keys)
        return_created_at = timeutils.parse_isotime(
            response.json['created_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_created_at)

    def test_create_pod_set_project_id_and_user_id(self):
        pdict = apiutils.pod_post_data()

        def _simulate_rpc_pod_create(pod):
            self.assertEqual(self.context.project_id, pod.project_id)
            self.assertEqual(self.context.user_id, pod.user_id)
            pod.create()
            return pod
        self.mock_pod_create.side_effect = _simulate_rpc_pod_create

        self.post_json('/pods', pdict)

    def test_create_pod_doesnt_contain_id(self):
        with mock.patch.object(self.dbapi, 'create_pod',
                               wraps=self.dbapi.create_pod) as cc_mock:
            pdict = apiutils.pod_post_data(desc='pod_example_A_desc')
            response = self.post_json('/pods', pdict)
            self.assertEqual(pdict['desc'], response.json['desc'])
            cc_mock.assert_called_once_with(mock.ANY)
            # Check that 'id' is not in first arg of positional args
            self.assertNotIn('id', cc_mock.call_args[0][0])

    def test_create_pod_generate_uuid(self):
        pdict = apiutils.pod_post_data()
        del pdict['uuid']

        response = self.post_json('/pods', pdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(pdict['desc'], response.json['desc'])
        self.assertTrue(utils.is_uuid_like(response.json['uuid']))

    def test_create_pod_no_bay_uuid(self):
        pdict = apiutils.pod_post_data()
        del pdict['bay_uuid']
        response = self.post_json('/pods', pdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)

    def test_create_pod_with_non_existent_bay_uuid(self):
        pdict = apiutils.pod_post_data(bay_uuid=utils.generate_uuid())
        response = self.post_json('/pods', pdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_create_pod_with_invalid_manifest(self):
        pdict = apiutils.pod_post_data()
        pdict['manifest'] = 'wrong manifest'
        response = self.post_json('/pods', pdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_create_pod_no_manifest(self):
        pdict = apiutils.pod_post_data()
        del pdict['manifest']
        response = self.post_json('/pods', pdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_create_pod_no_id_in_manifest(self):
        pdict = apiutils.pod_post_data()
        pdict['manifest'] = {}
        response = self.post_json('/pods', pdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])


class TestDelete(api_base.FunctionalTest):

    def setUp(self):
        super(TestDelete, self).setUp()
        obj_utils.create_test_bay(self.context)
        self.pod = obj_utils.create_test_pod(self.context)
        p = mock.patch.object(rpcapi.API, 'pod_delete')
        self.mock_pod_delete = p.start()
        self.mock_pod_delete.side_effect = self._simulate_rpc_pod_delete
        self.addCleanup(p.stop)

    def _simulate_rpc_pod_delete(self, pod_uuid):
        pod = objects.Pod.get_by_uuid(self.context, pod_uuid)
        pod.destroy()

    def test_delete_pod(self):
        self.delete('/pods/%s/%s' % (self.pod.uuid, self.pod.bay_uuid))
        response = self.get_json(
            '/pods/%s/%s' % (self.pod.uuid, self.pod.bay_uuid),
            expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_delete_pod_by_name(self):
        self.delete('/pods/%s/%s' % (self.pod.name, self.pod.bay_uuid))
        response = self.get_json(
            '/pods/%s/%s' % (self.pod.name, self.pod.bay_uuid),
            expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_delete_pod_by_name_not_found(self):
        response = self.delete(
            '/pods/not_found/5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_delete_multiple_pod_by_name(self):
        obj_utils.create_test_pod(self.context, name='test_pod',
                                  uuid=utils.generate_uuid())
        obj_utils.create_test_pod(self.context, name='test_pod',
                                  uuid=utils.generate_uuid())
        response = self.delete(
            '/pods/test_pod/5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            expect_errors=True)
        self.assertEqual(409, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_delete_pod_not_found(self):
        uuid = utils.generate_uuid()
        response = self.delete(
            '/pods/%s/%s' % (uuid, self.pod.bay_uuid),
            expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


class TestPodPolicyEnforcement(api_base.FunctionalTest):

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules({rule: 'project:non_fake'})
        exc = self.assertRaises(policy.PolicyNotAuthorized,
                                func, *arg, **kwarg)
        self.assertTrue(exc.message.startswith(rule))
        self.assertTrue(exc.message.endswith('disallowed by policy'))

    def test_policy_disallow_get_all(self):
        self._common_policy_check(
            'pod:get_all', self.get_json, '/pods')

    def test_policy_disallow_get_one(self):
        self._common_policy_check(
            'pod:get', self.get_json, '/pods/111-222-333')

    def test_policy_disallow_detail(self):
        self._common_policy_check(
            'pod:detail', self.get_json, '/pods/111-222-333/detail')

    def test_policy_disallow_update(self):
        pod = obj_utils.create_test_pod(self.context,
                                        desc='test pod',
                                        uuid=utils.generate_uuid())

        self._common_policy_check(
            'pod:update', self.patch_json,
            '/pods/%s' % pod.uuid,
            [{'path': '/desc', 'value': 'new test pod', 'op': 'replace'}])

    def test_policy_disallow_create(self):
        pdict = apiutils.pod_post_data()
        self._common_policy_check(
            'pod:create', self.post_json, '/pods', pdict)

    def test_policy_disallow_delete(self):
        pod = obj_utils.create_test_pod(self.context,
                                        name='test_pod',
                                        uuid=utils.generate_uuid())
        self._common_policy_check(
            'pod:delete', self.delete,
            '/pods/%s' % pod.uuid)
