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


class TestNodeObject(base.DbTestCase):

    def setUp(self):
        super(TestNodeObject, self).setUp()
        self.fake_node = utils.get_test_node()

    def test_get_by_id(self):
        node_id = self.fake_node['id']
        with mock.patch.object(self.dbapi, 'get_node_by_id',
                               autospec=True) as mock_get_node:
            mock_get_node.return_value = self.fake_node
            node = objects.Node.get(self.context, node_id)
            mock_get_node.assert_called_once_with(self.context, node_id)
            self.assertEqual(self.context, node._context)

    def test_get_by_uuid(self):
        uuid = self.fake_node['uuid']
        with mock.patch.object(self.dbapi, 'get_node_by_uuid',
                               autospec=True) as mock_get_node:
            mock_get_node.return_value = self.fake_node
            node = objects.Node.get(self.context, uuid)
            mock_get_node.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, node._context)

    def test_get_bad_id_and_uuid(self):
        self.assertRaises(exception.InvalidIdentity,
                          objects.Node.get, self.context, 'not-a-uuid')

    def test_list(self):
        with mock.patch.object(self.dbapi, 'get_node_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_node]
            nodes = objects.Node.list(self.context)
            self.assertEqual(mock_get_list.call_count, 1)
            self.assertThat(nodes, HasLength(1))
            self.assertIsInstance(nodes[0], objects.Node)
            self.assertEqual(self.context, nodes[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_node',
                               autospec=True) as mock_create_node:
            mock_create_node.return_value = self.fake_node
            node = objects.Node(self.context, **self.fake_node)
            node.create()
            mock_create_node.assert_called_once_with(self.fake_node)
            self.assertEqual(self.context, node._context)

    def test_destroy(self):
        uuid = self.fake_node['uuid']
        with mock.patch.object(self.dbapi, 'get_node_by_uuid',
                               autospec=True) as mock_get_node:
            mock_get_node.return_value = self.fake_node
            with mock.patch.object(self.dbapi, 'destroy_node',
                                   autospec=True) as mock_destroy_node:
                node = objects.Node.get_by_uuid(self.context, uuid)
                node.destroy()
                mock_get_node.assert_called_once_with(self.context, uuid)
                mock_destroy_node.assert_called_once_with(uuid)
                self.assertEqual(self.context, node._context)

    def test_save(self):
        uuid = self.fake_node['uuid']
        with mock.patch.object(self.dbapi, 'get_node_by_uuid',
                               autospec=True) as mock_get_node:
            mock_get_node.return_value = self.fake_node
            with mock.patch.object(self.dbapi, 'update_node',
                                   autospec=True) as mock_update_node:
                node = objects.Node.get_by_uuid(self.context, uuid)
                node.type = 'bare'
                node.save()

                mock_get_node.assert_called_once_with(self.context, uuid)
                mock_update_node.assert_called_once_with(
                        uuid, {'type': 'bare'})
                self.assertEqual(self.context, node._context)

    def test_refresh(self):
        uuid = self.fake_node['uuid']
        new_uuid = magnum_utils.generate_uuid()
        returns = [dict(self.fake_node, uuid=uuid),
                   dict(self.fake_node, uuid=new_uuid)]
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        with mock.patch.object(self.dbapi, 'get_node_by_uuid',
                               side_effect=returns,
                               autospec=True) as mock_get_node:
            node = objects.Node.get_by_uuid(self.context, uuid)
            self.assertEqual(uuid, node.uuid)
            node.refresh()
            self.assertEqual(new_uuid, node.uuid)
            self.assertEqual(expected, mock_get_node.call_args_list)
            self.assertEqual(self.context, node._context)
