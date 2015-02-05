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

import six

from magnum.common import exception
from magnum.common import utils as magnum_utils
from magnum.tests.db import base
from magnum.tests.db import utils as utils


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
        rc = self.dbapi.get_rc_by_id(self.rc.id)
        self.assertEqual(self.rc.id, rc.id)
        self.assertEqual(self.rc.uuid, rc.uuid)

    def test_get_rc_by_uuid(self):
        rc = self.dbapi.get_rc_by_uuid(self.context, self.rc.uuid)
        self.assertEqual(self.rc.id, rc.id)
        self.assertEqual(self.rc.uuid, rc.uuid)

    def test_get_rc_that_does_not_exist(self):
        self.assertRaises(exception.ReplicationControllerNotFound,
                          self.dbapi.get_rc_by_id, 999)
        self.assertRaises(exception.ReplicationControllerNotFound,
                          self.dbapi.get_rc_by_uuid,
                          self.context,
                          magnum_utils.generate_uuid())

    def test_get_rc_list_defaults(self):
        rc_id_list = [self.rc.id]
        for i in range(1, 6):
            rc = utils.create_test_rc(bay_uuid=self.bay.uuid,
                uuid=magnum_utils.generate_uuid())
            rc_id_list.append(rc.id)
        rc = [i[0] for i in self.dbapi.get_rcinfo_list()]
        self.assertEqual(sorted(rc), sorted(rc_id_list))

    def test_get_rcinfo_list_with_cols(self):
        uuids = {self.rc.id: self.rc.uuid}
        rc_replicas = {self.rc.id: self.rc.replicas}
        for i in range(1, 6):
            uuid = magnum_utils.generate_uuid()
            replicas = i
            rc = utils.create_test_rc(replicas=replicas, uuid=uuid,
                                      bay_uuid=self.bay.uuid)
            uuids[rc.id] = uuid
            rc_replicas[rc.id] = replicas
        rc = self.dbapi.get_rcinfo_list(columns=['id', 'uuid', 'replicas'])
        self.assertEqual(uuids, dict((r[0], r[1]) for r in rc))
        self.assertEqual(rc_replicas, dict((r[0], r[2]) for r in rc))

    def test_get_rcinfo_list_with_filters(self):
        bay1 = utils.get_test_bay(id=11, uuid=magnum_utils.generate_uuid())
        bay2 = utils.get_test_bay(id=12, uuid=magnum_utils.generate_uuid())

        self.dbapi.create_bay(bay1)
        self.dbapi.create_bay(bay2)

        rc1 = utils.create_test_rc(name='rc-one',
            uuid=magnum_utils.generate_uuid(),
            bay_uuid=bay1['uuid'],
            replicas=2)
        rc2 = utils.create_test_rc(name='rc-two',
            uuid=magnum_utils.generate_uuid(),
            bay_uuid=bay2['uuid'],
            replicas=3)

        rc = self.dbapi.get_rcinfo_list(
            filters={'bay_uuid': bay1['uuid']})
        self.assertEqual([rc1.id], [r.id for r in rc])

        rc = self.dbapi.get_rcinfo_list(
            filters={'bay_uuid': bay2['uuid']})
        self.assertEqual([rc2.id], [r.id for r in rc])

        rc = self.dbapi.get_rcinfo_list(filters={'name': 'rc-one'})
        self.assertEqual([rc1.id], [r[0] for r in rc])

        rc = self.dbapi.get_rcinfo_list(filters={'name': 'bad-rc'})
        self.assertEqual([], [r[0] for r in rc])

        rc = self.dbapi.get_rcinfo_list(filters={'replicas': 2})
        self.assertEqual([rc1.id], [r[0] for r in rc])

    def test_get_rc_list(self):
        uuids = [self.rc.uuid]
        for i in range(1, 6):
            rc = utils.create_test_rc(bay_uuid=self.bay.uuid,
                uuid=magnum_utils.generate_uuid())
            uuids.append(six.text_type(rc.uuid))
        rc = self.dbapi.get_rc_list()
        rc_uuids = [r.uuid for r in rc]
        self.assertEqual(sorted(uuids), sorted(rc_uuids))

    def test_get_rc_list_bay_not_exist(self):
        rc = self.dbapi.get_rc_list({'bay_uuid': self.bay.uuid})
        self.assertEqual(1, len(rc))
        rc = self.dbapi.get_rc_list({
            'bay_uuid': magnum_utils.generate_uuid()})
        self.assertEqual(0, len(rc))

    def test_get_rcs_by_bay_uuid(self):
        rc = self.dbapi.get_rcs_by_bay_uuid(self.bay.uuid)
        self.assertEqual(self.rc.id, rc[0].id)

    def test_get_rcs_by_bay_uuid_that_does_not_exist(self):
        res = self.dbapi.get_rcs_by_bay_uuid(magnum_utils.generate_uuid())
        self.assertEqual([], res)

    def test_destroy_rc(self):
        self.dbapi.destroy_rc(self.rc.id)
        self.assertRaises(exception.ReplicationControllerNotFound,
                          self.dbapi.get_rc_by_id, self.rc.id)

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
                          magnum_utils.generate_uuid())

    def test_update_rc(self):
        old_name = self.rc.name
        new_name = 'new-rc'
        self.assertNotEqual(old_name, new_name)
        res = self.dbapi.update_rc(self.rc.id, {'name': new_name})
        self.assertEqual(new_name, res.name)

    def test_update_rc_not_found(self):
        rc_uuid = magnum_utils.generate_uuid()
        self.assertRaises(exception.ReplicationControllerNotFound,
                          self.dbapi.update_rc,
                          rc_uuid, {'replica': 4})

    def test_update_rc_uuid(self):
        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.update_rc, self.rc.id,
                          {'uuid': ''})
