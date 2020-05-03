# Copyright (c) 2018 European Organization for Nuclear Research.
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

from magnum import objects
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils


class TestNodeGroupObject(base.DbTestCase):

    def setUp(self):
        super(TestNodeGroupObject, self).setUp()
        self.fake_nodegroup = utils.get_test_nodegroup()
        self.fake_nodegroup['docker_volume_size'] = 3
        self.fake_nodegroup['labels'] = {}

    def test_get_by_id(self):
        nodegroup_id = self.fake_nodegroup['id']
        cluster_id = self.fake_nodegroup['cluster_id']
        with mock.patch.object(self.dbapi, 'get_nodegroup_by_id',
                               autospec=True) as mock_get_nodegroup:
            mock_get_nodegroup.return_value = self.fake_nodegroup
            nodegroup = objects.NodeGroup.get(self.context, cluster_id,
                                              nodegroup_id)
            mock_get_nodegroup.assert_called_once_with(self.context,
                                                       cluster_id,
                                                       nodegroup_id)
            self.assertEqual(self.context, nodegroup._context)

    def test_get_by_uuid(self):
        uuid = self.fake_nodegroup['uuid']
        cluster_id = self.fake_nodegroup['cluster_id']
        with mock.patch.object(self.dbapi, 'get_nodegroup_by_uuid',
                               autospec=True) as mock_get_nodegroup:
            mock_get_nodegroup.return_value = self.fake_nodegroup
            nodegroup = objects.NodeGroup.get(self.context, cluster_id, uuid)
            mock_get_nodegroup.assert_called_once_with(self.context,
                                                       cluster_id, uuid)
            self.assertEqual(self.context, nodegroup._context)

    def test_get_by_name(self):
        name = self.fake_nodegroup['name']
        cluster_id = self.fake_nodegroup['cluster_id']
        with mock.patch.object(self.dbapi, 'get_nodegroup_by_name',
                               autospec=True) as mock_get_nodegroup:
            mock_get_nodegroup.return_value = self.fake_nodegroup
            nodegroup = objects.NodeGroup.get(self.context, cluster_id, name)
            mock_get_nodegroup.assert_called_once_with(self.context,
                                                       cluster_id, name)
            self.assertEqual(self.context, nodegroup._context)

    def test_list(self):
        cluster_id = self.fake_nodegroup['cluster_id']
        with mock.patch.object(self.dbapi, 'list_cluster_nodegroups',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_nodegroup]
            nodegroups = objects.NodeGroup.list(self.context, cluster_id)
            self.assertEqual(1, mock_get_list.call_count)
            mock_get_list.assert_called_once_with(
                self.context, cluster_id, limit=None, marker=None,
                filters=None, sort_dir=None, sort_key=None)
            self.assertThat(nodegroups, HasLength(1))
            self.assertIsInstance(nodegroups[0], objects.NodeGroup)
            self.assertEqual(self.context, nodegroups[0]._context)

    def test_list_with_filters(self):
        cluster_id = self.fake_nodegroup['cluster_id']
        with mock.patch.object(self.dbapi, 'list_cluster_nodegroups',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_nodegroup]
            filters = {'name': self.fake_nodegroup['name']}
            nodegroups = objects.NodeGroup.list(self.context, cluster_id,
                                                filters=filters)
            self.assertEqual(1, mock_get_list.call_count)
            mock_get_list.assert_called_once_with(
                self.context, cluster_id, limit=None, marker=None,
                filters=filters, sort_dir=None, sort_key=None)
            self.assertThat(nodegroups, HasLength(1))
            self.assertIsInstance(nodegroups[0], objects.NodeGroup)
            self.assertEqual(self.context, nodegroups[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_nodegroup',
                               autospec=True) as mock_create_nodegroup:
            mock_create_nodegroup.return_value = self.fake_nodegroup
            nodegroup = objects.NodeGroup(self.context, **self.fake_nodegroup)
            nodegroup.create()
            mock_create_nodegroup.assert_called_once_with(self.fake_nodegroup)
            self.assertEqual(self.context, nodegroup._context)

    def test_destroy(self):
        uuid = self.fake_nodegroup['uuid']
        cluster_id = self.fake_nodegroup['cluster_id']
        with mock.patch.object(self.dbapi, 'get_nodegroup_by_uuid',
                               autospec=True) as mock_get_nodegroup:
            mock_get_nodegroup.return_value = self.fake_nodegroup
            with mock.patch.object(self.dbapi, 'destroy_nodegroup',
                                   autospec=True) as mock_destroy_nodegroup:
                nodegroup = objects.NodeGroup.get_by_uuid(self.context,
                                                          cluster_id,
                                                          uuid)
                nodegroup.destroy()
                mock_get_nodegroup.assert_called_once_with(self.context,
                                                           cluster_id,
                                                           uuid)
                mock_destroy_nodegroup.assert_called_once_with(cluster_id,
                                                               uuid)
                self.assertEqual(self.context, nodegroup._context)

    def test_save(self):
        uuid = self.fake_nodegroup['uuid']
        cluster_id = self.fake_nodegroup['cluster_id']
        with mock.patch.object(self.dbapi, 'get_nodegroup_by_uuid',
                               autospec=True) as mock_get_nodegroup:
            mock_get_nodegroup.return_value = self.fake_nodegroup
            with mock.patch.object(self.dbapi, 'update_nodegroup',
                                   autospec=True) as mock_update_nodegroup:
                nodegroup = objects.NodeGroup.get_by_uuid(self.context,
                                                          cluster_id,
                                                          uuid)
                nodegroup.node_count = 10
                nodegroup.save()

                mock_get_nodegroup.assert_called_once_with(self.context,
                                                           cluster_id,
                                                           uuid)
                expected_changes = {
                    'node_count': 10,
                }
                mock_update_nodegroup.assert_called_once_with(
                    cluster_id, uuid, expected_changes)
                self.assertEqual(self.context, nodegroup._context)

    def test_refresh(self):
        uuid = self.fake_nodegroup['uuid']
        cluster_id = self.fake_nodegroup['cluster_id']
        new_uuid = uuidutils.generate_uuid()
        returns = [dict(self.fake_nodegroup, uuid=uuid),
                   dict(self.fake_nodegroup, uuid=new_uuid)]
        expected = [mock.call(self.context, cluster_id, uuid),
                    mock.call(self.context, cluster_id, uuid)]
        with mock.patch.object(self.dbapi, 'get_nodegroup_by_uuid',
                               side_effect=returns,
                               autospec=True) as mock_get_nodegroup:
            nodegroup = objects.NodeGroup.get_by_uuid(self.context,
                                                      cluster_id,
                                                      uuid)
            self.assertEqual(uuid, nodegroup.uuid)
            nodegroup.refresh()
            self.assertEqual(new_uuid, nodegroup.uuid)
            self.assertEqual(expected, mock_get_nodegroup.call_args_list)
            self.assertEqual(self.context, nodegroup._context)
