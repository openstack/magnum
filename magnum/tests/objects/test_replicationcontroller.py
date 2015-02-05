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

import mock
from testtools.matchers import HasLength

from magnum.common import utils as magnum_utils
from magnum import objects
from magnum.tests.db import base
from magnum.tests.db import utils


class TestReplicationControllerObject(base.DbTestCase):

    def setUp(self):
        super(TestReplicationControllerObject, self).setUp()
        self.fake_rc = utils.get_test_rc()

    def test_get_by_id(self):
        rc_id = self.fake_rc['id']
        with mock.patch.object(self.dbapi, 'get_rc_by_id',
                               autospec=True) as mock_get_rc:
            mock_get_rc.return_value = self.fake_rc
            rc = objects.ReplicationController.get_by_id(self.context,
                                                         rc_id)
            mock_get_rc.assert_called_once_with(self.context, rc_id)
            self.assertEqual(self.context, rc._context)

    def test_get_by_uuid(self):
        uuid = self.fake_rc['uuid']
        with mock.patch.object(self.dbapi, 'get_rc_by_uuid',
                               autospec=True) as mock_get_rc:
            mock_get_rc.return_value = self.fake_rc
            rc = objects.ReplicationController.get_by_uuid(self.context,
                                                           uuid)
            mock_get_rc.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, rc._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'get_rc_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_rc]
            rcs = objects.ReplicationController.list(self.context)
            self.assertEqual(mock_get_list.call_count, 1)
            self.assertThat(rcs, HasLength(1))
            self.assertIsInstance(rcs[0], objects.ReplicationController)
            self.assertEqual(self.context, rcs[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_rc',
                               autospec=True) as mock_create_rc:
            mock_create_rc.return_value = self.fake_rc
            rc = objects.ReplicationController(self.context, **self.fake_rc)
            rc.create()
            mock_create_rc.assert_called_once_with(self.fake_rc)
            self.assertEqual(self.context, rc._context)

    def test_destroy(self):
        uuid = self.fake_rc['uuid']
        with mock.patch.object(self.dbapi, 'get_rc_by_uuid',
                               autospec=True) as mock_get_rc:
            mock_get_rc.return_value = self.fake_rc
            with mock.patch.object(self.dbapi, 'destroy_rc',
                                   autospec=True) as mock_destroy_rc:
                rc = objects.ReplicationController.get_by_uuid(self.context,
                                                               uuid)
                rc.destroy()
                mock_get_rc.assert_called_once_with(self.context, uuid)
                mock_destroy_rc.assert_called_once_with(uuid)
                self.assertEqual(self.context, rc._context)

    def test_save(self):
        uuid = self.fake_rc['uuid']
        with mock.patch.object(self.dbapi, 'get_rc_by_uuid',
                               autospec=True) as mock_get_rc:
            mock_get_rc.return_value = self.fake_rc
            with mock.patch.object(self.dbapi, 'update_rc',
                                   autospec=True) as mock_update_rc:
                rc = objects.ReplicationController.get_by_uuid(self.context,
                                                               uuid)
                rc.replicas = 10
                rc.save()

                mock_get_rc.assert_called_once_with(self.context, uuid)
                mock_update_rc.assert_called_once_with(
                        uuid, {'replicas': 10})
                self.assertEqual(self.context, rc._context)

    def test_refresh(self):
        uuid = self.fake_rc['uuid']
        new_uuid = magnum_utils.generate_uuid()
        returns = [dict(self.fake_rc, uuid=uuid),
                   dict(self.fake_rc, uuid=new_uuid)]
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        with mock.patch.object(self.dbapi, 'get_rc_by_uuid',
                               side_effect=returns,
                               autospec=True) as mock_get_rc:
            rc = objects.ReplicationController.get_by_uuid(self.context, uuid)
            self.assertEqual(uuid, rc.uuid)
            rc.refresh()
            self.assertEqual(new_uuid, rc.uuid)
            self.assertEqual(expected, mock_get_rc.call_args_list)
            self.assertEqual(self.context, rc._context)
