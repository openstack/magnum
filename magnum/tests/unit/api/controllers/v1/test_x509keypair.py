# Copyright 2015 NEC Corporation.  All rights reserved.
#
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
from oslo_utils import timeutils
from six.moves.urllib import parse as urlparse

from magnum.api.controllers.v1 import x509keypair as api_x509keypair
from magnum.common import utils
from magnum.conductor import api as rpcapi
from magnum import objects
from magnum.tests import base
from magnum.tests.unit.api import base as api_base
from magnum.tests.unit.api import utils as apiutils
from magnum.tests.unit.objects import utils as obj_utils


class TestX509KeyPairObject(base.TestCase):

    def test_x509keypair_init(self):
        x509keypair_dict = apiutils.x509keypair_post_data(bay_uuid=None)
        x509keypair = api_x509keypair.X509KeyPair(**x509keypair_dict)
        self.assertEqual('certificate', x509keypair.certificate)


class TestListX509KeyPair(api_base.FunctionalTest):

    def setUp(self):
        super(TestListX509KeyPair, self).setUp()
        self.bay = obj_utils.create_test_bay(self.context)

    def test_empty(self):
        response = self.get_json('/x509keypairs')
        self.assertEqual([], response['x509keypairs'])

    def test_one(self):
        x509keypair = obj_utils.create_test_x509keypair(self.context)
        response = self.get_json('/x509keypairs')
        self.assertEqual(x509keypair.uuid, response['x509keypairs'][0]["uuid"])
        self.assertIn('name', response['x509keypairs'][0])
        self.assertIn('bay_uuid', response['x509keypairs'][0])
        self.assertIn('certificate', response['x509keypairs'][0])
        self.assertIn('private_key', response['x509keypairs'][0])

    def test_get_one(self):
        x509keypair = obj_utils.create_test_x509keypair(self.context)
        response = self.get_json('/x509keypairs/%s' % x509keypair['uuid'])
        self.assertEqual(x509keypair.uuid, response['uuid'])
        self.assertIn('name', response)
        self.assertIn('bay_uuid', response)
        self.assertIn('certificate', response)
        self.assertIn('private_key', response)

    def test_get_one_by_name(self):
        x509keypair = obj_utils.create_test_x509keypair(self.context)
        response = self.get_json('/x509keypairs/%s' % x509keypair['name'])
        self.assertEqual(x509keypair.uuid, response['uuid'])
        self.assertIn('name', response)
        self.assertIn('bay_uuid', response)
        self.assertIn('certificate', response)
        self.assertIn('private_key', response)

    def test_get_one_by_name_not_found(self):
        response = self.get_json(
            '/x509keypairs/not_found',
            expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_get_one_by_name_multiple_x509keypair(self):
        obj_utils.create_test_x509keypair(self.context,
                                          name='test_x509keypair',
                                          uuid=utils.generate_uuid())
        obj_utils.create_test_x509keypair(self.context,
                                          name='test_x509keypair',
                                          uuid=utils.generate_uuid())
        response = self.get_json('/x509keypairs/test_x509keypair',
                                 expect_errors=True)
        self.assertEqual(409, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_detail(self):
        x509keypair = obj_utils.create_test_x509keypair(self.context)
        response = self.get_json('/x509keypairs/detail')
        self.assertEqual(x509keypair.uuid, response['x509keypairs'][0]["uuid"])
        self.assertIn('name', response['x509keypairs'][0])
        self.assertIn('bay_uuid', response['x509keypairs'][0])
        self.assertIn('certificate', response['x509keypairs'][0])
        self.assertIn('private_key', response['x509keypairs'][0])

    def test_detail_against_single(self):
        x509keypair = obj_utils.create_test_x509keypair(self.context)
        response = self.get_json(
            '/x509keypairs/%s/detail' % x509keypair['uuid'],
            expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_many(self):
        keypair_list = []
        for id_ in range(5):
            x509keypair = obj_utils.create_test_x509keypair(
                self.context, id=id_,
                uuid=utils.generate_uuid())
            keypair_list.append(x509keypair.uuid)
        response = self.get_json('/x509keypairs')
        self.assertEqual(len(keypair_list), len(response['x509keypairs']))
        uuids = [b['uuid'] for b in response['x509keypairs']]
        self.assertEqual(sorted(keypair_list), sorted(uuids))

    def test_links(self):
        uuid = utils.generate_uuid()
        obj_utils.create_test_x509keypair(self.context, id=1, uuid=uuid)
        response = self.get_json('/x509keypairs/%s' % uuid)
        self.assertIn('links', response.keys())
        self.assertEqual(2, len(response['links']))
        self.assertIn(uuid, response['links'][0]['href'])
        for l in response['links']:
            bookmark = l['rel'] == 'bookmark'
            self.assertTrue(self.validate_link(l['href'], bookmark=bookmark))

    def test_collection_links(self):
        for id_ in range(5):
            obj_utils.create_test_x509keypair(self.context, id=id_,
                                              uuid=utils.generate_uuid())
        response = self.get_json('/x509keypairs/?limit=3')
        self.assertEqual(3, len(response['x509keypairs']))

        next_marker = response['x509keypairs'][-1]['uuid']
        self.assertIn(next_marker, response['next'])

    def test_collection_links_default_limit(self):
        cfg.CONF.set_override('max_limit', 3, 'api')
        for id_ in range(5):
            obj_utils.create_test_x509keypair(self.context, id=id_,
                                              uuid=utils.generate_uuid())
        response = self.get_json('/x509keypairs')
        self.assertEqual(3, len(response['x509keypairs']))

        next_marker = response['x509keypairs'][-1]['uuid']
        self.assertIn(next_marker, response['next'])


class TestPost(api_base.FunctionalTest):

    def setUp(self):
        super(TestPost, self).setUp()
        self.bay = obj_utils.create_test_bay(self.context)
        p = mock.patch.object(rpcapi.API, 'x509keypair_create')
        self.mock_x509keypair_create = p.start()
        self.mock_x509keypair_create.side_effect = \
            self._simulate_rpc_x509keypair_create
        self.addCleanup(p.stop)

    def _simulate_rpc_x509keypair_create(self, x509keypair):
        x509keypair.create()
        return x509keypair

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_x509keypair(self, mock_utcnow):
        cdict = apiutils.x509keypair_post_data()
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.post_json('/x509keypairs', cdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        # Check location header
        self.assertIsNotNone(response.location)
        expected_location = '/v1/x509keypairs/%s' % cdict['uuid']
        self.assertEqual(urlparse.urlparse(response.location).path,
                         expected_location)
        self.assertEqual(cdict['uuid'], response.json['uuid'])
        self.assertNotIn('updated_at', response.json.keys)
        return_created_at = timeutils.parse_isotime(
            response.json['created_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_created_at)

    def test_create_x509keypair_set_project_id_and_user_id(self):
        cdict = apiutils.x509keypair_post_data()

        def _simulate_keypair_create(x509keypair):
            self.assertEqual(x509keypair.project_id, self.context.project_id)
            self.assertEqual(x509keypair.user_id, self.context.user_id)
            x509keypair.create()
            return x509keypair
        self.mock_x509keypair_create.side_effect = _simulate_keypair_create

        self.post_json('/x509keypairs', cdict)

    def test_create_x509keypair_doesnt_contain_id(self):
        with mock.patch.object(self.dbapi, 'create_x509keypair',
                               wraps=self.dbapi.create_x509keypair) as cc_mock:
            cdict = apiutils.x509keypair_post_data(
                name='x509keypair_example_A')
            response = self.post_json('/x509keypairs', cdict)
            self.assertEqual(cdict['name'], response.json['name'])
            cc_mock.assert_called_once_with(mock.ANY)
            # Check that 'id' is not in first arg of positional args
            self.assertNotIn('id', cc_mock.call_args[0][0])

    def test_create_x509keypair_generate_uuid(self):
        cdict = apiutils.x509keypair_post_data()
        del cdict['uuid']

        response = self.post_json('/x509keypairs', cdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(cdict['name'], response.json['name'])
        self.assertTrue(utils.is_uuid_like(response.json['uuid']))

    def test_create_x509keypair_no_bay_uuid(self):
        cdict = apiutils.x509keypair_post_data()
        del cdict['bay_uuid']
        response = self.post_json('/x509keypairs', cdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)

    def test_create_x509keypair_with_non_existent_bay_uuid(self):
        cdict = apiutils.x509keypair_post_data(bay_uuid=utils.generate_uuid())
        response = self.post_json('/x509keypairs', cdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_create_x509keypair_with_bay_name(self):
        cdict = apiutils.x509keypair_post_data(bay_uuid=self.bay.name)
        response = self.post_json('/x509keypairs', cdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)


class TestDelete(api_base.FunctionalTest):

    def setUp(self):
        super(TestDelete, self).setUp()
        self.bay = obj_utils.create_test_bay(self.context)
        self.x509keypair = obj_utils.create_test_x509keypair(self.context)
        p = mock.patch.object(rpcapi.API, 'x509keypair_delete')
        self.mock_x509keypair_delete = p.start()
        self.mock_x509keypair_delete.side_effect = \
            self._simulate_rpc_x509keypair_delete
        self.addCleanup(p.stop)

    def _simulate_rpc_x509keypair_delete(self, x509keypair_uuid):
        x509keypair = objects.X509KeyPair.get_by_uuid(self.context,
                                                      x509keypair_uuid)
        x509keypair.destroy()

    def test_delete_x509keypair(self):
        self.delete('/x509keypairs/%s' % self.x509keypair.uuid)
        response = self.get_json('/x509keypairs/%s' % self.x509keypair.uuid,
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_delete_x509keypair_not_found(self):
        uuid = utils.generate_uuid()
        response = self.delete('/x509keypairs/%s' % uuid, expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_delete_x509keypair_with_name_not_found(self):
        response = self.delete('/x509keypairs/not_found', expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_delete_x509keypair_with_name(self):
        response = self.delete('/x509keypairs/%s' % self.x509keypair.name,
                               expect_errors=True)
        self.assertEqual(204, response.status_int)

    def test_delete_multiple_x509keypair_by_name(self):
        obj_utils.create_test_x509keypair(self.context,
                                          name='test_x509keypair',
                                          uuid=utils.generate_uuid())
        obj_utils.create_test_x509keypair(self.context,
                                          name='test_x509keypair',
                                          uuid=utils.generate_uuid())
        response = self.delete('/x509keypairs/test_x509keypair',
                               expect_errors=True)
        self.assertEqual(409, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])
