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

"""Tests for manipulating Containers via the DB API"""

import six

from magnum.common import exception
from magnum.common import utils as magnum_utils
from magnum.tests.db import base
from magnum.tests.db import utils


class DbContainerTestCase(base.DbTestCase):

    def test_create_container(self):
        utils.create_test_container()

    def test_create_container_already_exists(self):
        utils.create_test_container()
        self.assertRaises(exception.ContainerAlreadyExists,
                          utils.create_test_container)

    def test_get_container_by_id(self):
        container = utils.create_test_container()
        res = self.dbapi.get_container_by_id(container.id)
        self.assertEqual(container.id, res.id)
        self.assertEqual(container.uuid, res.uuid)

    def test_get_container_by_uuid(self):
        container = utils.create_test_container()
        res = self.dbapi.get_container_by_uuid(self.context,
                                               container.uuid)
        self.assertEqual(container.id, res.id)
        self.assertEqual(container.uuid, res.uuid)

    def test_get_container_that_does_not_exist(self):
        self.assertRaises(exception.ContainerNotFound,
                          self.dbapi.get_container_by_id, 99)
        self.assertRaises(exception.ContainerNotFound,
                          self.dbapi.get_container_by_uuid,
                          self.context,
                          magnum_utils.generate_uuid())

    def test_get_containerinfo_list_defaults(self):
        container_id_list = []
        for i in range(1, 6):
            container = utils.create_test_container(
                uuid=magnum_utils.generate_uuid())
            container_id_list.append(container.id)
        res = [i[0] for i in self.dbapi.get_containerinfo_list()]
        self.assertEqual(sorted(res), sorted(container_id_list))

    def test_get_containerinfo_list_with_cols(self):
        uuids = {}
        images = {}
        for i in range(1, 6):
            uuid = magnum_utils.generate_uuid()
            image = 'image' + str(i)
            container = utils.create_test_container(image_id=image, uuid=uuid)
            uuids[container.id] = uuid
            images[container.id] = image
        res = self.dbapi.get_containerinfo_list(columns=['id', 'image_id',
                                                         'uuid'])
        self.assertEqual(images, dict((r[0], r[1]) for r in res))
        self.assertEqual(uuids, dict((r[0], r[2]) for r in res))

    def test_get_containerinfo_list_with_filters(self):
        container1 = utils.create_test_container(name='c1',
            uuid=magnum_utils.generate_uuid(),
            project_id='fake-project1',
            user_id='fake-user1')
        container2 = utils.create_test_container(name='c2',
            uuid=magnum_utils.generate_uuid(),
            project_id='fake-project2',
            user_id='fake-user2')

        res = self.dbapi.get_containerinfo_list(filters={'name': 'c1'})
        self.assertEqual([container1.id], [r[0] for r in res])

        res = self.dbapi.get_containerinfo_list(filters={
                     'project_id': 'fake-project1', 'user_id': 'fake-user1'})
        self.assertEqual([container1.id], [r[0] for r in res])

        res = self.dbapi.get_containerinfo_list(filters={'name': 'c2'})
        self.assertEqual([container2.id], [r[0] for r in res])

        res = self.dbapi.get_containerinfo_list(filters={
                     'project_id': 'fake-project2', 'user_id': 'fake-user2'})
        self.assertEqual([container2.id], [r[0] for r in res])

        res = self.dbapi.get_containerinfo_list(filters={'name': 'bad-name'})
        self.assertEqual([], [r[0] for r in res])

    def test_get_container_list(self):
        uuids = []
        for i in range(1, 6):
            container = utils.create_test_container(
                uuid=magnum_utils.generate_uuid())
            uuids.append(six.text_type(container['uuid']))
        res = self.dbapi.get_container_list(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    def test_get_container_list_with_filters(self):
        container1 = utils.create_test_container(name='container-one',
            uuid=magnum_utils.generate_uuid())
        container2 = utils.create_test_container(name='container-two',
            uuid=magnum_utils.generate_uuid())

        res = self.dbapi.get_container_list(self.context,
                                            filters={'name': 'container-one'})
        self.assertEqual([container1.id], [r.id for r in res])

        res = self.dbapi.get_container_list(self.context,
                                            filters={'name': 'container-two'})
        self.assertEqual([container2.id], [r.id for r in res])

        res = self.dbapi.get_container_list(self.context,
                                            filters={'name': 'bad-container'})
        self.assertEqual([], [r.id for r in res])

    def test_destroy_container(self):
        container = utils.create_test_container()
        self.dbapi.destroy_container(container.id)
        self.assertRaises(exception.ContainerNotFound,
                          self.dbapi.get_container_by_id, container.id)

    def test_destroy_container_by_uuid(self):
        container = utils.create_test_container()
        self.dbapi.destroy_container(container.uuid)
        self.assertRaises(exception.ContainerNotFound,
                          self.dbapi.get_container_by_uuid,
                          self.context, container.uuid)

    def test_destroy_container_that_does_not_exist(self):
        self.assertRaises(exception.ContainerNotFound,
                          self.dbapi.destroy_container,
                          magnum_utils.generate_uuid())

    def test_update_container(self):
        container = utils.create_test_container()
        old_image = container.image_id
        new_image = 'new-image'
        self.assertNotEqual(old_image, new_image)

        res = self.dbapi.update_container(container.id,
                                          {'image_id': new_image})
        self.assertEqual(new_image, res.image_id)

    def test_update_container_not_found(self):
        container_uuid = magnum_utils.generate_uuid()
        new_image = 'new-image'
        self.assertRaises(exception.ContainerNotFound,
                          self.dbapi.update_container,
                          container_uuid, {'image_id': new_image})

    def test_update_container_uuid(self):
        container = utils.create_test_container()
        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.update_container, container.id,
                          {'uuid': ''})
