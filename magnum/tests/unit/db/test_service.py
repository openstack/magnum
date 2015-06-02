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

"""Tests for manipulating Services via the DB API"""

import six

from magnum.common import exception
from magnum.common import utils as magnum_utils
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils as utils


class DbServiceTestCase(base.DbTestCase):

    def setUp(self):
        # This method creates a service for every test and
        # replaces a test for creating a service.
        super(DbServiceTestCase, self).setUp()
        self.bay = utils.create_test_bay()
        self.service = utils.create_test_service(bay_uuid=self.bay.uuid)

    def test_create_service_duplicated_uuid(self):
        self.assertRaises(exception.ServiceAlreadyExists,
                          utils.create_test_service,
                          uuid=self.service.uuid,
                          bay_uuid=self.bay.uuid)

    def test_get_service_by_id(self):
        res = self.dbapi.get_service_by_id(self.context, self.service.id)
        self.assertEqual(self.service.id, res.id)
        self.assertEqual(self.service.uuid, res.uuid)

    def test_get_service_by_uuid(self):
        res = self.dbapi.get_service_by_uuid(self.context, self.service.uuid)
        self.assertEqual(self.service.id, res.id)
        self.assertEqual(self.service.uuid, res.uuid)

    def test_get_service_by_name(self):
        res = self.dbapi.get_service_by_name(self.context, self.service.name)
        self.assertEqual(self.service.id, res.id)
        self.assertEqual(self.service.uuid, res.uuid)

    def test_get_service_by_name_multiple_service(self):
        utils.create_test_service(bay_uuid=self.bay.uuid,
                                  uuid=magnum_utils.generate_uuid())
        self.assertRaises(exception.Conflict, self.dbapi.get_service_by_name,
                          self.context, self.service.name)

    def test_get_service_by_name_not_found(self):
        self.assertRaises(exception.ServiceNotFound,
                          self.dbapi.get_service_by_name,
                          self.context, 'not_found')

    def test_get_service_that_does_not_exist(self):
        self.assertRaises(exception.ServiceNotFound,
                          self.dbapi.get_service_by_id, self.context, 999)
        self.assertRaises(exception.ServiceNotFound,
                          self.dbapi.get_service_by_uuid,
                          self.context,
                          magnum_utils.generate_uuid())

    def test_get_service_list(self):
        uuids = [self.service.uuid]
        for i in range(1, 6):
            service = utils.create_test_service(
                bay_uuid=self.bay.uuid,
                uuid=magnum_utils.generate_uuid())
            uuids.append(six.text_type(service.uuid))
        res = self.dbapi.get_service_list(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    def test_get_service_list_with_filters(self):
        bay1 = utils.get_test_bay(id=11, uuid=magnum_utils.generate_uuid())
        bay2 = utils.get_test_bay(id=12, uuid=magnum_utils.generate_uuid())
        self.dbapi.create_bay(bay1)
        self.dbapi.create_bay(bay2)

        service1 = utils.create_test_service(
            name='service-one',
            uuid=magnum_utils.generate_uuid(),
            bay_uuid=bay1['uuid'],
            ports=[{'port': 8000}])
        service2 = utils.create_test_service(
            name='service-two',
            uuid=magnum_utils.generate_uuid(),
            bay_uuid=bay2['uuid'],
            ports=[{'port': 8001}])

        res = self.dbapi.get_service_list(self.context,
                                          filters={'bay_uuid': bay1['uuid']})
        self.assertEqual([service1.id], [r.id for r in res])

        res = self.dbapi.get_service_list(self.context,
                                          filters={'bay_uuid': bay2['uuid']})
        self.assertEqual([service2.id], [r.id for r in res])

        res = self.dbapi.get_service_list(self.context,
                                          filters={'name': 'service-one'})
        self.assertEqual([service1.id], [r.id for r in res])

        res = self.dbapi.get_service_list(self.context,
                                          filters={'name': 'bad-service'})
        self.assertEqual([], [r.id for r in res])

        res = self.dbapi.get_service_list(self.context,
                                          filters={'ports': [{'port': 8000}]})
        self.assertEqual([service1.id], [r.id for r in res])

        res = self.dbapi.get_service_list(self.context,
                                          filters={'ports': [{'port': 8001}]})
        self.assertEqual([service2.id], [r.id for r in res])

    def test_get_service_list_bay_not_exist(self):
        res = self.dbapi.get_service_list(self.context, filters={
                                          'bay_uuid': self.bay.uuid})
        self.assertEqual(1, len(res))
        res = self.dbapi.get_service_list(self.context, filters={
            'bay_uuid': magnum_utils.generate_uuid()})
        self.assertEqual(0, len(res))

    def test_get_services_by_bay_uuid(self):
        res = self.dbapi.get_services_by_bay_uuid(self.bay.uuid)
        self.assertEqual(self.service.id, res[0].id)

    def test_get_services_by_bay_uuid_that_does_not_exist(self):
        res = self.dbapi.get_services_by_bay_uuid(magnum_utils.generate_uuid())
        self.assertEqual([], res)

    def test_destroy_service(self):
        self.dbapi.destroy_service(self.service.id)
        self.assertRaises(exception.ServiceNotFound,
                          self.dbapi.get_service_by_id,
                          self.context, self.service.id)

    def test_destroy_service_by_uuid(self):
        self.assertIsNotNone(self.dbapi.get_service_by_uuid(self.context,
                                                            self.service.uuid))
        self.dbapi.destroy_service(self.service.uuid)
        self.assertRaises(exception.ServiceNotFound,
                          self.dbapi.get_service_by_uuid,
                          self.context, self.service.uuid)

    def test_destroy_service_that_does_not_exist(self):
        self.assertRaises(exception.ServiceNotFound,
                          self.dbapi.destroy_service,
                          magnum_utils.generate_uuid())

    def test_update_service(self):
        old_name = self.service.name
        new_name = 'new-service'
        self.assertNotEqual(old_name, new_name)
        res = self.dbapi.update_service(self.service.id, {'name': new_name})
        self.assertEqual(new_name, res.name)

    def test_update_service_not_found(self):
        service_uuid = magnum_utils.generate_uuid()
        self.assertRaises(exception.ServiceNotFound, self.dbapi.update_service,
                          service_uuid, {'port': 80})

    def test_update_service_uuid(self):
        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.update_service, self.service.id,
                          {'uuid': ''})
