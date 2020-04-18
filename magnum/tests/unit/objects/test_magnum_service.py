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

from magnum import objects
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils


class TestMagnumServiceObject(base.DbTestCase):

    def setUp(self):
        super(TestMagnumServiceObject, self).setUp()
        self.fake_magnum_service = utils.get_test_magnum_service()

    def test_get_by_host_and_binary(self):
        with mock.patch.object(self.dbapi,
                               'get_magnum_service_by_host_and_binary',
                               autospec=True) as mock_get_magnum_service:
            mock_get_magnum_service.return_value = self.fake_magnum_service
            ms = objects.MagnumService.get_by_host_and_binary(self.context,
                                                              'fake-host',
                                                              'fake-bin')
            mock_get_magnum_service.assert_called_once_with('fake-host',
                                                            'fake-bin')
            self.assertEqual(self.context, ms._context)

    def test_get_by_host_and_binary_no_service(self):
        with mock.patch.object(self.dbapi, 'create_magnum_service',
                               autospec=True) as mock_get_magnum_service:
            mock_get_magnum_service.return_value = None
            ms = objects.MagnumService.get_by_host_and_binary(self.context,
                                                              'fake-host',
                                                              'fake-bin')

            self.assertIsNone(ms)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_magnum_service',
                               autospec=True) as mock_create_magnum_service:
            mock_create_magnum_service.return_value = self.fake_magnum_service
            ms_dict = {'host': 'fakehost', 'binary': 'fake-bin'}
            ms = objects.MagnumService(self.context, **ms_dict)
            ms.create(self.context)
            mock_create_magnum_service.assert_called_once_with(ms_dict)

    def test_destroy(self):
        with mock.patch.object(self.dbapi,
                               'get_magnum_service_by_host_and_binary',
                               autospec=True) as mock_get_magnum_service:
            mock_get_magnum_service.return_value = self.fake_magnum_service
            with mock.patch.object(self.dbapi,
                                   'destroy_magnum_service',
                                   autospec=True) as mock_destroy_ms:
                ms = objects.MagnumService.get_by_host_and_binary(
                    self.context, 'fake-host', 'fake-bin')
                ms.destroy()
                mock_get_magnum_service.assert_called_once_with(
                    'fake-host', 'fake-bin')
                mock_destroy_ms.assert_called_once_with(
                    self.fake_magnum_service['id'])
                self.assertEqual(self.context, ms._context)

    def test_save(self):
        with mock.patch.object(self.dbapi,
                               'get_magnum_service_by_host_and_binary',
                               autospec=True) as mock_get_magnum_service:
            mock_get_magnum_service.return_value = self.fake_magnum_service
            with mock.patch.object(self.dbapi,
                                   'update_magnum_service',
                                   autospec=True) as mock_update_ms:
                ms = objects.MagnumService.get_by_host_and_binary(
                    self.context, 'fake-host', 'fake-bin')
                ms.disabled = True
                ms.save()
                mock_get_magnum_service.assert_called_once_with(
                    'fake-host', 'fake-bin')
                mock_update_ms.assert_called_once_with(
                    self.fake_magnum_service['id'], {'disabled': True})
                self.assertEqual(self.context, ms._context)

    def test_report_state_up(self):
        with mock.patch.object(self.dbapi,
                               'get_magnum_service_by_host_and_binary',
                               autospec=True) as mock_get_magnum_service:
            mock_get_magnum_service.return_value = self.fake_magnum_service
            with mock.patch.object(self.dbapi,
                                   'update_magnum_service',
                                   autospec=True) as mock_update_ms:
                ms = objects.MagnumService.get_by_host_and_binary(
                    self.context, 'fake-host', 'fake-bin')
                last_report_count = self.fake_magnum_service['report_count']
                ms.report_state_up()
                mock_get_magnum_service.assert_called_once_with(
                    'fake-host', 'fake-bin')
                self.assertEqual(self.context, ms._context)
                mock_update_ms.assert_called_once_with(
                    self.fake_magnum_service['id'],
                    {'report_count': last_report_count + 1})
