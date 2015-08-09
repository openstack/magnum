# Copyright 2015 NEC Foundation
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

"""Tests for manipulating X509KeyPairs via the DB API"""

import six

from magnum.common import context
from magnum.common import exception
from magnum.common import utils as magnum_utils
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils


class DbX509KeyPairTestCase(base.DbTestCase):

    def test_create_x509keypair(self):
        utils.create_test_x509keypair()

    def test_create_x509keypair_nullable_bay_uuid(self):
        utils.create_test_x509keypair(bay_uuid=None)

    def test_create_x509keypair_already_exists(self):
        utils.create_test_x509keypair()
        self.assertRaises(exception.X509KeyPairAlreadyExists,
                          utils.create_test_x509keypair)

    def test_get_x509keypair_by_id(self):
        x509keypair = utils.create_test_x509keypair()
        res = self.dbapi.get_x509keypair_by_id(self.context, x509keypair.id)
        self.assertEqual(x509keypair.id, res.id)
        self.assertEqual(x509keypair.uuid, res.uuid)

    def test_get_x509keypair_by_name(self):
        x509keypair = utils.create_test_x509keypair()
        res = self.dbapi.get_x509keypair_by_name(self.context,
                                                 x509keypair.name)
        self.assertEqual(x509keypair.name, res.name)
        self.assertEqual(x509keypair.uuid, res.uuid)

    def test_get_x509keypair_by_uuid(self):
        x509keypair = utils.create_test_x509keypair()
        res = self.dbapi.get_x509keypair_by_uuid(self.context,
                                                 x509keypair.uuid)
        self.assertEqual(x509keypair.id, res.id)
        self.assertEqual(x509keypair.uuid, res.uuid)

    def test_get_x509keypair_that_does_not_exist(self):
        self.assertRaises(exception.X509KeyPairNotFound,
                          self.dbapi.get_x509keypair_by_id,
                          self.context, 999)
        self.assertRaises(exception.X509KeyPairNotFound,
                          self.dbapi.get_x509keypair_by_uuid,
                          self.context,
                          '12345678-9999-0000-aaaa-123456789012')

    def test_get_x509keypair_list(self):
        uuids = []
        for i in range(1, 6):
            x509keypair = utils.create_test_x509keypair(
                uuid=magnum_utils.generate_uuid())
            uuids.append(six.text_type(x509keypair['uuid']))
        res = self.dbapi.get_x509keypair_list(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    def test_get_x509keypair_list_with_filters(self):
        bay1 = utils.get_test_bay(id=1, uuid=magnum_utils.generate_uuid())
        bay2 = utils.get_test_bay(id=2, uuid=magnum_utils.generate_uuid())
        self.dbapi.create_bay(bay1)
        self.dbapi.create_bay(bay2)

        x509keypair1 = utils.create_test_x509keypair(
            name='x509keypair-one',
            uuid=magnum_utils.generate_uuid(),
            bay_uuid=bay1['uuid'])
        x509keypair2 = utils.create_test_x509keypair(
            name='x509keypair-two',
            uuid=magnum_utils.generate_uuid(),
            bay_uuid=bay2['uuid'])
        x509keypair3 = utils.create_test_x509keypair(
            name='x509keypair-three',
            bay_uuid=bay2['uuid'])

        res = self.dbapi.get_x509keypair_list(
            self.context, filters={'bay_uuid': bay1['uuid']})
        self.assertEqual([x509keypair1.id], [r.id for r in res])

        res = self.dbapi.get_x509keypair_list(
            self.context, filters={'bay_uuid': bay2['uuid']})
        self.assertEqual([x509keypair2.id, x509keypair3.id],
                         [r.id for r in res])

        res = self.dbapi.get_x509keypair_list(
            self.context, filters={'name': 'x509keypair-one'})
        self.assertEqual([x509keypair1.id], [r.id for r in res])

        res = self.dbapi.get_x509keypair_list(
            self.context, filters={'name': 'bad-x509keypair'})
        self.assertEqual([], [r.id for r in res])

    def test_get_x509keypair_list_by_admin_all_tenants(self):
        uuids = []
        for i in range(1, 6):
            x509keypair = utils.create_test_x509keypair(
                uuid=magnum_utils.generate_uuid(),
                project_id=magnum_utils.generate_uuid(),
                user_id=magnum_utils.generate_uuid())
            uuids.append(six.text_type(x509keypair['uuid']))
        ctx = context.make_admin_context()
        res = self.dbapi.get_x509keypair_list(
            ctx, opts={'get_all_tenants': True})
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    def test_get_x509keypair_list_bay_not_exist(self):
        utils.create_test_x509keypair()
        self.assertEqual(1, len(self.dbapi.get_x509keypair_list(self.context)))
        res = self.dbapi.get_x509keypair_list(self.context, filters={
            'bay_uuid': magnum_utils.generate_uuid()})
        self.assertEqual(0, len(res))

    def test_destroy_x509keypair(self):
        x509keypair = utils.create_test_x509keypair()
        self.assertIsNotNone(self.dbapi.get_x509keypair_by_id(
            self.context, x509keypair.id))
        self.dbapi.destroy_x509keypair(x509keypair.id)
        self.assertRaises(exception.X509KeyPairNotFound,
                          self.dbapi.get_x509keypair_by_id,
                          self.context, x509keypair.id)

    def test_destroy_x509keypair_by_uuid(self):
        x509keypair = utils.create_test_x509keypair()
        self.assertIsNotNone(self.dbapi.get_x509keypair_by_uuid(
            self.context, x509keypair.uuid))
        self.dbapi.destroy_x509keypair(x509keypair.uuid)
        self.assertRaises(exception.X509KeyPairNotFound,
                          self.dbapi.get_x509keypair_by_uuid, self.context,
                          x509keypair.uuid)

    def test_destroy_x509keypair_that_does_not_exist(self):
        self.assertRaises(exception.X509KeyPairNotFound,
                          self.dbapi.destroy_x509keypair,
                          '12345678-9999-0000-aaaa-123456789012')
