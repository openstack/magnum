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


class TestBayModelObject(base.DbTestCase):

    def setUp(self):
        super(TestBayModelObject, self).setUp()
        self.fake_baymodel = utils.get_test_baymodel()

    def test_get_by_id(self):
        baymodel_id = self.fake_baymodel['id']
        with mock.patch.object(self.dbapi, 'get_baymodel_by_id',
                               autospec=True) as mock_get_baymodel:
            mock_get_baymodel.return_value = self.fake_baymodel
            baymodel = objects.BayModel.get(self.context, baymodel_id)
            mock_get_baymodel.assert_called_once_with(self.context,
                                                      baymodel_id)
            self.assertEqual(self.context, baymodel._context)

    def test_get_by_uuid(self):
        uuid = self.fake_baymodel['uuid']
        with mock.patch.object(self.dbapi, 'get_baymodel_by_uuid',
                               autospec=True) as mock_get_baymodel:
            mock_get_baymodel.return_value = self.fake_baymodel
            baymodel = objects.BayModel.get(self.context, uuid)
            mock_get_baymodel.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, baymodel._context)

    def test_get_bad_id_and_uuid(self):
        self.assertRaises(exception.InvalidIdentity,
                          objects.BayModel.get, self.context, 'not-a-uuid')

    def test_get_by_name(self):
        name = self.fake_baymodel['name']
        with mock.patch.object(self.dbapi, 'get_baymodel_by_name',
                               autospec=True) as mock_get_baymodel:
            mock_get_baymodel.return_value = self.fake_baymodel
            baymodel = objects.BayModel.get_by_name(self.context, name)
            mock_get_baymodel.assert_called_once_with(self.context, name)
            self.assertEqual(self.context, baymodel._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'get_baymodel_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_baymodel]
            baymodels = objects.BayModel.list(self.context)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(baymodels, HasLength(1))
            self.assertIsInstance(baymodels[0], objects.BayModel)
            self.assertEqual(self.context, baymodels[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_baymodel',
                               autospec=True) as mock_create_baymodel:
            mock_create_baymodel.return_value = self.fake_baymodel
            baymodel = objects.BayModel(self.context, **self.fake_baymodel)
            baymodel.create()
            mock_create_baymodel.assert_called_once_with(self.fake_baymodel)
            self.assertEqual(self.context, baymodel._context)

    def test_destroy(self):
        uuid = self.fake_baymodel['uuid']
        with mock.patch.object(self.dbapi, 'get_baymodel_by_uuid',
                               autospec=True) as mock_get_baymodel:
            mock_get_baymodel.return_value = self.fake_baymodel
            with mock.patch.object(self.dbapi, 'destroy_baymodel',
                                   autospec=True) as mock_destroy_baymodel:
                bm = objects.BayModel.get_by_uuid(self.context, uuid)
                bm.destroy()
                mock_get_baymodel.assert_called_once_with(self.context, uuid)
                mock_destroy_baymodel.assert_called_once_with(uuid)
                self.assertEqual(self.context, bm._context)

    def test_save(self):
        uuid = self.fake_baymodel['uuid']
        with mock.patch.object(self.dbapi, 'get_baymodel_by_uuid',
                               autospec=True) as mock_get_baymodel:
            mock_get_baymodel.return_value = self.fake_baymodel
            with mock.patch.object(self.dbapi, 'update_baymodel',
                                   autospec=True) as mock_update_baymodel:
                bm = objects.BayModel.get_by_uuid(self.context, uuid)
                bm.image_id = 'test-image'
                bm.save()

                mock_get_baymodel.assert_called_once_with(self.context, uuid)
                mock_update_baymodel.assert_called_once_with(
                    uuid, {'image_id': 'test-image'})
                self.assertEqual(self.context, bm._context)

    def test_refresh(self):
        uuid = self.fake_baymodel['uuid']
        new_uuid = uuidutils.generate_uuid()
        returns = [dict(self.fake_baymodel, uuid=uuid),
                   dict(self.fake_baymodel, uuid=new_uuid)]
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        with mock.patch.object(self.dbapi, 'get_baymodel_by_uuid',
                               side_effect=returns,
                               autospec=True) as mock_get_baymodel:
            bm = objects.BayModel.get_by_uuid(self.context, uuid)
            self.assertEqual(uuid, bm.uuid)
            bm.refresh()
            self.assertEqual(new_uuid, bm.uuid)
            self.assertEqual(expected, mock_get_baymodel.call_args_list)
            self.assertEqual(self.context, bm._context)
