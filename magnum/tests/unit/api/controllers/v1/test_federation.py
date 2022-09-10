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

from oslo_config import cfg
from oslo_utils import uuidutils

from magnum.api.controllers.v1 import federation as api_federation
from magnum.conductor import api as rpcapi
import magnum.conf
from magnum import objects
from magnum.tests import base
from magnum.tests.unit.api import base as api_base
from magnum.tests.unit.api import utils as apiutils
from magnum.tests.unit.objects import utils as obj_utils

CONF = magnum.conf.CONF


class TestFederationObject(base.TestCase):
    def test_federation_init(self):
        fed_dict = apiutils.federation_post_data()
        fed_dict['uuid'] = uuidutils.generate_uuid()
        federation = api_federation.Federation(**fed_dict)
        self.assertEqual(fed_dict['uuid'], federation.uuid)


class TestListFederation(api_base.FunctionalTest):
    def setUp(self):
        super(TestListFederation, self).setUp()

    def test_empty(self):
        response = self.get_json('/federations')
        self.assertEqual(response['federations'], [])

    def test_one(self):
        federation = obj_utils.create_test_federation(
            self.context, uuid=uuidutils.generate_uuid())
        response = self.get_json('/federations')
        self.assertEqual(federation.uuid, response['federations'][0]['uuid'])

    def test_get_one(self):
        federation = obj_utils.create_test_federation(
            self.context, uuid=uuidutils.generate_uuid())
        response = self.get_json('/federations/%s' % federation['uuid'])
        self.assertEqual(federation.uuid, response['uuid'])

    def test_get_one_by_name(self):
        federation = obj_utils.create_test_federation(
            self.context, uuid=uuidutils.generate_uuid())
        response = self.get_json('/federations/%s' % federation['name'])
        self.assertEqual(federation.uuid, response['uuid'])

    def test_get_one_by_name_not_found(self):
        response = self.get_json('/federations/not_found', expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_get_one_by_uuid(self):
        temp_uuid = uuidutils.generate_uuid()
        federation = obj_utils.create_test_federation(self.context,
                                                      uuid=temp_uuid)
        response = self.get_json('/federations/%s' % temp_uuid)
        self.assertEqual(federation.uuid, response['uuid'])

    def test_get_one_by_uuid_not_found(self):
        temp_uuid = uuidutils.generate_uuid()
        response = self.get_json('/federations/%s' % temp_uuid,
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_get_one_by_name_multiple_federation(self):
        obj_utils.create_test_federation(self.context, name='test_federation',
                                         uuid=uuidutils.generate_uuid())
        obj_utils.create_test_federation(self.context, name='test_federation',
                                         uuid=uuidutils.generate_uuid())
        response = self.get_json('/federations/test_federation',
                                 expect_errors=True)
        self.assertEqual(409, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_get_all_with_pagination_marker(self):
        federation_list = []
        for id_ in range(4):
            federation = obj_utils.create_test_federation(
                self.context, id=id_, uuid=uuidutils.generate_uuid())
            federation_list.append(federation)

        response = self.get_json(
            '/federations?limit=3&marker=%s' % federation_list[2].uuid)
        self.assertEqual(1, len(response['federations']))
        self.assertEqual(federation_list[-1].uuid,
                         response['federations'][0]['uuid'])

    def test_detail(self):
        federation = obj_utils.create_test_federation(
            self.context, uuid=uuidutils.generate_uuid())
        response = self.get_json('/federations/detail')
        self.assertEqual(federation.uuid, response['federations'][0]["uuid"])

    def test_detail_with_pagination_marker(self):
        federation_list = []
        for id_ in range(4):
            federation = obj_utils.create_test_federation(
                self.context, id=id_, uuid=uuidutils.generate_uuid())
            federation_list.append(federation)

        response = self.get_json(
            '/federations/detail?limit=3&marker=%s' % federation_list[2].uuid)
        self.assertEqual(1, len(response['federations']))
        self.assertEqual(federation_list[-1].uuid,
                         response['federations'][0]['uuid'])

    def test_detail_against_single(self):
        federation = obj_utils.create_test_federation(
            self.context, uuid=uuidutils.generate_uuid())
        response = self.get_json(
            '/federations/%s/detail' % federation['uuid'], expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_many(self):
        federation_list = []
        for id_ in range(5):
            temp_uuid = uuidutils.generate_uuid()
            federation = obj_utils.create_test_federation(
                self.context, id=id_, uuid=temp_uuid)
            federation_list.append(federation.uuid)

        response = self.get_json('/federations')
        self.assertEqual(len(federation_list), len(response['federations']))
        uuids = [f['uuid'] for f in response['federations']]
        self.assertEqual(sorted(federation_list), sorted(uuids))

    def test_links(self):
        uuid = uuidutils.generate_uuid()
        obj_utils.create_test_federation(self.context, id=1, uuid=uuid)
        response = self.get_json('/federations/%s' % uuid)
        self.assertIn('links', response.keys())
        self.assertEqual(2, len(response['links']))
        self.assertIn(uuid, response['links'][0]['href'])
        for link in response['links']:
            bookmark = link['rel'] == 'bookmark'
            self.assertTrue(self.validate_link(link['href'],
                                               bookmark=bookmark))

    def test_collection_links(self):
        for id_ in range(5):
            obj_utils.create_test_federation(self.context, id=id_,
                                             uuid=uuidutils.generate_uuid())
        response = self.get_json('/federations/?limit=3')
        next_marker = response['federations'][-1]['uuid']
        self.assertIn(next_marker, response['next'])

    def test_collection_links_default_limit(self):
        cfg.CONF.set_override('max_limit', 3, 'api')
        for id_ in range(5):
            obj_utils.create_test_federation(self.context, id=id_,
                                             uuid=uuidutils.generate_uuid())
        response = self.get_json('/federations')
        self.assertEqual(3, len(response['federations']))

        next_marker = response['federations'][-1]['uuid']
        self.assertIn(next_marker, response['next'])


class TestPatch(api_base.FunctionalTest):
    def setUp(self):
        super(TestPatch, self).setUp()
        p = mock.patch.object(rpcapi.API, 'federation_update_async')
        self.mock_federation_update = p.start()
        self.mock_federation_update.side_effect = \
            self._sim_rpc_federation_update
        self.addCleanup(p.stop)

    def _sim_rpc_federation_update(self, federation, rollback=False):
        federation.save()
        return federation

    def test_member_join(self):
        f = obj_utils.create_test_federation(
            self.context, name='federation-example',
            uuid=uuidutils.generate_uuid(), member_ids=[])
        new_member = obj_utils.create_test_cluster(self.context)

        response = self.patch_json(
            '/federations/%s' % f.uuid,
            [{'path': '/member_ids', 'value': new_member.uuid, 'op': 'add'}])
        self.assertEqual(202, response.status_int)

        # make sure it was added:
        fed = self.get_json('/federations/%s' % f.uuid)
        self.assertTrue(new_member.uuid in fed['member_ids'])

    def test_member_unjoin(self):
        member = obj_utils.create_test_cluster(self.context)
        federation = obj_utils.create_test_federation(
            self.context, name='federation-example',
            uuid=uuidutils.generate_uuid(), member_ids=[member.uuid])

        response = self.patch_json(
            '/federations/%s' % federation.uuid,
            [{'path': '/member_ids', 'value': member.uuid, 'op': 'remove'}])
        self.assertEqual(202, response.status_int)

        # make sure it was deleted:
        fed = self.get_json('/federations/%s' % federation.uuid)
        self.assertFalse(member.uuid in fed['member_ids'])

    def test_join_non_existent_cluster(self):
        foo_uuid = uuidutils.generate_uuid()
        f = obj_utils.create_test_federation(
            self.context, name='federation-example',
            uuid=uuidutils.generate_uuid(), member_ids=[])

        response = self.patch_json(
            '/federations/%s' % f.uuid,
            [{'path': '/member_ids', 'value': foo_uuid, 'op': 'add'}],
            expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_unjoin_non_existent_cluster(self):
        foo_uuid = uuidutils.generate_uuid()
        f = obj_utils.create_test_federation(
            self.context, name='federation-example',
            uuid=uuidutils.generate_uuid(), member_ids=[])

        response = self.patch_json(
            '/federations/%s' % f.uuid,
            [{'path': '/member_ids', 'value': foo_uuid, 'op': 'remove'}],
            expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_join_cluster_already_member(self):
        cluster = obj_utils.create_test_cluster(self.context)
        f = obj_utils.create_test_federation(
            self.context, name='federation-example',
            uuid=uuidutils.generate_uuid(), member_ids=[cluster.uuid])

        response = self.patch_json(
            '/federations/%s' % f.uuid,
            [{'path': '/member_ids', 'value': cluster.uuid, 'op': 'add'}],
            expect_errors=True)
        self.assertEqual(409, response.status_int)

    def test_unjoin_non_member_cluster(self):
        cluster = obj_utils.create_test_cluster(self.context)
        f = obj_utils.create_test_federation(
            self.context, name='federation-example',
            uuid=uuidutils.generate_uuid(), member_ids=[])

        response = self.patch_json(
            '/federations/%s' % f.uuid,
            [{'path': '/member_ids', 'value': cluster.uuid, 'op': 'remove'}],
            expect_errors=True)
        self.assertEqual(404, response.status_int)


class TestPost(api_base.FunctionalTest):
    def setUp(self):
        super(TestPost, self).setUp()
        p = mock.patch.object(rpcapi.API, 'federation_create_async')
        self.mock_fed_create = p.start()
        self.mock_fed_create.side_effect = self._simulate_federation_create
        self.addCleanup(p.stop)
        self.hostcluster = obj_utils.create_test_cluster(self.context)

    def _simulate_federation_create(self, federation, create_timeout):
        federation.create()
        return federation

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_federation(self, mock_utcnow):
        bdict = apiutils.federation_post_data(
            uuid=uuidutils.generate_uuid(),
            hostcluster_id=self.hostcluster.uuid)
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.post_json('/federations', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        self.assertTrue(uuidutils.is_uuid_like(response.json['uuid']))

    def test_create_federation_no_hostcluster_id(self):
        bdict = apiutils.federation_post_data(uuid=uuidutils.generate_uuid())
        del bdict['hostcluster_id']
        response = self.post_json('/federations', bdict, expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_create_federation_hostcluster_does_not_exist(self):
        bdict = apiutils.federation_post_data(
            uuid=uuidutils.generate_uuid(),
            hostcluster_id=uuidutils.generate_uuid())
        response = self.post_json('/federations', bdict, expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_create_federation_no_dns_zone_name(self):
        bdict = apiutils.federation_post_data(
            uuid=uuidutils.generate_uuid(),
            hostcluster_id=self.hostcluster.uuid)
        del bdict['properties']
        response = self.post_json('/federations', bdict, expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_create_federation_generate_uuid(self):
        bdict = apiutils.federation_post_data(
            hostcluster_id=self.hostcluster.uuid)
        del bdict['uuid']
        response = self.post_json('/federations', bdict)
        self.assertEqual(202, response.status_int)

    def test_create_federation_with_invalid_name(self):
        invalid_names = [
            'x' * 243, '123456', '123456test_federation',
            '-test_federation', '.test_federation', '_test_federation', ''
        ]

        for value in invalid_names:
            bdict = apiutils.federation_post_data(
                uuid=uuidutils.generate_uuid(), name=value,
                hostcluster_id=self.hostcluster.uuid)
            response = self.post_json('/federations', bdict,
                                      expect_errors=True)
            self.assertEqual('application/json', response.content_type)
            self.assertEqual(400, response.status_int)
            self.assertTrue(response.json['errors'])

    def test_create_federation_with_valid_name(self):
        valid_names = [
            'test_federation123456', 'test-federation', 'test.federation',
            'testfederation.', 'testfederation-', 'testfederation_',
            'test.-_federation', 'Testfederation'
        ]

        for value in valid_names:
            bdict = apiutils.federation_post_data(
                name=value, hostcluster_id=self.hostcluster.uuid)
            bdict['uuid'] = uuidutils.generate_uuid()
            response = self.post_json('/federations', bdict)
            self.assertEqual(202, response.status_int)

    def test_create_federation_without_name(self):
        bdict = apiutils.federation_post_data(
            uuid=uuidutils.generate_uuid(),
            hostcluster_id=self.hostcluster.uuid)
        del bdict['name']
        response = self.post_json('/federations', bdict)
        self.assertEqual(202, response.status_int)


class TestDelete(api_base.FunctionalTest):
    def setUp(self):
        super(TestDelete, self).setUp()
        self.federation = obj_utils.create_test_federation(
            self.context, name='federation-example',
            uuid=uuidutils.generate_uuid())
        p = mock.patch.object(rpcapi.API, 'federation_delete_async')
        self.mock_federation_delete = p.start()
        self.mock_federation_delete.side_effect = \
            self._simulate_federation_delete
        self.addCleanup(p.stop)

    def _simulate_federation_delete(self, federation_uuid):
        federation = objects.Federation.get_by_uuid(self.context,
                                                    federation_uuid)
        federation.destroy()

    def test_delete_federation(self):
        self.delete('/federations/%s' % self.federation.uuid)
        response = self.get_json('/federations/%s' % self.federation.uuid,
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_delete_federation_not_found(self):
        delete = self.delete('/federations/%s' % uuidutils.generate_uuid(),
                             expect_errors=True)
        self.assertEqual(404, delete.status_int)
        self.assertEqual('application/json', delete.content_type)
        self.assertTrue(delete.json['errors'])

    def test_delete_federation_with_name(self):
        delete = self.delete('/federations/%s' % self.federation.name)
        self.assertEqual(204, delete.status_int)

    def test_delete_federation_with_name_not_found(self):
        delete = self.delete('/federations/%s' % 'foo',
                             expect_errors=True)
        self.assertEqual(404, delete.status_int)
        self.assertEqual('application/json', delete.content_type)
        self.assertTrue(delete.json['errors'])
