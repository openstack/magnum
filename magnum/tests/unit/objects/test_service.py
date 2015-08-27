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
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils


class TestServiceObject(base.DbTestCase):

    def setUp(self):
        super(TestServiceObject, self).setUp()
        self.fake_service = utils.get_test_service()

    def test_get_by_id(self):
        service_id = self.fake_service['id']
        with mock.patch.object(self.dbapi, 'get_service_by_id',
                               autospec=True) as mock_get_service:
            mock_get_service.return_value = self.fake_service
            service = objects.Service.get_by_id(self.context, service_id)
            mock_get_service.assert_called_once_with(self.context, service_id)
            self.assertEqual(self.context, service._context)

    def test_get_by_uuid(self):
        uuid = self.fake_service['uuid']
        with mock.patch.object(self.dbapi, 'get_service_by_uuid',
                               autospec=True) as mock_get_service:
            mock_get_service.return_value = self.fake_service
            service = objects.Service.get_by_uuid(self.context, uuid)
            mock_get_service.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, service._context)

    def test_get_by_name(self):
        name = self.fake_service['name']
        with mock.patch.object(self.dbapi, 'get_service_by_name',
                               autospec=True) as mock_get_service:
            mock_get_service.return_value = self.fake_service
            service = objects.Service.get_by_name(self.context, name)
            mock_get_service.assert_called_once_with(self.context, name)
            self.assertEqual(self.context, service._context)

    def test_list_by_bay_uuid(self):
        bay_uuid = self.fake_service['bay_uuid']
        with mock.patch.object(self.dbapi, 'get_services_by_bay_uuid',
                               autospec=True) as mock_get_service:
            mock_get_service.return_value = [self.fake_service]
            services = objects.Service.list_by_bay_uuid(self.context,
                                                        bay_uuid)
            self.assertThat(services, HasLength(1))
            mock_get_service.assert_called_once_with(self.context,
                                                     bay_uuid)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'get_service_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_service]
            services = objects.Service.list(self.context)
            self.assertEqual(mock_get_list.call_count, 1)
            self.assertThat(services, HasLength(1))
            self.assertIsInstance(services[0], objects.Service)
            self.assertEqual(self.context, services[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_service',
                               autospec=True) as mock_create_service:
            mock_create_service.return_value = self.fake_service
            service = objects.Service(self.context, **self.fake_service)
            service.create()
            mock_create_service.assert_called_once_with(self.fake_service)
            self.assertEqual(self.context, service._context)

    def test_destroy(self):
        uuid = self.fake_service['uuid']
        with mock.patch.object(self.dbapi, 'get_service_by_uuid',
                               autospec=True) as mock_get_service:
            mock_get_service.return_value = self.fake_service
            with mock.patch.object(self.dbapi, 'destroy_service',
                                   autospec=True) as mock_destroy_service:
                service = objects.Service.get_by_uuid(self.context, uuid)
                service.destroy()
                mock_get_service.assert_called_once_with(self.context, uuid)
                mock_destroy_service.assert_called_once_with(uuid)
                self.assertEqual(self.context, service._context)

    def test_save(self):
        uuid = self.fake_service['uuid']
        with mock.patch.object(self.dbapi, 'get_service_by_uuid',
                               autospec=True) as mock_get_service:
            mock_get_service.return_value = self.fake_service
            with mock.patch.object(self.dbapi, 'update_service',
                                   autospec=True) as mock_update_service:
                service = objects.Service.get_by_uuid(self.context, uuid)
                service.ports = [{'port': 4567}]
                service.save()

                mock_get_service.assert_called_once_with(self.context, uuid)
                mock_update_service.assert_called_once_with(
                    uuid, {'ports': [{'port': 4567}]})
                self.assertEqual(self.context, service._context)

    def test_refresh(self):
        uuid = self.fake_service['uuid']
        new_uuid = magnum_utils.generate_uuid()
        returns = [dict(self.fake_service, uuid=uuid),
                   dict(self.fake_service, uuid=new_uuid)]
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        with mock.patch.object(self.dbapi, 'get_service_by_uuid',
                               side_effect=returns,
                               autospec=True) as mock_get_service:
            service = objects.Service.get_by_uuid(self.context, uuid)
            self.assertEqual(uuid, service.uuid)
            service.refresh()
            self.assertEqual(new_uuid, service.uuid)
            self.assertEqual(expected, mock_get_service.call_args_list)
            self.assertEqual(self.context, service._context)
