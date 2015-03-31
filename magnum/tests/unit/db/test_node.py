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

"""Tests for manipulating Nodes via the DB API"""

import six

from magnum.common import exception
from magnum.common import utils as magnum_utils
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils


class DbNodeTestCase(base.DbTestCase):

    def test_create_node(self):
        utils.create_test_node()

    def test_create_node_already_exists(self):
        utils.create_test_node()
        self.assertRaises(exception.NodeAlreadyExists,
                          utils.create_test_node)

    def test_create_node_instance_already_associated(self):
        instance_uuid = magnum_utils.generate_uuid()
        utils.create_test_node(uuid=magnum_utils.generate_uuid(),
                               ironic_node_id=instance_uuid)
        self.assertRaises(exception.InstanceAssociated,
                          utils.create_test_node,
                          uuid=magnum_utils.generate_uuid(),
                          ironic_node_id=instance_uuid)

    def test_get_node_by_id(self):
        node = utils.create_test_node()
        res = self.dbapi.get_node_by_id(self.context, node.id)
        self.assertEqual(node.id, res.id)
        self.assertEqual(node.uuid, res.uuid)

    def test_get_node_by_uuid(self):
        node = utils.create_test_node()
        res = self.dbapi.get_node_by_uuid(self.context, node.uuid)
        self.assertEqual(node.id, res.id)
        self.assertEqual(node.uuid, res.uuid)

    def test_get_node_that_does_not_exist(self):
        self.assertRaises(exception.NodeNotFound,
                          self.dbapi.get_node_by_id, self.context, 99)
        self.assertRaises(exception.NodeNotFound,
                          self.dbapi.get_node_by_uuid,
                          self.context,
                          magnum_utils.generate_uuid())

    def test_get_node_list(self):
        uuids = []
        for i in range(1, 6):
            node = utils.create_test_node(uuid=magnum_utils.generate_uuid())
            uuids.append(six.text_type(node['uuid']))
        res = self.dbapi.get_node_list(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    def test_get_node_list_with_filters(self):
        node1 = utils.create_test_node(type='virt',
            ironic_node_id=magnum_utils.generate_uuid(),
            uuid=magnum_utils.generate_uuid())
        node2 = utils.create_test_node(type='bare',
            uuid=magnum_utils.generate_uuid())

        res = self.dbapi.get_node_list(self.context, filters={'type': 'virt'})
        self.assertEqual([node1.id], [r.id for r in res])

        res = self.dbapi.get_node_list(self.context,
                                       filters={'type': 'bad-type'})
        self.assertEqual([], [r.id for r in res])

        res = self.dbapi.get_node_list(self.context,
                                       filters={'associated': True})
        self.assertEqual([node1.id], [r.id for r in res])

        res = self.dbapi.get_node_list(self.context,
                                       filters={'associated': False})
        self.assertEqual([node2.id], [r.id for r in res])

    def test_destroy_node(self):
        node = utils.create_test_node()
        self.dbapi.destroy_node(node.id)
        self.assertRaises(exception.NodeNotFound,
                          self.dbapi.get_node_by_id, self.context, node.id)

    def test_destroy_node_by_uuid(self):
        node = utils.create_test_node()
        self.dbapi.destroy_node(node.uuid)
        self.assertRaises(exception.NodeNotFound,
                          self.dbapi.get_node_by_uuid,
                          self.context, node.uuid)

    def test_destroy_node_that_does_not_exist(self):
        self.assertRaises(exception.NodeNotFound,
                          self.dbapi.destroy_node,
                          magnum_utils.generate_uuid())

    def test_update_node(self):
        node = utils.create_test_node()
        old_image = node.image_id
        new_image = 'new-image'
        self.assertNotEqual(old_image, new_image)

        res = self.dbapi.update_node(node.id, {'image_id': new_image})
        self.assertEqual(new_image, res.image_id)

    def test_update_node_not_found(self):
        node_uuid = magnum_utils.generate_uuid()
        new_image = 'new-image'
        self.assertRaises(exception.NodeNotFound, self.dbapi.update_node,
                          node_uuid, {'image_id': new_image})

    def test_update_node_uuid(self):
        node = utils.create_test_node()
        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.update_node, node.id,
                          {'uuid': ''})

    def test_update_node_associate_and_disassociate(self):
        node = utils.create_test_node()
        new_i_uuid = magnum_utils.generate_uuid()
        res = self.dbapi.update_node(node.id, {'ironic_node_id': new_i_uuid})
        self.assertEqual(new_i_uuid, res.ironic_node_id)
        res = self.dbapi.update_node(node.id, {'ironic_node_id': None})
        self.assertIsNone(res.ironic_node_id)

    def test_update_node_already_associated(self):
        node = utils.create_test_node()
        new_i_uuid_one = magnum_utils.generate_uuid()
        self.dbapi.update_node(node.id, {'ironic_node_id': new_i_uuid_one})
        new_i_uuid_two = magnum_utils.generate_uuid()
        self.assertRaises(exception.NodeAssociated,
                          self.dbapi.update_node, node.id,
                          {'ironic_node_id': new_i_uuid_two})

    def test_update_node_instance_already_associated(self):
        node1 = utils.create_test_node(uuid=magnum_utils.generate_uuid())
        new_i_uuid = magnum_utils.generate_uuid()
        self.dbapi.update_node(node1.id, {'ironic_node_id': new_i_uuid})
        node2 = utils.create_test_node(uuid=magnum_utils.generate_uuid())
        self.assertRaises(exception.InstanceAssociated,
                          self.dbapi.update_node, node2.id,
                          {'ironic_node_id': new_i_uuid})
