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
from six.moves.urllib import parse as urlparse
from wsme import types as wtypes

from magnum.api.controllers.v1 import service as api_service
from magnum.common.pythonk8sclient.swagger_client import rest
from magnum.common import utils
from magnum.conductor import api as rpcapi
from magnum.tests import base
from magnum.tests.unit.api import base as api_base
from magnum.tests.unit.api import utils as apiutils
from magnum.tests.unit.objects import utils as obj_utils


class TestServiceObject(base.TestCase):

    def test_service_init(self):
        service_dict = apiutils.service_post_data(bay_uuid=None)
        del service_dict['uuid']
        service = api_service.Service(**service_dict)
        self.assertEqual(wtypes.Unset, service.uuid)


class TestListService(api_base.FunctionalTest):

    def setUp(self):
        super(TestListService, self).setUp()
        bay = obj_utils.create_test_bay(self.context)
        obj_utils.create_test_baymodel(self.context, uuid=bay.baymodel_id,
                                       coe='kubernetes')
        self.service = obj_utils.create_test_service(self.context)

    @mock.patch.object(rpcapi.API, 'service_list')
    def test_empty(self, mock_pod_list):
        mock_pod_list.return_value = []
        response = self.get_json('/services?bay_ident=5d12f6fd-a196-4bf0-ae4c-'
                                 '1f639a523a52')
        self.assertEqual([], response['services'])

    def _assert_service_fields(self, service):
        service_fields = ['name', 'bay_uuid', 'name', 'labels', 'selector',
                          'ip', 'ports']
        for field in service_fields:
            self.assertIn(field, service)

    @mock.patch.object(rpcapi.API, 'service_show')
    def test_one(self, mock_service_show):
        service = obj_utils.create_test_service(self.context)
        mock_service_show.return_value = service
        response = self.get_json('/services/%s/%s' % (service['uuid'],
                                                      service['bay_uuid']))
        self.assertEqual(service.uuid, response["uuid"])
        self._assert_service_fields(response)

    @mock.patch.object(rpcapi.API, 'service_show')
    def test_get_one(self, mock_service_show):
        service = obj_utils.create_test_service(self.context)
        mock_service_show.return_value = service
        response = self.get_json(
            '/services/%s/%s' % (service['uuid'], service['bay_uuid']))
        self.assertEqual(service.uuid, response['uuid'])
        self._assert_service_fields(response)

    @mock.patch.object(rpcapi.API, 'service_show')
    def test_get_one_by_name(self, mock_service_show):
        service = obj_utils.create_test_service(self.context)
        mock_service_show.return_value = service
        response = self.get_json(
            '/services/%s/%s' % (service['name'], service['bay_uuid']))
        self.assertEqual(service.uuid, response['uuid'])
        self._assert_service_fields(response)

    @mock.patch.object(rpcapi.API, 'service_show')
    def test_get_one_by_name_not_found(self, mock_service_show):
        err = rest.ApiException(status=404)
        mock_service_show.side_effect = err
        response = self.get_json(
            '/services/not_found/5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            expect_errors=True)
        self.assertEqual(500, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(rpcapi.API, 'service_show')
    def test_get_one_by_name_multiple_service(self, mock_service_show):
        obj_utils.create_test_service(
            self.context, name='test_service',
            uuid=utils.generate_uuid())
        obj_utils.create_test_service(
            self.context, name='test_service',
            uuid=utils.generate_uuid())
        err = rest.ApiException(status=500)
        mock_service_show.side_effect = err
        response = self.get_json(
            '/services/test_service/5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            expect_errors=True)
        self.assertEqual(500, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(rpcapi.API, 'service_list')
    def test_get_all_with_pagination_marker(self, mock_service_list):
        service_list = []
        for id_ in range(4):
            service = obj_utils.create_test_service(self.context, id=id_,
                                                    uuid=utils.generate_uuid())
            service_list.append(service.uuid)

        mock_service_list.return_value = [service]
        response = self.get_json('/services?limit=3&marker=%s&bay_ident='
                                 '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'
                                 % service_list[2])
        self.assertEqual(1, len(response['services']))
        self.assertEqual(service_list[-1], response['services'][0]['uuid'])

    @mock.patch.object(rpcapi.API, 'service_list')
    def test_detail(self, mock_service_list):
        service = obj_utils.create_test_service(self.context)
        mock_service_list.return_value = [service]
        response = self.get_json('/services/detail?bay_ident=5d12f6fd-a196-'
                                 '4bf0-ae4c-1f639a523a52')
        self.assertEqual(service.uuid, response['services'][0]["uuid"])
        self._assert_service_fields(response['services'][0])

    @mock.patch.object(rpcapi.API, 'service_list')
    def test_detail_with_pagination_marker(self, mock_service_list):
        service_list = []
        for id_ in range(4):
            service = obj_utils.create_test_service(self.context, id=id_,
                                                    uuid=utils.generate_uuid())
            service_list.append(service.uuid)

        mock_service_list.return_value = [service]
        response = self.get_json('/services/detail?limit=3&marker=%s&bay_ident'
                                 '=5d12f6fd-a196-4bf0-ae4c-1f639a523a52'
                                 % service_list[2])
        self.assertEqual(1, len(response['services']))
        self.assertEqual(service_list[-1], response['services'][0]['uuid'])
        self._assert_service_fields(response['services'][0])

    @mock.patch.object(rpcapi.API, 'service_list')
    def test_detail_against_single(self, mock_service_list):
        service = obj_utils.create_test_service(self.context)
        mock_service_list.return_value = [service]
        response = self.get_json('/services/%s/detail' % service['uuid'],
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)

    @mock.patch.object(rpcapi.API, 'service_list')
    def test_many(self, mock_service_list):
        service_list = []
        for id_ in range(1):
            service = obj_utils.create_test_service(self.context, id=id_,
                                                    uuid=utils.generate_uuid())
            service_list.append(service.uuid)
        mock_service_list.return_value = [service]
        response = self.get_json('/services?bay_ident=5d12f6fd-a196-4bf0-ae4c-'
                                 '1f639a523a52')
        self.assertEqual(len(service_list), len(response['services']))
        uuids = [s['uuid'] for s in response['services']]
        self.assertEqual(sorted(service_list), sorted(uuids))

    @mock.patch.object(rpcapi.API, 'service_show')
    def test_links(self, mock_service_show):
        uuid = utils.generate_uuid()
        service = obj_utils.create_test_service(self.context, id=1, uuid=uuid)
        mock_service_show.return_value = service
        response = self.get_json(
            '/services/%s/%s' % (uuid, '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'))
        self.assertIn('links', response.keys())
        self.assertEqual(2, len(response['links']))
        self.assertIn(uuid, response['links'][0]['href'])

    @mock.patch.object(rpcapi.API, 'service_list')
    def test_collection_links(self, mock_service_list):
        for id_ in range(5):
            service = obj_utils.create_test_service(
                self.context, id=id_,
                uuid=utils.generate_uuid())
        mock_service_list.return_value = [service]
        response = self.get_json('/services/?limit=1&bay_ident=5d12f6fd-a196-'
                                 '4bf0-ae4c-1f639a523a52')
        self.assertEqual(1, len(response['services']))

        next_marker = response['services'][-1]['uuid']
        self.assertIn(next_marker, response['next'])

    @mock.patch.object(rpcapi.API, 'service_list')
    def test_collection_links_default_limit(self, mock_service_list):
        cfg.CONF.set_override('max_limit', 3, 'api')
        for id_ in range(5):
            service = obj_utils.create_test_service(
                self.context, id=id_,
                uuid=utils.generate_uuid())
            mock_service_list.return_value = [service]
        response = self.get_json('/services?bay_ident=5d12f6fd-a196-4bf0-ae4c-'
                                 '1f639a523a52')
        self.assertEqual(1, len(response['services']))


class TestPatch(api_base.FunctionalTest):

    def setUp(self):
        super(TestPatch, self).setUp()
        self.bay = obj_utils.create_test_bay(self.context,
                                             uuid=utils.generate_uuid())
        obj_utils.create_test_baymodel(self.context, uuid=self.bay.baymodel_id,
                                       coe='kubernetes')
        self.bay2 = obj_utils.create_test_bay(self.context,
                                              uuid=utils.generate_uuid())
        self.service = obj_utils.create_test_service(self.context,
                                                     bay_uuid=self.bay.uuid)

    @mock.patch.object(rpcapi.API, 'service_update')
    def test_replace_bay_uuid(self, mock_service_update):
        self.service.manifest = '{"foo": "bar"}'
        mock_service_update.return_value = self.service
        mock_service_update.return_value.bay_uuid = self.bay2.uuid
        response = self.patch_json(
            '/services/%s/%s' % (self.service.uuid, self.service.bay_uuid),
            [{'path': '/bay_uuid',
              'value': self.bay2.uuid,
              'op': 'replace'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)

    @mock.patch.object(rpcapi.API, 'service_update')
    def test_replace_non_existent_bay_uuid(self, mock_service_update):
        err = rest.ApiException(status=400)
        mock_service_update.side_effect = err
        response = self.patch_json(
            '/services/%s/%s' % (self.service.uuid, self.service.bay_uuid),
            [{'path': '/bay_uuid',
              'value': utils.generate_uuid(),
              'op': 'replace'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(rpcapi.API, 'service_update')
    def test_replace_internal_field(self, mock_service_update):
        err = rest.ApiException(status=400)
        mock_service_update.side_effect = err
        response = self.patch_json(
            '/services/%s/%s' % (self.service.uuid, self.service.bay_uuid),
            [{'path': '/labels', 'value': {}, 'op': 'replace'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(rpcapi.API, 'service_update')
    def test_replace_non_existent_service(self, mock_service_update):
        err = rest.ApiException(status=404)
        mock_service_update.side_effect = err
        response = self.patch_json(
            '/services/%s?bay_ident=%s' %
            (utils.generate_uuid(), '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'),
            [{'path': '/bay_uuid',
              'value': self.bay2.uuid,
              'op': 'replace'}],
            expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(rpcapi.API, 'service_update')
    @mock.patch.object(api_service.Service, 'parse_manifest')
    def test_replace_with_manifest(self, parse_manifest, service_update):
        service_update.return_value = self.service
        service_update.return_value.manifest = '{"foo": "bar"}'
        response = self.patch_json(
            '/services/%s/%s' % (self.service.uuid, self.service.bay_uuid),
            [{'path': '/manifest',
              'value': '{"foo": "bar"}',
              'op': 'replace'}])
        self.assertEqual(200, response.status_int)
        self.assertEqual('application/json', response.content_type)
        parse_manifest.assert_called_once_with()
        self.assertTrue(service_update.is_called)

    @mock.patch.object(rpcapi.API, 'service_update')
    def test_add_non_existent_property(self, mock_service_update):
        response = self.patch_json(
            '/services/%s/%s' % (self.service.uuid, self.service.bay_uuid),
            [{'path': '/foo', 'value': 'bar', 'op': 'add'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_remove_uuid(self):
        response = self.patch_json(
            '/services/%s/%s' % (self.service.uuid, self.service.bay_uuid),
            [{'path': '/uuid', 'op': 'remove'}],
            expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_remove_bay_uuid(self):
        response = self.patch_json(
            '/services/%s/%s' % (self.service.uuid, self.service.bay_uuid),
            [{'path': '/bay_uuid', 'op': 'remove'}],
            expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_remove_internal_field(self):
        response = self.patch_json(
            '/services/%s/%s' % (self.service.uuid, self.service.bay_uuid),
            [{'path': '/labels', 'op': 'remove'}],
            expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_remove_non_existent_property(self):
        response = self.patch_json(
            '/services/%s/%s' % (self.service.uuid, self.service.bay_uuid),
            [{'path': '/non-existent', 'op': 'remove'}],
            expect_errors=True)
        self.assertEqual(400, response.status_code)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(rpcapi.API, 'service_show')
    @mock.patch.object(rpcapi.API, 'service_update')
    @mock.patch.object(api_service.Service, 'parse_manifest')
    def test_replace_ok_by_name(self, parse_manifest,
                                mock_service_update,
                                mock_service_show):
        self.service.manifest = '{"foo": "bar"}'
        mock_service_update.return_value = self.service

        response = self.patch_json(
            '/services/%s/%s' % (self.service.name, self.service.bay_uuid),
            [{'path': '/manifest',
              'value': '{"foo": "bar"}',
              'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)
        parse_manifest.assert_called_once_with()
        self.assertTrue(mock_service_update.is_called)

        mock_service_show.return_value = self.service
        response = self.get_json(
            '/services/%s/%s' % (self.service.uuid,
                                 self.service.bay_uuid), expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_name_not_found(self, mock_utcnow):
        name = 'not_found'
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json(
            '/services/%s/%s' % (name, self.service.bay_uuid),
            [{'path': '/bay_uuid',
              'value': self.bay2.uuid,
              'op': 'replace'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_name_multiple_service(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        obj_utils.create_test_service(self.context, name='test_service',
                                      uuid=utils.generate_uuid())
        obj_utils.create_test_service(self.context, name='test_service',
                                      uuid=utils.generate_uuid())

        response = self.patch_json(
            '/services/test_service?bay_ident=%s' % self.bay.uuid,
            [{'path': '/bay_uuid',
              'value': self.bay2.uuid,
              'op': 'replace'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)


class TestPost(api_base.FunctionalTest):

    def setUp(self):
        super(TestPost, self).setUp()
        obj_utils.create_test_bay(self.context)
        self.service_obj = obj_utils.create_test_service(self.context)
        p = mock.patch.object(rpcapi.API, 'service_create')
        self.mock_service_create = p.start()
        self.mock_service_create.return_value = self.service_obj
        self.mock_service_create.side_effect = (
            self._simulate_rpc_service_create)
        self.addCleanup(p.stop)
        p = mock.patch('magnum.objects.BayModel.get_by_uuid')
        self.mock_baymodel_get_by_uuid = p.start()
        self.mock_baymodel_get_by_uuid.return_value.coe = 'kubernetes'
        self.addCleanup(p.stop)

    def _simulate_rpc_service_create(self, service):
        service.create()
        return service

    @mock.patch('oslo_utils.timeutils.utcnow')
    @mock.patch.object(rpcapi.API, 'service_create')
    def test_create_service(self, mock_service_create,
                            mock_utcnow):
        sdict = apiutils.service_post_data()
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        mock_service_create.return_value = self.service_obj
        response = self.post_json('/services', sdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        # Check location header
        self.assertIsNotNone(response.location)
        expected_location = '/v1/services/%s' % sdict['uuid']
        self.assertEqual(expected_location,
                         urlparse.urlparse(response.location).path)
        self.assertEqual(sdict['uuid'], response.json['uuid'])
        self.assertNotIn('updated_at', response.json.keys)

    def test_create_service_set_project_id_and_user_id(self):
        sdict = apiutils.service_post_data()

        def _simulate_rpc_service_create(service):
            self.assertEqual(service.project_id, self.context.project_id)
            self.assertEqual(service.user_id, self.context.user_id)
            return service
        self.mock_service_create.side_effect = _simulate_rpc_service_create

        self.post_json('/services', sdict)

    @mock.patch.object(rpcapi.API, 'service_create')
    def test_create_service_doesnt_contain_id(self, mock_service_create):
        sdict = apiutils.service_post_data()
        mock_service_create.return_value = self.service_obj
        response = self.post_json('/services', sdict)
        self.assertEqual('application/json', response.content_type)

    @mock.patch.object(rpcapi.API, 'service_create')
    def test_create_service_generate_uuid(self,
                                          mock_service_create):
        sdict = apiutils.service_post_data()
        del sdict['uuid']

        mock_service_create.return_value = self.service_obj
        response = self.post_json('/services', sdict,
                                  expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertTrue(utils.is_uuid_like(response.json['uuid']))

    def test_create_service_no_bay_uuid(self):
        sdict = apiutils.service_post_data()
        del sdict['bay_uuid']
        response = self.post_json('/services', sdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)

    def test_create_service_with_non_existent_bay_uuid(self):
        sdict = apiutils.service_post_data(bay_uuid=utils.generate_uuid())
        response = self.post_json('/services', sdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_create_service_no_manifest(self):
        sdict = apiutils.service_post_data()
        del sdict['manifest']
        response = self.post_json('/services', sdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_create_service_invalid_manifest(self):
        sdict = apiutils.service_post_data()
        sdict['manifest'] = 'wrong_manifest'
        response = self.post_json('/services', sdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_create_service_no_id_in_manifest(self):
        sdict = apiutils.service_post_data()
        sdict['manifest'] = {}
        response = self.post_json('/services', sdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])


class TestDelete(api_base.FunctionalTest):

    def setUp(self):
        super(TestDelete, self).setUp()
        bay = obj_utils.create_test_bay(self.context)
        obj_utils.create_test_baymodel(self.context, uuid=bay.baymodel_id,
                                       coe='kubernetes')
        self.service = obj_utils.create_test_service(self.context)

    @mock.patch.object(rpcapi.API, 'service_delete')
    @mock.patch.object(rpcapi.API, 'service_show')
    def test_delete_service(self, mock_service_show,
                            mock_service_delete):
        mock_service_delete.return_value = {}
        self.delete(
            '/services/%s/%s' % (self.service.uuid, self.service.bay_uuid))
        err = rest.ApiException(status=404)
        mock_service_show.side_effect = err
        response = self.get_json(
            '/services/%s/%s' % (self.service.uuid, self.service.bay_uuid),
            expect_errors=True)
        self.assertEqual(500, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(rpcapi.API, 'service_delete')
    @mock.patch.object(rpcapi.API, 'service_show')
    def test_delete_service_not_found(self, mock_service_show,
                                      mock_service_delete):
        uuid = utils.generate_uuid()
        err = rest.ApiException(status=404)
        mock_service_delete.side_effect = err
        response = self.delete(
            '/services/%s/%s' % (uuid, self.service.bay_uuid),
            expect_errors=True)
        self.assertEqual(500, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(rpcapi.API, 'service_delete')
    @mock.patch.object(rpcapi.API, 'service_show')
    def test_delete_service_with_name(self, mock_service_show,
                                      mock_service_delete):
        mock_service_delete.return_value = {}
        response = self.delete(
            '/services/%s/%s' % (self.service.name, self.service.bay_uuid),
            expect_errors=True)
        err = rest.ApiException(status=204)
        mock_service_show.side_effect = err
        response = self.get_json(
            '/services/%s/%s' % (self.service.uuid, self.service.bay_uuid),
            expect_errors=True)
        self.assertEqual(500, response.status_int)

    @mock.patch.object(rpcapi.API, 'service_delete')
    def test_delete_service_with_name_not_found(self,
                                                mock_service_delete):
        err = rest.ApiException(status=404)
        mock_service_delete.side_effect = err
        response = self.delete(
            '/services/not_found/5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            expect_errors=True)
        self.assertEqual(500, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(rpcapi.API, 'service_delete')
    def test_delete_multiple_service_by_name(self, mock_service_delete):
        obj_utils.create_test_service(self.context, name='test_service',
                                      uuid=utils.generate_uuid())
        obj_utils.create_test_service(self.context, name='test_service',
                                      uuid=utils.generate_uuid())
        err = rest.ApiException(status=409)
        mock_service_delete.side_effect = err
        response = self.delete(
            '/services/test_service/5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            expect_errors=True)
        self.assertEqual(500, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


class TestServiceEnforcement(api_base.FunctionalTest):

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules({rule: 'project:non_fake'})
        exc = self.assertRaises(policy.PolicyNotAuthorized,
                                func, *arg, **kwarg)
        self.assertTrue(exc.message.startswith(rule))
        self.assertTrue(exc.message.endswith('disallowed by policy'))

    def test_policy_disallow_get_all(self):
        self._common_policy_check(
            'service:get_all', self.get_json, '/services')

    def test_policy_disallow_get_one(self):
        self._common_policy_check(
            'service:get', self.get_json, '/services/111-222-333')

    def test_policy_disallow_detail(self):
        self._common_policy_check(
            'service:detail', self.get_json, '/services/111-222-333/detail')

    def test_policy_disallow_update(self):
        service = obj_utils.create_test_service(self.context,
                                                desc='test service',
                                                uuid=utils.generate_uuid())

        self._common_policy_check(
            'service:update', self.patch_json,
            '/services/%s' % service.uuid,
            [{'path': '/bay_uuid',
              'value': utils.generate_uuid(),
              'op': 'replace'}])

    def test_policy_disallow_create(self):
        pdict = apiutils.service_post_data()
        self._common_policy_check(
            'service:create', self.post_json, '/services', pdict)

    def test_policy_disallow_delete(self):
        service = obj_utils.create_test_service(self.context,
                                                desc='test_service',
                                                uuid=utils.generate_uuid())
        self._common_policy_check(
            'service:delete', self.delete,
            '/services/%s' % service.uuid)
