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


class TestFederationObject(base.DbTestCase):
    def setUp(self):
        super(TestFederationObject, self).setUp()
        self.fake_federation = utils.get_test_federation(
            uuid=uuidutils.generate_uuid(),
            hostcluster_id=uuidutils.generate_uuid(),
            member_ids=[]
        )

    def test_get_by_id(self):
        federation_id = self.fake_federation['id']
        with mock.patch.object(self.dbapi, 'get_federation_by_id',
                               autospec=True) as mock_get_federation:
            mock_get_federation.return_value = self.fake_federation
            federation = objects.Federation.get(self.context, federation_id)
            mock_get_federation.assert_called_once_with(self.context,
                                                        federation_id)
            self.assertEqual(self.context, federation._context)

    def test_get_by_uuid(self):
        federation_uuid = self.fake_federation['uuid']
        with mock.patch.object(self.dbapi, 'get_federation_by_uuid',
                               autospec=True) as mock_get_federation:
            mock_get_federation.return_value = self.fake_federation
            federation = objects.Federation.get(self.context, federation_uuid)
            mock_get_federation.assert_called_once_with(self.context,
                                                        federation_uuid)
            self.assertEqual(self.context, federation._context)

    def test_get_by_name(self):
        name = self.fake_federation['name']
        with mock.patch.object(self.dbapi, 'get_federation_by_name',
                               autospec=True) as mock_get_federation:
            mock_get_federation.return_value = self.fake_federation
            federation = objects.Federation.get_by_name(self.context, name)
            mock_get_federation.assert_called_once_with(self.context, name)
            self.assertEqual(self.context, federation._context)

    def test_get_bad_id_and_uuid(self):
        self.assertRaises(exception.InvalidIdentity,
                          objects.Federation.get, self.context, 'not-a-uuid')

    def test_list(self):
        with mock.patch.object(self.dbapi, 'get_federation_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_federation]
            federations = objects.Federation.list(self.context)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(federations, HasLength(1))
            self.assertIsInstance(federations[0], objects.Federation)
            self.assertEqual(self.context, federations[0]._context)

    def test_list_all(self):
        with mock.patch.object(self.dbapi, 'get_federation_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_federation]
            self.context.all_tenants = True
            federations = objects.Federation.list(self.context)
            mock_get_list.assert_called_once_with(
                self.context, limit=None, marker=None, filters=None,
                sort_dir=None, sort_key=None)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(federations, HasLength(1))
            self.assertIsInstance(federations[0], objects.Federation)
            self.assertEqual(self.context, federations[0]._context)

    def test_list_with_filters(self):
        with mock.patch.object(self.dbapi, 'get_federation_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_federation]
            filters = {'name': 'federation1'}
            federations = objects.Federation.list(self.context,
                                                  filters=filters)

            mock_get_list.assert_called_once_with(self.context, sort_key=None,
                                                  sort_dir=None,
                                                  filters=filters, limit=None,
                                                  marker=None)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(federations, HasLength(1))
            self.assertIsInstance(federations[0], objects.Federation)
            self.assertEqual(self.context, federations[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_federation',
                               autospec=True) as mock_create_federation:
            mock_create_federation.return_value = self.fake_federation
            federation = objects.Federation(self.context,
                                            **self.fake_federation)
            federation.create()
            mock_create_federation.assert_called_once_with(
                self.fake_federation)
            self.assertEqual(self.context, federation._context)

    def test_destroy(self):
        uuid = self.fake_federation['uuid']
        with mock.patch.object(self.dbapi, 'get_federation_by_uuid',
                               autospec=True) as mock_get_federation:
            mock_get_federation.return_value = self.fake_federation
            with mock.patch.object(self.dbapi, 'destroy_federation',
                                   autospec=True) as mock_destroy_federation:
                federation = objects.Federation.get_by_uuid(self.context, uuid)
                federation.destroy()
                mock_get_federation.assert_called_once_with(self.context, uuid)
                mock_destroy_federation.assert_called_once_with(uuid)
                self.assertEqual(self.context, federation._context)

    def test_save(self):
        uuid = self.fake_federation['uuid']
        with mock.patch.object(self.dbapi, 'get_federation_by_uuid',
                               autospec=True) as mock_get_federation:
            mock_get_federation.return_value = self.fake_federation
            with mock.patch.object(self.dbapi, 'update_federation',
                                   autospec=True) as mock_update_federation:
                federation = objects.Federation.get_by_uuid(self.context, uuid)
                federation.member_ids = ['new-member']
                federation.save()

                mock_get_federation.assert_called_once_with(self.context, uuid)
                mock_update_federation.assert_called_once_with(
                    uuid, {'member_ids': ['new-member']})
                self.assertEqual(self.context, federation._context)

    def test_refresh(self):
        uuid = self.fake_federation['uuid']
        new_uuid = uuidutils.generate_uuid()
        returns = [dict(self.fake_federation, uuid=uuid),
                   dict(self.fake_federation, uuid=new_uuid)]
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        with mock.patch.object(self.dbapi, 'get_federation_by_uuid',
                               side_effect=returns,
                               autospec=True) as mock_get_federation:
            federation = objects.Federation.get_by_uuid(self.context, uuid)
            self.assertEqual(uuid, federation.uuid)
            federation.refresh()
            self.assertEqual(new_uuid, federation.uuid)
            self.assertEqual(expected, mock_get_federation.call_args_list)
            self.assertEqual(self.context, federation._context)
