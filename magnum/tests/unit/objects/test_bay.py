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
from oslo_utils import uuidutils
from testtools.matchers import HasLength

from magnum.common import exception
from magnum import objects
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils


class TestBayObject(base.DbTestCase):

    def setUp(self):
        super(TestBayObject, self).setUp()
        self.fake_bay = utils.get_test_bay()
        self.fake_bay['trust_id'] = 'trust_id'
        self.fake_bay['trustee_username'] = 'trustee_user'
        self.fake_bay['trustee_user_id'] = 'trustee_user_id'
        self.fake_bay['trustee_password'] = 'password'
        baymodel_id = self.fake_bay['baymodel_id']
        self.fake_baymodel = objects.BayModel(uuid=baymodel_id)

    @mock.patch('magnum.objects.BayModel.get_by_uuid')
    def test_get_by_id(self, mock_baymodel_get):
        bay_id = self.fake_bay['id']
        with mock.patch.object(self.dbapi, 'get_bay_by_id',
                               autospec=True) as mock_get_bay:
            mock_baymodel_get.return_value = self.fake_baymodel
            mock_get_bay.return_value = self.fake_bay
            bay = objects.Bay.get(self.context, bay_id)
            mock_get_bay.assert_called_once_with(self.context, bay_id)
            self.assertEqual(self.context, bay._context)
            self.assertEqual(bay.baymodel_id, bay.baymodel.uuid)

    @mock.patch('magnum.objects.BayModel.get_by_uuid')
    def test_get_by_uuid(self, mock_baymodel_get):
        uuid = self.fake_bay['uuid']
        with mock.patch.object(self.dbapi, 'get_bay_by_uuid',
                               autospec=True) as mock_get_bay:
            mock_baymodel_get.return_value = self.fake_baymodel
            mock_get_bay.return_value = self.fake_bay
            bay = objects.Bay.get(self.context, uuid)
            mock_get_bay.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, bay._context)
            self.assertEqual(bay.baymodel_id, bay.baymodel.uuid)

    @mock.patch('magnum.objects.BayModel.get_by_uuid')
    def test_get_by_name(self, mock_baymodel_get):
        name = self.fake_bay['name']
        with mock.patch.object(self.dbapi, 'get_bay_by_name',
                               autospec=True) as mock_get_bay:
            mock_baymodel_get.return_value = self.fake_baymodel
            mock_get_bay.return_value = self.fake_bay
            bay = objects.Bay.get_by_name(self.context, name)
            mock_get_bay.assert_called_once_with(self.context, name)
            self.assertEqual(self.context, bay._context)
            self.assertEqual(bay.baymodel_id, bay.baymodel.uuid)

    def test_get_bad_id_and_uuid(self):
        self.assertRaises(exception.InvalidIdentity,
                          objects.Bay.get, self.context, 'not-a-uuid')

    @mock.patch('magnum.objects.BayModel.get_by_uuid')
    def test_list(self, mock_baymodel_get):
        with mock.patch.object(self.dbapi, 'get_bay_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_bay]
            mock_baymodel_get.return_value = self.fake_baymodel
            bays = objects.Bay.list(self.context)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(bays, HasLength(1))
            self.assertIsInstance(bays[0], objects.Bay)
            self.assertEqual(self.context, bays[0]._context)
            self.assertEqual(bays[0].baymodel_id, bays[0].baymodel.uuid)

    @mock.patch('magnum.objects.BayModel.get_by_uuid')
    def test_list_all(self, mock_baymodel_get):
        with mock.patch.object(self.dbapi, 'get_bay_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_bay]
            mock_baymodel_get.return_value = self.fake_baymodel
            self.context.all_tenants = True
            bays = objects.Bay.list(self.context)
            mock_get_list.assert_called_once_with(
                self.context, limit=None, marker=None, filters=None,
                sort_dir=None, sort_key=None)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(bays, HasLength(1))
            self.assertIsInstance(bays[0], objects.Bay)
            self.assertEqual(self.context, bays[0]._context)

    @mock.patch('magnum.objects.BayModel.get_by_uuid')
    def test_list_with_filters(self, mock_baymodel_get):
        with mock.patch.object(self.dbapi, 'get_bay_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_bay]
            mock_baymodel_get.return_value = self.fake_baymodel
            filters = {'name': 'bay1'}
            bays = objects.Bay.list(self.context, filters=filters)

            mock_get_list.assert_called_once_with(self.context, sort_key=None,
                                                  sort_dir=None,
                                                  filters=filters, limit=None,
                                                  marker=None)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(bays, HasLength(1))
            self.assertIsInstance(bays[0], objects.Bay)
            self.assertEqual(self.context, bays[0]._context)

    @mock.patch('magnum.objects.BayModel.get_by_uuid')
    def test_create(self, mock_baymodel_get):
        with mock.patch.object(self.dbapi, 'create_bay',
                               autospec=True) as mock_create_bay:
            mock_baymodel_get.return_value = self.fake_baymodel
            mock_create_bay.return_value = self.fake_bay
            bay = objects.Bay(self.context, **self.fake_bay)
            bay.create()
            mock_create_bay.assert_called_once_with(self.fake_bay)
            self.assertEqual(self.context, bay._context)

    @mock.patch('magnum.objects.BayModel.get_by_uuid')
    def test_destroy(self, mock_baymodel_get):
        uuid = self.fake_bay['uuid']
        with mock.patch.object(self.dbapi, 'get_bay_by_uuid',
                               autospec=True) as mock_get_bay:
            mock_get_bay.return_value = self.fake_bay
            mock_baymodel_get.return_value = self.fake_baymodel
            with mock.patch.object(self.dbapi, 'destroy_bay',
                                   autospec=True) as mock_destroy_bay:
                bay = objects.Bay.get_by_uuid(self.context, uuid)
                bay.destroy()
                mock_get_bay.assert_called_once_with(self.context, uuid)
                mock_destroy_bay.assert_called_once_with(uuid)
                self.assertEqual(self.context, bay._context)

    @mock.patch('magnum.objects.BayModel.get_by_uuid')
    def test_save(self, mock_baymodel_get):
        uuid = self.fake_bay['uuid']
        with mock.patch.object(self.dbapi, 'get_bay_by_uuid',
                               autospec=True) as mock_get_bay:
            mock_baymodel_get.return_value = self.fake_baymodel
            mock_get_bay.return_value = self.fake_bay
            with mock.patch.object(self.dbapi, 'update_bay',
                                   autospec=True) as mock_update_bay:
                bay = objects.Bay.get_by_uuid(self.context, uuid)
                bay.node_count = 10
                bay.master_count = 5
                bay.save()

                mock_get_bay.assert_called_once_with(self.context, uuid)
                mock_update_bay.assert_called_once_with(
                    uuid, {'node_count': 10, 'master_count': 5,
                           'baymodel': self.fake_baymodel})
                self.assertEqual(self.context, bay._context)

    @mock.patch('magnum.objects.BayModel.get_by_uuid')
    def test_refresh(self, mock_baymodel_get):
        uuid = self.fake_bay['uuid']
        new_uuid = uuidutils.generate_uuid()
        returns = [dict(self.fake_bay, uuid=uuid),
                   dict(self.fake_bay, uuid=new_uuid)]
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        with mock.patch.object(self.dbapi, 'get_bay_by_uuid',
                               side_effect=returns,
                               autospec=True) as mock_get_bay:
            mock_baymodel_get.return_value = self.fake_baymodel
            bay = objects.Bay.get_by_uuid(self.context, uuid)
            self.assertEqual(uuid, bay.uuid)
            bay.refresh()
            self.assertEqual(new_uuid, bay.uuid)
            self.assertEqual(expected, mock_get_bay.call_args_list)
            self.assertEqual(self.context, bay._context)
