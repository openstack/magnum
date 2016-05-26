# Copyright 2015 OpenStack Foundation
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

"""Tests for manipulating Services via the DB API"""

from oslo_utils import uuidutils
import six

from magnum.common import exception
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils as utils


class DbRCTestCase(base.DbTestCase):

    def setUp(self):
        # This method creates a replication controller for every test and
        # replaces a test for creating a replication controller.
        super(DbRCTestCase, self).setUp()
        self.bay = utils.create_test_bay()
        self.rc = utils.create_test_rc(bay_uuid=self.bay.uuid)

    def test_create_rc_duplicated_uuid(self):
        self.assertRaises(exception.ReplicationControllerAlreadyExists,
                          utils.create_test_rc,
                          uuid=self.rc.uuid,
                          bay_uuid=self.bay.uuid)

    def test_get_rc_by_id(self):
        rc = self.dbapi.get_rc_by_id(self.context, self.rc.id)
        self.assertEqual(self.rc.id, rc.id)
        self.assertEqual(self.rc.uuid, rc.uuid)

    def test_get_rc_by_uuid(self):
        rc = self.dbapi.get_rc_by_uuid(self.context, self.rc.uuid)
        self.assertEqual(self.rc.id, rc.id)
        self.assertEqual(self.rc.uuid, rc.uuid)

    def test_get_rc_by_name(self):
        res = self.dbapi.get_rc_by_name(self.context, self.rc.name)
        self.assertEqual(self.rc.name, res.name)
        self.assertEqual(self.rc.uuid, res.uuid)

    def test_get_rc_by_name_multiple_rcs(self):
        utils.create_test_rc(bay_uuid=self.bay.uuid,
                             uuid=uuidutils.generate_uuid())
        self.assertRaises(exception.Conflict, self.dbapi.get_rc_by_name,
                          self.context, self.rc.name)

    def test_get_rc_by_name_not_found(self):
        self.assertRaises(exception.ReplicationControllerNotFound,
                          self.dbapi.get_rc_by_name, self.context,
                          'not_found')

    def test_get_rc_that_does_not_exist(self):
        self.assertRaises(exception.ReplicationControllerNotFound,
                          self.dbapi.get_rc_by_id, self.context, 999)
        self.assertRaises(exception.ReplicationControllerNotFound,
                          self.dbapi.get_rc_by_uuid,
                          self.context,
                          uuidutils.generate_uuid())

    def test_get_rc_list(self):
        uuids = [self.rc.uuid]
        for i in range(1, 6):
            rc = utils.create_test_rc(
                bay_uuid=self.bay.uuid,
                uuid=uuidutils.generate_uuid())
            uuids.append(six.text_type(rc.uuid))
        rc = self.dbapi.get_rc_list(self.context)
        rc_uuids = [r.uuid for r in rc]
        self.assertEqual(sorted(uuids), sorted(rc_uuids))

    def test_get_rc_list_sorted(self):
        uuids = [self.rc.uuid]
        for _ in range(5):
            rc = utils.create_test_rc(uuid=uuidutils.generate_uuid())
            uuids.append(six.text_type(rc.uuid))
        res = self.dbapi.get_rc_list(self.context, sort_key='uuid')
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), res_uuids)

        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.get_rc_list,
                          self.context,
                          sort_key='foo')

    def test_get_rc_list_bay_not_exist(self):
        rc = self.dbapi.get_rc_list(self.context, filters={
                                    'bay_uuid': self.bay.uuid})
        self.assertEqual(1, len(rc))
        rc = self.dbapi.get_rc_list(self.context, filters={
            'bay_uuid': uuidutils.generate_uuid()})
        self.assertEqual(0, len(rc))

    def test_destroy_rc(self):
        self.dbapi.destroy_rc(self.rc.id)
        self.assertRaises(exception.ReplicationControllerNotFound,
                          self.dbapi.get_rc_by_id, self.context, self.rc.id)

    def test_destroy_rc_by_uuid(self):
        self.assertIsNotNone(self.dbapi.get_rc_by_uuid(self.context,
                                                       self.rc.uuid))
        self.dbapi.destroy_rc(self.rc.uuid)
        self.assertRaises(exception.ReplicationControllerNotFound,
                          self.dbapi.get_rc_by_uuid,
                          self.context, self.rc.uuid)

    def test_destroy_rc_that_does_not_exist(self):
        self.assertRaises(exception.ReplicationControllerNotFound,
                          self.dbapi.destroy_rc,
                          uuidutils.generate_uuid())

    def test_update_rc(self):
        old_name = self.rc.name
        new_name = 'new-rc'
        self.assertNotEqual(old_name, new_name)
        res = self.dbapi.update_rc(self.rc.id, {'name': new_name})
        self.assertEqual(new_name, res.name)

    def test_update_rc_not_found(self):
        rc_uuid = uuidutils.generate_uuid()
        self.assertRaises(exception.ReplicationControllerNotFound,
                          self.dbapi.update_rc,
                          rc_uuid, {'replica': 4})

    def test_update_rc_uuid(self):
        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.update_rc, self.rc.id,
                          {'uuid': ''})
