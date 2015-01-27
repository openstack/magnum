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

from magnum.common import exception
from magnum.common import utils as magnum_utils
from magnum import objects
from magnum.tests.db import base
from magnum.tests.db import utils


class TestBayObject(base.DbTestCase):

    def setUp(self):
        super(TestBayObject, self).setUp()
        self.fake_bay = utils.get_test_bay()

    def test_get_by_id(self):
        bay_id = self.fake_bay['id']
        with mock.patch.object(self.dbapi, 'get_bay_by_id',
                               autospec=True) as mock_get_bay:
            mock_get_bay.return_value = self.fake_bay
            bay = objects.Bay.get(self.context, bay_id)
            mock_get_bay.assert_called_once_with(bay_id)
            self.assertEqual(self.context, bay._context)

    def test_get_by_uuid(self):
        uuid = self.fake_bay['uuid']
        with mock.patch.object(self.dbapi, 'get_bay_by_uuid',
                               autospec=True) as mock_get_bay:
            mock_get_bay.return_value = self.fake_bay
            bay = objects.Bay.get(self.context, uuid)
            mock_get_bay.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, bay._context)

    def test_get_bad_id_and_uuid(self):
        self.assertRaises(exception.InvalidIdentity,
                          objects.Bay.get, self.context, 'not-a-uuid')

    def test_list(self):
        with mock.patch.object(self.dbapi, 'get_bay_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_bay]
            bays = objects.Bay.list(self.context)
            self.assertEqual(mock_get_list.call_count, 1)
            self.assertThat(bays, HasLength(1))
            self.assertIsInstance(bays[0], objects.Bay)
            self.assertEqual(self.context, bays[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_bay',
                               autospec=True) as mock_create_bay:
            mock_create_bay.return_value = self.fake_bay
            bay = objects.Bay(self.context, **self.fake_bay)
            bay.create()
            mock_create_bay.assert_called_once_with(self.fake_bay)
            self.assertEqual(self.context, bay._context)

    def test_destroy(self):
        uuid = self.fake_bay['uuid']
        with mock.patch.object(self.dbapi, 'get_bay_by_uuid',
                               autospec=True) as mock_get_bay:
            mock_get_bay.return_value = self.fake_bay
            with mock.patch.object(self.dbapi, 'destroy_bay',
                                   autospec=True) as mock_destroy_bay:
                bay = objects.Bay.get_by_uuid(self.context, uuid)
                bay.destroy()
                mock_get_bay.assert_called_once_with(self.context, uuid)
                mock_destroy_bay.assert_called_once_with(uuid)
                self.assertEqual(self.context, bay._context)

    def test_save(self):
        uuid = self.fake_bay['uuid']
        with mock.patch.object(self.dbapi, 'get_bay_by_uuid',
                               autospec=True) as mock_get_bay:
            mock_get_bay.return_value = self.fake_bay
            with mock.patch.object(self.dbapi, 'update_bay',
                                   autospec=True) as mock_update_bay:
                bay = objects.Bay.get_by_uuid(self.context, uuid)
                bay.node_count = 10
                bay.save()

                mock_get_bay.assert_called_once_with(self.context, uuid)
                mock_update_bay.assert_called_once_with(
                        uuid, {'node_count': 10})
                self.assertEqual(self.context, bay._context)

    def test_refresh(self):
        uuid = self.fake_bay['uuid']
        new_uuid = magnum_utils.generate_uuid()
        returns = [dict(self.fake_bay, uuid=uuid),
                   dict(self.fake_bay, uuid=new_uuid)]
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        with mock.patch.object(self.dbapi, 'get_bay_by_uuid',
                               side_effect=returns,
                               autospec=True) as mock_get_bay:
            bay = objects.Bay.get_by_uuid(self.context, uuid)
            self.assertEqual(uuid, bay.uuid)
            bay.refresh()
            self.assertEqual(new_uuid, bay.uuid)
            self.assertEqual(expected, mock_get_bay.call_args_list)
            self.assertEqual(self.context, bay._context)
