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

import mock
import uuid

from magnum import objects
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils


class TestBayLockObject(base.DbTestCase):

    def setUp(self):
        super(TestBayLockObject, self).setUp()
        baylock_dict = utils.get_test_baylock()
        self.bay_uuid = baylock_dict['bay_uuid']
        self.conductor_id = baylock_dict['conductor_id']

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_bay_lock',
                               autospec=True) as mock_create_baylock:
            objects.BayLock.create(self.bay_uuid, self.conductor_id)
            mock_create_baylock.assert_called_once_with(self.bay_uuid,
                                                        self.conductor_id)

    def test_steal(self):
        with mock.patch.object(self.dbapi, 'steal_bay_lock',
                               autospec=True) as mock_steal_baylock:
            old_conductor_id = self.conductor_id
            new_conductor_id = str(uuid.uuid4())
            objects.BayLock.steal(self.bay_uuid, old_conductor_id,
                                  new_conductor_id)
            mock_steal_baylock.assert_called_once_with(self.bay_uuid,
                old_conductor_id, new_conductor_id)

    def test_release(self):
        with mock.patch.object(self.dbapi, 'release_bay_lock',
                               autospec=True) as mock_release_baylock:
            objects.BayLock.release(self.bay_uuid, self.conductor_id)
            mock_release_baylock.assert_called_once_with(self.bay_uuid,
                                                         self.conductor_id)
