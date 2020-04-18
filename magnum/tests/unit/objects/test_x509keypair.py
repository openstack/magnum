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

from unittest import mock

from oslo_utils import uuidutils
from testtools.matchers import HasLength

from magnum.common import exception
from magnum import objects
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils


class TestX509KeyPairObject(base.DbTestCase):

    def setUp(self):
        super(TestX509KeyPairObject, self).setUp()
        self.fake_x509keypair = utils.get_test_x509keypair()

    def test_get_by_id(self):
        x509keypair_id = self.fake_x509keypair['id']
        with mock.patch.object(self.dbapi, 'get_x509keypair_by_id',
                               autospec=True) as mock_get_x509keypair:
            mock_get_x509keypair.return_value = self.fake_x509keypair
            x509keypair = objects.X509KeyPair.get(self.context, x509keypair_id)
            mock_get_x509keypair.assert_called_once_with(self.context,
                                                         x509keypair_id)
            self.assertEqual(self.context, x509keypair._context)

    def test_get_by_uuid(self):
        uuid = self.fake_x509keypair['uuid']
        with mock.patch.object(self.dbapi, 'get_x509keypair_by_uuid',
                               autospec=True) as mock_get_x509keypair:
            mock_get_x509keypair.return_value = self.fake_x509keypair
            x509keypair = objects.X509KeyPair.get(self.context, uuid)
            mock_get_x509keypair.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, x509keypair._context)

    def test_get_bad_id_and_uuid(self):
        self.assertRaises(exception.InvalidIdentity,
                          objects.X509KeyPair.get, self.context, 'not-a-uuid')

    def test_list(self):
        with mock.patch.object(self.dbapi, 'get_x509keypair_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_x509keypair]
            x509keypairs = objects.X509KeyPair.list(self.context)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(x509keypairs, HasLength(1))
            self.assertIsInstance(x509keypairs[0], objects.X509KeyPair)
            self.assertEqual(self.context, x509keypairs[0]._context)

    def test_list_all(self):
        with mock.patch.object(self.dbapi, 'get_x509keypair_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_x509keypair]
            self.context.all_tenants = True
            x509keypairs = objects.X509KeyPair.list(self.context)
            mock_get_list.assert_called_once_with(
                self.context, limit=None, marker=None, filters=None,
                sort_dir=None, sort_key=None)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(x509keypairs, HasLength(1))
            self.assertIsInstance(x509keypairs[0], objects.X509KeyPair)
            self.assertEqual(self.context, x509keypairs[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_x509keypair',
                               autospec=True) as mock_create_x509keypair:
            mock_create_x509keypair.return_value = self.fake_x509keypair
            x509keypair = objects.X509KeyPair(self.context,
                                              **self.fake_x509keypair)
            x509keypair.create()
            mock_create_x509keypair.assert_called_once_with(
                self.fake_x509keypair)
            self.assertEqual(self.context, x509keypair._context)

    def test_destroy(self):
        uuid = self.fake_x509keypair['uuid']
        with mock.patch.object(self.dbapi, 'get_x509keypair_by_uuid',
                               autospec=True) as mock_get_x509keypair:
            mock_get_x509keypair.return_value = self.fake_x509keypair
            with mock.patch.object(self.dbapi, 'destroy_x509keypair',
                                   autospec=True) as mock_destroy_x509keypair:
                x509keypair = objects.X509KeyPair.get_by_uuid(self.context,
                                                              uuid)
                x509keypair.destroy()
                mock_get_x509keypair.assert_called_once_with(self.context,
                                                             uuid)
                mock_destroy_x509keypair.assert_called_once_with(uuid)
                self.assertEqual(self.context, x509keypair._context)

    def test_save(self):
        uuid = self.fake_x509keypair['uuid']
        with mock.patch.object(self.dbapi, 'get_x509keypair_by_uuid',
                               autospec=True) as mock_get_x509keypair:
            mock_get_x509keypair.return_value = self.fake_x509keypair
            with mock.patch.object(self.dbapi, 'update_x509keypair',
                                   autospec=True) as mock_update_x509keypair:
                x509keypair = objects.X509KeyPair.get_by_uuid(self.context,
                                                              uuid)
                x509keypair.certificate = 'new_certificate'
                x509keypair.save()

                mock_get_x509keypair.assert_called_once_with(self.context,
                                                             uuid)
                mock_update_x509keypair.assert_called_once_with(
                    uuid, {'certificate': 'new_certificate'})
                self.assertEqual(self.context, x509keypair._context)

    def test_refresh(self):
        uuid = self.fake_x509keypair['uuid']
        new_uuid = uuidutils.generate_uuid()
        returns = [dict(self.fake_x509keypair, uuid=uuid),
                   dict(self.fake_x509keypair, uuid=new_uuid)]
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        with mock.patch.object(self.dbapi, 'get_x509keypair_by_uuid',
                               side_effect=returns,
                               autospec=True) as mock_get_x509keypair:
            x509keypair = objects.X509KeyPair.get_by_uuid(self.context, uuid)
            self.assertEqual(uuid, x509keypair.uuid)
            x509keypair.refresh()
            self.assertEqual(new_uuid, x509keypair.uuid)
            self.assertEqual(expected, mock_get_x509keypair.call_args_list)
            self.assertEqual(self.context, x509keypair._context)
