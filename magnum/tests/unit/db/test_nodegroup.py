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

"""Tests for manipulating NodeGroups via the DB API"""
from oslo_utils import uuidutils

from magnum.common import exception
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils


class DbNodeGroupTestCase(base.DbTestCase):

    def test_create_nodegroup(self):
        utils.create_test_nodegroup()

    def test_create_nodegroup_already_exists(self):
        utils.create_test_nodegroup()
        self.assertRaises(exception.NodeGroupAlreadyExists,
                          utils.create_test_nodegroup)

    def test_create_nodegroup_same_name_same_cluster(self):
        # NOTE(ttsiouts): Don't allow the same name for nodegroups
        # in the same cluster.
        nodegroup = utils.create_test_nodegroup()
        new = {
            'name': nodegroup.name,
            'id': nodegroup.id + 8,
            'cluster_id': nodegroup.cluster_id
        }
        self.assertRaises(exception.NodeGroupAlreadyExists,
                          utils.create_test_nodegroup, **new)

    def test_create_nodegroup_same_name_different_cluster(self):
        # NOTE(ttsiouts): Verify nodegroups with the same name
        # but in different clusters are allowed.
        nodegroup = utils.create_test_nodegroup()
        new = {
            'name': nodegroup.name,
            'id': nodegroup.id + 8,
            'cluster_id': 'fake-cluster-uuid',
            'uuid': 'fake-nodegroup-uuid',
            'project_id': nodegroup.project_id,
        }
        try:
            utils.create_test_nodegroup(**new)
        except Exception:
            # Something went wrong, just fail the testcase
            self.assertTrue(False)

    def test_get_nodegroup_by_id(self):
        nodegroup = utils.create_test_nodegroup()
        res = self.dbapi.get_nodegroup_by_id(self.context,
                                             nodegroup.cluster_id,
                                             nodegroup.id)
        self.assertEqual(nodegroup.id, res.id)
        self.assertEqual(nodegroup.uuid, res.uuid)

    def test_get_nodegroup_by_name(self):
        nodegroup = utils.create_test_nodegroup()
        res = self.dbapi.get_nodegroup_by_name(self.context,
                                               nodegroup.cluster_id,
                                               nodegroup.name)
        self.assertEqual(nodegroup.name, res.name)
        self.assertEqual(nodegroup.uuid, res.uuid)

    def test_get_cluster_by_uuid(self):
        nodegroup = utils.create_test_nodegroup()
        res = self.dbapi.get_nodegroup_by_uuid(self.context,
                                               nodegroup.cluster_id,
                                               nodegroup.uuid)
        self.assertEqual(nodegroup.id, res.id)
        self.assertEqual(nodegroup.uuid, res.uuid)

    def test_get_nodegroup_that_does_not_exist(self):
        # Create a cluster with no nodegroups
        cluster = utils.create_test_cluster()
        self.assertRaises(exception.NodeGroupNotFound,
                          self.dbapi.get_nodegroup_by_id,
                          self.context, cluster.uuid,  100)
        self.assertRaises(exception.NodeGroupNotFound,
                          self.dbapi.get_nodegroup_by_uuid,
                          self.context, cluster.uuid,
                          '12345678-9999-0000-aaaa-123456789012')
        self.assertRaises(exception.NodeGroupNotFound,
                          self.dbapi.get_nodegroup_by_name,
                          self.context, cluster.uuid, 'not_found')

    def test_get_nodegroups_in_cluster(self):
        uuids_in_cluster = []
        uuids_not_in_cluster = []
        cluster = utils.create_test_cluster(uuid=uuidutils.generate_uuid())
        for i in range(2):
            ng = utils.create_test_nodegroup(uuid=uuidutils.generate_uuid(),
                                             name='test%(id)s' % {'id': i},
                                             cluster_id=cluster.uuid)
            uuids_in_cluster.append(ng.uuid)
        for i in range(2):
            ng = utils.create_test_nodegroup(uuid=uuidutils.generate_uuid(),
                                             name='test%(id)s' % {'id': i},
                                             cluster_id='fake_cluster')
            uuids_not_in_cluster.append(ng.uuid)
        res = self.dbapi.list_cluster_nodegroups(self.context, cluster.uuid)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids_in_cluster), sorted(res_uuids))
        for uuid in uuids_not_in_cluster:
            self.assertNotIn(uuid, res_uuids)

    def test_get_cluster_list_sorted(self):
        uuids = []
        cluster = utils.create_test_cluster(uuid=uuidutils.generate_uuid())
        for i in range(5):
            ng = utils.create_test_nodegroup(uuid=uuidutils.generate_uuid(),
                                             name='test%(id)s' % {'id': i},
                                             cluster_id=cluster.uuid)
            uuids.append(ng.uuid)
        res = self.dbapi.list_cluster_nodegroups(self.context, cluster.uuid,
                                                 sort_key='uuid')
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), res_uuids)

        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.list_cluster_nodegroups,
                          self.context,
                          cluster.uuid,
                          sort_key='not-there')

    def test_get_nodegroup_list_with_filters(self):
        cluster_dict = utils.get_test_cluster(
            id=1, uuid=uuidutils.generate_uuid())
        cluster = self.dbapi.create_cluster(cluster_dict)

        group1 = utils.create_test_nodegroup(
            name='group-one',
            cluster_id=cluster.uuid,
            flavor_id=1,
            uuid=uuidutils.generate_uuid(),
            node_count=1)
        group2 = utils.create_test_nodegroup(
            name='group-two',
            cluster_id=cluster.uuid,
            flavor_id=1,
            uuid=uuidutils.generate_uuid(),
            node_count=1)
        group3 = utils.create_test_nodegroup(
            name='group-four',
            cluster_id=cluster.uuid,
            flavor_id=2,
            uuid=uuidutils.generate_uuid(),
            node_count=3)

        filters = {'name': 'group-one'}
        res = self.dbapi.list_cluster_nodegroups(
            self.context, cluster.uuid, filters=filters)
        self.assertEqual([group1.id], [r.id for r in res])

        filters = {'node_count': 1}
        res = self.dbapi.list_cluster_nodegroups(
            self.context, cluster.uuid, filters=filters)
        self.assertEqual([group1.id, group2.id], [r.id for r in res])

        filters = {'flavor_id': 2, 'node_count': 3}
        res = self.dbapi.list_cluster_nodegroups(
            self.context, cluster.uuid, filters=filters)
        self.assertEqual([group3.id], [r.id for r in res])

        filters = {'name': 'group-five'}
        res = self.dbapi.list_cluster_nodegroups(
            self.context, cluster.uuid, filters=filters)
        self.assertEqual([], [r.id for r in res])

    def test_destroy_nodegroup(self):
        cluster = utils.create_test_cluster()
        nodegroup = utils.create_test_nodegroup()
        self.assertEqual(nodegroup.uuid, self.dbapi.get_nodegroup_by_uuid(
            self.context, cluster.uuid, nodegroup.uuid).uuid)
        self.dbapi.destroy_nodegroup(cluster.uuid, nodegroup.uuid)

        self.assertRaises(exception.NodeGroupNotFound,
                          self.dbapi.get_nodegroup_by_uuid,
                          self.context, cluster.uuid, nodegroup.uuid)

        self.assertRaises(exception.NodeGroupNotFound,
                          self.dbapi.destroy_nodegroup, cluster.uuid,
                          nodegroup.uuid)

    def test_destroy_nodegroup_by_uuid(self):
        cluster = utils.create_test_cluster()
        nodegroup = utils.create_test_nodegroup()
        self.assertIsNotNone(self.dbapi.get_nodegroup_by_uuid(self.context,
                                                              cluster.uuid,
                                                              nodegroup.uuid))
        self.dbapi.destroy_nodegroup(cluster.uuid, nodegroup.uuid)
        self.assertRaises(exception.NodeGroupNotFound,
                          self.dbapi.get_nodegroup_by_uuid, self.context,
                          cluster.uuid, nodegroup.uuid)

    def test_destroy_cluster_by_uuid_that_does_not_exist(self):
        self.assertRaises(exception.NodeGroupNotFound,
                          self.dbapi.destroy_nodegroup, 'c_uuid',
                          '12345678-9999-0000-aaaa-123456789012')

    def test_update_cluster(self):
        nodegroup = utils.create_test_nodegroup()
        old_flavor = nodegroup.flavor_id
        new_flavor = 5
        self.assertNotEqual(old_flavor, new_flavor)
        res = self.dbapi.update_nodegroup(nodegroup.cluster_id, nodegroup.id,
                                          {'flavor_id': new_flavor})
        self.assertEqual(new_flavor, res.flavor_id)

    def test_update_nodegroup_not_found(self):
        uuid = uuidutils.generate_uuid()
        self.assertRaises(exception.NodeGroupNotFound,
                          self.dbapi.update_nodegroup, "c_uuid", uuid,
                          {'node_count': 5})
