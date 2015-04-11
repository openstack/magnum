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

"""Tests for manipulating BayLocks via the DB API"""

import uuid

from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils as utils


class DbBayLockTestCase(base.DbTestCase):

    def setUp(self):
        super(DbBayLockTestCase, self).setUp()
        self.bay = utils.create_test_bay()

    def test_create_bay_lock_success(self):
        ret = self.dbapi.create_bay_lock(self.bay.uuid, str(uuid.uuid4()))
        self.assertIsNone(ret)

    def test_create_bay_lock_fail_double_same(self):
        conductor_id = str(uuid.uuid4())
        self.dbapi.create_bay_lock(self.bay.uuid, conductor_id)
        ret = self.dbapi.create_bay_lock(self.bay.uuid, conductor_id)
        self.assertEqual(conductor_id, ret)

    def test_create_bay_lock_fail_double_different(self):
        conductor_id = str(uuid.uuid4())
        self.dbapi.create_bay_lock(self.bay.uuid, conductor_id)
        ret = self.dbapi.create_bay_lock(self.bay.uuid, str(uuid.uuid4()))
        self.assertEqual(conductor_id, ret)

    def test_steal_bay_lock_success(self):
        conductor_id = str(uuid.uuid4())
        self.dbapi.create_bay_lock(self.bay.uuid, conductor_id)
        ret = self.dbapi.steal_bay_lock(self.bay.uuid, conductor_id,
                                        str(uuid.uuid4()))
        self.assertIsNone(ret)

    def test_steal_bay_lock_fail_gone(self):
        conductor_id = str(uuid.uuid4())
        self.dbapi.create_bay_lock(self.bay.uuid, conductor_id)
        self.dbapi.release_bay_lock(self.bay.uuid, conductor_id)
        ret = self.dbapi.steal_bay_lock(self.bay.uuid, conductor_id,
                                        str(uuid.uuid4()))
        self.assertTrue(ret)

    def test_steal_bay_lock_fail_stolen(self):
        conductor_id = str(uuid.uuid4())
        self.dbapi.create_bay_lock(self.bay.uuid, conductor_id)

        # Simulate stolen lock
        conductor_id2 = str(uuid.uuid4())
        self.dbapi.release_bay_lock(self.bay.uuid, conductor_id)
        self.dbapi.create_bay_lock(self.bay.uuid, conductor_id2)

        ret = self.dbapi.steal_bay_lock(self.bay.uuid, str(uuid.uuid4()),
                                        conductor_id2)
        self.assertEqual(conductor_id2, ret)

    def test_release_bay_lock_success(self):
        conductor_id = str(uuid.uuid4())
        self.dbapi.create_bay_lock(self.bay.uuid, conductor_id)
        ret = self.dbapi.release_bay_lock(self.bay.uuid, conductor_id)
        self.assertIsNone(ret)

    def test_release_bay_lock_fail_double(self):
        conductor_id = str(uuid.uuid4())
        self.dbapi.create_bay_lock(self.bay.uuid, conductor_id)
        self.dbapi.release_bay_lock(self.bay.uuid, conductor_id)
        ret = self.dbapi.release_bay_lock(self.bay.uuid, conductor_id)
        self.assertTrue(ret)

    def test_release_bay_lock_fail_wrong_conductor_id(self):
        conductor_id = str(uuid.uuid4())
        self.dbapi.create_bay_lock(self.bay.uuid, conductor_id)
        ret = self.dbapi.release_bay_lock(self.bay.uuid, str(uuid.uuid4()))
        self.assertTrue(ret)
