# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Tests for manipulating Federations via the DB API"""
from oslo_utils import uuidutils
import six

from magnum.common import context
from magnum.common import exception
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils


class DbFederationTestCase(base.DbTestCase):
    def test_create_federation(self):
        utils.create_test_federation()

    def test_create_federation_already_exists(self):
        utils.create_test_federation()
        self.assertRaises(exception.FederationAlreadyExists,
                          utils.create_test_federation)

    def test_get_federation_by_id(self):
        federation = utils.create_test_federation()
        res = self.dbapi.get_federation_by_id(self.context, federation.id)
        self.assertEqual(federation.id, res.id)
        self.assertEqual(federation.uuid, res.uuid)

    def test_get_federation_by_name(self):
        federation = utils.create_test_federation()
        res = self.dbapi.get_federation_by_name(self.context, federation.name)
        self.assertEqual(federation.name, res.name)
        self.assertEqual(federation.uuid, res.uuid)

    def test_get_federation_by_uuid(self):
        federation = utils.create_test_federation()
        res = self.dbapi.get_federation_by_uuid(self.context, federation.uuid)
        self.assertEqual(federation.id, res.id)
        self.assertEqual(federation.uuid, res.uuid)

    def test_get_federation_that_does_not_exist(self):
        self.assertRaises(exception.FederationNotFound,
                          self.dbapi.get_federation_by_id,
                          self.context, 999)
        self.assertRaises(exception.FederationNotFound,
                          self.dbapi.get_federation_by_uuid,
                          self.context,
                          '12345678-9999-0000-aaaa-123456789012')
        self.assertRaises(exception.FederationNotFound,
                          self.dbapi.get_federation_by_name,
                          self.context, 'not_found')

    def test_get_federation_by_name_multiple_federation(self):
        utils.create_test_federation(id=1, name='federation-1',
                                     uuid=uuidutils.generate_uuid())
        utils.create_test_federation(id=2, name='federation-1',
                                     uuid=uuidutils.generate_uuid())
        self.assertRaises(exception.Conflict,
                          self.dbapi.get_federation_by_name,
                          self.context, 'federation-1')

    def test_get_federation_list(self):
        uuids = []
        for _ in range(5):
            federation = utils.create_test_federation(
                uuid=uuidutils.generate_uuid())
            uuids.append(six.text_type(federation.uuid))

        res = self.dbapi.get_federation_list(self.context, sort_key='uuid')
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), res_uuids)

    def test_get_federation_list_sorted(self):
        uuids = []
        for _ in range(5):
            federation = utils.create_test_federation(
                uuid=uuidutils.generate_uuid())
            uuids.append(six.text_type(federation.uuid))

        res = self.dbapi.get_federation_list(self.context, sort_key='uuid')
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), res_uuids)

        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.get_federation_list,
                          self.context,
                          sort_key='foo')

    def test_get_federation_list_with_filters(self):
        fed1 = utils.create_test_federation(
            id=1,
            uuid=uuidutils.generate_uuid(),
            name='fed1',
            project_id='proj1',
            hostcluster_id='master1',
            member_ids=['member1', 'member2'],
            properties={'dns-zone': 'fed1.com.'})

        fed2 = utils.create_test_federation(
            id=2,
            uuid=uuidutils.generate_uuid(),
            name='fed',
            project_id='proj2',
            hostcluster_id='master2',
            member_ids=['member3', 'member4'],
            properties={"dns-zone": "fed2.com."})

        # NOTE(clenimar): we are specifying a project_id to the test
        # resources above, which means that our current context
        # (self.context) will not be able to see these resources.
        # Create an admin context in order to test the queries:
        ctx = context.make_admin_context(all_tenants=True)

        # Filter by name:
        res = self.dbapi.get_federation_list(ctx, filters={'name': 'fed1'})
        self.assertEqual([fed1.id], [r.id for r in res])

        res = self.dbapi.get_federation_list(ctx, filters={'name': 'foo'})
        self.assertEqual([], [r.id for r in res])

        # Filter by project_id
        res = self.dbapi.get_federation_list(ctx,
                                             filters={'project_id': 'proj1'})
        self.assertEqual([fed1.id], [r.id for r in res])

        res = self.dbapi.get_federation_list(ctx,
                                             filters={'project_id': 'foo'})
        self.assertEqual([], [r.id for r in res])

        # Filter by hostcluster_id
        res = self.dbapi.get_federation_list(ctx, filters={
            'hostcluster_id': 'master1'})
        self.assertEqual([fed1.id], [r.id for r in res])

        res = self.dbapi.get_federation_list(ctx, filters={
            'hostcluster_id': 'master2'})
        self.assertEqual([fed2.id], [r.id for r in res])

        res = self.dbapi.get_federation_list(ctx,
                                             filters={'hostcluster_id': 'foo'})
        self.assertEqual([], [r.id for r in res])

        # Filter by member_ids (please note that it is currently implemented
        # as an exact match. So it will only return federations whose member
        # clusters are exactly those passed as a filter)
        res = self.dbapi.get_federation_list(
            ctx, filters={'member_ids': ['member1', 'member2']})
        self.assertEqual([fed1.id], [r.id for r in res])

        res = self.dbapi.get_federation_list(
            ctx, filters={'member_ids': ['foo']})
        self.assertEqual([], [r.id for r in res])

        # Filter by properties
        res = self.dbapi.get_federation_list(
            ctx, filters={
                'properties': {'dns-zone': 'fed2.com.'}
            })
        self.assertEqual([fed2.id], [r.id for r in res])

        res = self.dbapi.get_federation_list(
            ctx, filters={
                'properties': {'dns-zone': 'foo.bar.'}
            })
        self.assertEqual([], [r.id for r in res])

    def test_get_federation_list_by_admin_all_tenants(self):
        uuids = []
        for _ in range(5):
            federation = utils.create_test_federation(
                uuid=uuidutils.generate_uuid(),
                project_id=uuidutils.generate_uuid())
            uuids.append(six.text_type(federation['uuid']))

        ctx = context.make_admin_context(all_tenants=True)
        res = self.dbapi.get_federation_list(ctx)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(len(res), 5)
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    def test_destroy_federation(self):
        federation = utils.create_test_federation()
        self.assertIsNotNone(
            self.dbapi.get_federation_by_id(self.context, federation.id))
        self.dbapi.destroy_federation(federation.id)
        self.assertRaises(exception.FederationNotFound,
                          self.dbapi.get_federation_by_id,
                          self.context, federation.id)

    def test_destroy_federation_by_uuid(self):
        federation = utils.create_test_federation(
            uuid=uuidutils.generate_uuid())
        self.assertIsNotNone(
            self.dbapi.get_federation_by_uuid(self.context, federation.uuid))
        self.dbapi.destroy_federation(federation.uuid)
        self.assertRaises(exception.FederationNotFound,
                          self.dbapi.get_federation_by_uuid,
                          self.context, federation.uuid)

    def test_destroy_federation_by_id_that_does_not_exist(self):
        self.assertRaises(exception.FederationNotFound,
                          self.dbapi.destroy_federation,
                          '12345678-9999-0000-aaaa-123456789012')

    def test_destroy_federation_by_uudid_that_does_not_exist(self):
        self.assertRaises(exception.FederationNotFound,
                          self.dbapi.destroy_federation, '15')

    def test_update_federation_members(self):
        federation = utils.create_test_federation()
        old_members = federation.member_ids
        new_members = old_members + ['new-member-id']
        self.assertNotEqual(old_members, new_members)
        res = self.dbapi.update_federation(federation.id,
                                           {'member_ids': new_members})
        self.assertEqual(new_members, res.member_ids)

    def test_update_federation_properties(self):
        federation = utils.create_test_federation()
        old_properties = federation.properties
        new_properties = {
            'dns-zone': 'new.domain.com.'
        }
        self.assertNotEqual(old_properties, new_properties)
        res = self.dbapi.update_federation(federation.id,
                                           {'properties': new_properties})
        self.assertEqual(new_properties, res.properties)

    def test_update_federation_not_found(self):
        federation_uuid = uuidutils.generate_uuid()
        self.assertRaises(exception.FederationNotFound,
                          self.dbapi.update_federation, federation_uuid,
                          {'member_ids': ['foo']})
