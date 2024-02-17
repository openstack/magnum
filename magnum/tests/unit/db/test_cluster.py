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

"""Tests for manipulating Clusters via the DB API"""
from oslo_utils import uuidutils

from magnum.common import context
from magnum.common import exception
from magnum.objects.fields import ClusterStatus as cluster_status
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils


class DbClusterTestCase(base.DbTestCase):

    def test_create_cluster(self):
        utils.create_test_cluster()

    def test_create_cluster_nullable_cluster_template_id(self):
        utils.create_test_cluster(cluster_template_id=None)

    def test_create_cluster_already_exists(self):
        utils.create_test_cluster()
        self.assertRaises(exception.ClusterAlreadyExists,
                          utils.create_test_cluster)

    def test_get_cluster_by_id(self):
        cluster = utils.create_test_cluster()
        res = self.dbapi.get_cluster_by_id(self.context, cluster.id)
        self.assertEqual(cluster.id, res.id)
        self.assertEqual(cluster.uuid, res.uuid)

    def test_get_cluster_by_name(self):
        cluster = utils.create_test_cluster()
        res = self.dbapi.get_cluster_by_name(self.context, cluster.name)
        self.assertEqual(cluster.name, res.name)
        self.assertEqual(cluster.uuid, res.uuid)

    def test_get_cluster_by_uuid(self):
        cluster = utils.create_test_cluster()
        res = self.dbapi.get_cluster_by_uuid(self.context, cluster.uuid)
        self.assertEqual(cluster.id, res.id)
        self.assertEqual(cluster.uuid, res.uuid)

    def test_get_cluster_that_does_not_exist(self):
        self.assertRaises(exception.ClusterNotFound,
                          self.dbapi.get_cluster_by_id,
                          self.context, 999)
        self.assertRaises(exception.ClusterNotFound,
                          self.dbapi.get_cluster_by_uuid,
                          self.context,
                          '12345678-9999-0000-aaaa-123456789012')
        self.assertRaises(exception.ClusterNotFound,
                          self.dbapi.get_cluster_by_name,
                          self.context, 'not_found')

    def test_get_cluster_by_name_multiple_cluster(self):
        utils.create_test_cluster(
            id=1, name='clusterone',
            uuid=uuidutils.generate_uuid())
        utils.create_test_cluster(
            id=2, name='clusterone',
            uuid=uuidutils.generate_uuid())
        self.assertRaises(exception.Conflict,
                          self.dbapi.get_cluster_by_name,
                          self.context, 'clusterone')

    def test_get_all_cluster_stats(self):
        uuid1 = uuidutils.generate_uuid()
        utils.create_test_cluster(
            id=1, name='clusterone',
            uuid=uuid1)
        utils.create_nodegroups_for_cluster(cluster_id=uuid1)
        uuid2 = uuidutils.generate_uuid()
        utils.create_test_cluster(
            id=2, name='clustertwo',
            uuid=uuid2)
        utils.create_nodegroups_for_cluster(cluster_id=uuid2)
        ret = self.dbapi.get_cluster_stats(self.context)
        self.assertEqual(ret, (2, 12))

    def test_get_one_tenant_cluster_stats(self):
        uuid1 = uuidutils.generate_uuid()
        utils.create_test_cluster(
            id=1, name='clusterone', project_id='proj1',
            uuid=uuid1)
        utils.create_nodegroups_for_cluster(
            cluster_id=uuid1, project_id='proj1')
        uuid2 = uuidutils.generate_uuid()
        utils.create_test_cluster(
            id=2, name='clustertwo', project_id='proj2',
            uuid=uuid2)
        utils.create_nodegroups_for_cluster(
            cluster_id=uuid2, project_id='proj2')
        ret = self.dbapi.get_cluster_stats(self.context, 'proj2')
        self.assertEqual(ret, (1, 6))

    def test_get_cluster_list(self):
        uuids = []
        for i in range(1, 6):
            cluster = utils.create_test_cluster(uuid=uuidutils.generate_uuid())
            uuids.append(str(cluster['uuid']))
        res = self.dbapi.get_cluster_list(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    def test_get_cluster_list_sorted(self):
        uuids = []
        for _ in range(5):
            cluster = utils.create_test_cluster(uuid=uuidutils.generate_uuid())
            uuids.append(str(cluster.uuid))
        res = self.dbapi.get_cluster_list(self.context, sort_key='uuid')
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), res_uuids)

        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.get_cluster_list,
                          self.context,
                          sort_key='foo')

    def test_get_cluster_list_with_filters(self):
        ct1 = utils.get_test_cluster_template(id=1,
                                              uuid=uuidutils.generate_uuid())
        ct2 = utils.get_test_cluster_template(id=2,
                                              uuid=uuidutils.generate_uuid())
        self.dbapi.create_cluster_template(ct1)
        self.dbapi.create_cluster_template(ct2)

        uuid1 = uuidutils.generate_uuid()
        cluster1 = utils.create_test_cluster(
            name='cluster-one',
            uuid=uuid1,
            cluster_template_id=ct1['uuid'],
            status=cluster_status.CREATE_IN_PROGRESS)
        utils.create_nodegroups_for_cluster(cluster_id=uuid1)
        uuid2 = uuidutils.generate_uuid()
        cluster2 = utils.create_test_cluster(
            name='cluster-two',
            uuid=uuid2,
            cluster_template_id=ct2['uuid'],
            status=cluster_status.UPDATE_IN_PROGRESS)
        utils.create_nodegroups_for_cluster(
            cluster_id=uuid2, node_count=1, master_count=1)
        cluster3 = utils.create_test_cluster(
            name='cluster-three',
            status=cluster_status.DELETE_IN_PROGRESS)
        utils.create_nodegroups_for_cluster(
            node_count=2, master_count=5)

        res = self.dbapi.get_cluster_list(
            self.context, filters={'cluster_template_id': ct1['uuid']})
        self.assertEqual([cluster1.id], [r.id for r in res])

        res = self.dbapi.get_cluster_list(
            self.context, filters={'cluster_template_id': ct2['uuid']})
        self.assertEqual([cluster2.id], [r.id for r in res])

        res = self.dbapi.get_cluster_list(self.context,
                                          filters={'name': 'cluster-one'})
        self.assertEqual([cluster1.id], [r.id for r in res])

        res = self.dbapi.get_cluster_list(self.context,
                                          filters={'name': 'bad-cluster'})
        self.assertEqual([], [r.id for r in res])

        res = self.dbapi.get_cluster_list(self.context,
                                          filters={'node_count': 3})
        self.assertEqual([cluster1.id], [r.id for r in res])

        res = self.dbapi.get_cluster_list(self.context,
                                          filters={'node_count': 1})
        self.assertEqual([cluster2.id], [r.id for r in res])

        res = self.dbapi.get_cluster_list(self.context,
                                          filters={'master_count': 3})
        self.assertEqual([cluster1.id], [r.id for r in res])

        res = self.dbapi.get_cluster_list(self.context,
                                          filters={'master_count': 1})
        self.assertEqual([cluster2.id], [r.id for r in res])

        # Check that both filters have to be valid
        filters = {'master_count': 1, 'node_count': 1}
        res = self.dbapi.get_cluster_list(self.context, filters=filters)
        self.assertEqual([cluster2.id], [r.id for r in res])

        filters = {'master_count': 1, 'node_count': 2}
        res = self.dbapi.get_cluster_list(self.context, filters=filters)
        self.assertEqual(0, len(res))

        filters = {'status': [cluster_status.CREATE_IN_PROGRESS,
                              cluster_status.DELETE_IN_PROGRESS]}
        res = self.dbapi.get_cluster_list(self.context,
                                          filters=filters)
        self.assertEqual([cluster1.id, cluster3.id], [r.id for r in res])

    def test_get_cluster_list_by_admin_all_tenants(self):
        uuids = []
        for i in range(1, 6):
            cluster = utils.create_test_cluster(
                uuid=uuidutils.generate_uuid(),
                project_id=uuidutils.generate_uuid(),
                user_id=uuidutils.generate_uuid())
            uuids.append(str(cluster['uuid']))
        ctx = context.make_admin_context(all_tenants=True)
        res = self.dbapi.get_cluster_list(ctx)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    def test_get_cluster_list_cluster_template_not_exist(self):
        utils.create_test_cluster()
        self.assertEqual(1, len(self.dbapi.get_cluster_list(self.context)))
        res = self.dbapi.get_cluster_list(self.context, filters={
            'cluster_template_id': uuidutils.generate_uuid()})
        self.assertEqual(0, len(res))

    def test_destroy_cluster(self):
        cluster = utils.create_test_cluster()
        self.assertIsNotNone(self.dbapi.get_cluster_by_id(self.context,
                                                          cluster.id))
        self.dbapi.destroy_cluster(cluster.id)
        self.assertRaises(exception.ClusterNotFound,
                          self.dbapi.get_cluster_by_id,
                          self.context, cluster.id)

    def test_destroy_cluster_by_uuid(self):
        cluster = utils.create_test_cluster()
        self.assertIsNotNone(self.dbapi.get_cluster_by_uuid(self.context,
                                                            cluster.uuid))
        self.dbapi.destroy_cluster(cluster.uuid)
        self.assertRaises(exception.ClusterNotFound,
                          self.dbapi.get_cluster_by_uuid, self.context,
                          cluster.uuid)

    def test_destroy_cluster_by_id_that_does_not_exist(self):
        self.assertRaises(exception.ClusterNotFound,
                          self.dbapi.destroy_cluster,
                          '12345678-9999-0000-aaaa-123456789012')

    def test_destroy_cluster_by_uuid_that_does_not_exist(self):
        self.assertRaises(exception.ClusterNotFound,
                          self.dbapi.destroy_cluster, '999')

    def test_update_cluster(self):
        cluster = utils.create_test_cluster()
        old_status = cluster.status
        new_status = 'UPDATE_IN_PROGRESS'
        self.assertNotEqual(old_status, new_status)
        res = self.dbapi.update_cluster(cluster.id, {'status': new_status})
        self.assertEqual(new_status, res.status)

    def test_update_cluster_not_found(self):
        cluster_uuid = uuidutils.generate_uuid()
        self.assertRaises(exception.ClusterNotFound, self.dbapi.update_cluster,
                          cluster_uuid, {'node_count': 5})

    def test_update_cluster_uuid(self):
        cluster = utils.create_test_cluster()
        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.update_cluster, cluster.id,
                          {'uuid': ''})
