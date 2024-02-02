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

from unittest import mock

from oslo_utils import uuidutils
from testtools.matchers import HasLength

from magnum.common import exception
from magnum import objects
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils


class TestClusterObject(base.DbTestCase):

    def setUp(self):
        super(TestClusterObject, self).setUp()
        self.fake_cluster = utils.get_test_cluster()
        self.fake_nodegroups = utils.get_nodegroups_for_cluster()
        self.fake_cluster['trust_id'] = 'trust_id'
        self.fake_cluster['trustee_username'] = 'trustee_user'
        self.fake_cluster['trustee_user_id'] = 'trustee_user_id'
        self.fake_cluster['trustee_password'] = 'password'
        self.fake_cluster['coe_version'] = 'fake-coe-version'
        self.fake_cluster['container_version'] = 'fake-container-version'
        cluster_template_id = self.fake_cluster['cluster_template_id']
        self.fake_cluster_template = objects.ClusterTemplate(
            uuid=cluster_template_id)
        self.fake_cluster['keypair'] = 'keypair1'
        self.fake_cluster['docker_volume_size'] = 3
        self.fake_cluster['labels'] = {}
        self.fake_cluster['health_status'] = 'HEALTHY'
        self.fake_cluster['health_status_reason'] = {}

    @mock.patch('magnum.objects.ClusterTemplate.get_by_uuid')
    def test_get_by_id(self, mock_cluster_template_get):
        cluster_id = self.fake_cluster['id']
        with mock.patch.object(self.dbapi, 'get_cluster_by_id',
                               autospec=True) as mock_get_cluster:
            mock_cluster_template_get.return_value = self.fake_cluster_template
            mock_get_cluster.return_value = self.fake_cluster
            cluster = objects.Cluster.get(self.context, cluster_id)
            mock_get_cluster.assert_called_once_with(self.context, cluster_id)
            self.assertEqual(self.context, cluster._context)
            self.assertEqual(cluster.cluster_template_id,
                             cluster.cluster_template.uuid)

    @mock.patch('magnum.objects.ClusterTemplate.get_by_uuid')
    def test_get_by_uuid(self, mock_cluster_template_get):
        uuid = self.fake_cluster['uuid']
        with mock.patch.object(self.dbapi, 'get_cluster_by_uuid',
                               autospec=True) as mock_get_cluster:
            mock_cluster_template_get.return_value = self.fake_cluster_template
            mock_get_cluster.return_value = self.fake_cluster
            cluster = objects.Cluster.get(self.context, uuid)
            mock_get_cluster.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, cluster._context)
            self.assertEqual(cluster.cluster_template_id,
                             cluster.cluster_template.uuid)

    @mock.patch('magnum.objects.ClusterTemplate.get_by_uuid')
    def test_get_by_name(self, mock_cluster_template_get):
        name = self.fake_cluster['name']
        with mock.patch.object(self.dbapi, 'get_cluster_by_name',
                               autospec=True) as mock_get_cluster:
            mock_cluster_template_get.return_value = self.fake_cluster_template
            mock_get_cluster.return_value = self.fake_cluster
            cluster = objects.Cluster.get_by_name(self.context, name)
            mock_get_cluster.assert_called_once_with(self.context, name)
            self.assertEqual(self.context, cluster._context)
            self.assertEqual(cluster.cluster_template_id,
                             cluster.cluster_template.uuid)

    def test_get_bad_id_and_uuid(self):
        self.assertRaises(exception.InvalidIdentity,
                          objects.Cluster.get, self.context, 'not-a-uuid')

    @mock.patch('magnum.objects.ClusterTemplate.get_by_uuid')
    def test_list(self, mock_cluster_template_get):
        with mock.patch.object(self.dbapi, 'get_cluster_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_cluster]
            mock_cluster_template_get.return_value = self.fake_cluster_template
            clusters = objects.Cluster.list(self.context)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(clusters, HasLength(1))
            self.assertIsInstance(clusters[0], objects.Cluster)
            self.assertEqual(self.context, clusters[0]._context)
            self.assertEqual(clusters[0].cluster_template_id,
                             clusters[0].cluster_template.uuid)

    @mock.patch('magnum.objects.ClusterTemplate.get_by_uuid')
    def test_list_all(self, mock_cluster_template_get):
        with mock.patch.object(self.dbapi, 'get_cluster_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_cluster]
            mock_cluster_template_get.return_value = self.fake_cluster_template
            self.context.all_tenants = True
            clusters = objects.Cluster.list(self.context)
            mock_get_list.assert_called_once_with(
                self.context, limit=None, marker=None, filters=None,
                sort_dir=None, sort_key=None)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(clusters, HasLength(1))
            self.assertIsInstance(clusters[0], objects.Cluster)
            self.assertEqual(self.context, clusters[0]._context)
            mock_cluster_template_get.assert_not_called()

    def test_list_with_filters(self):
        with mock.patch.object(self.dbapi, 'get_cluster_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_cluster]
            filters = {'name': 'cluster1'}
            clusters = objects.Cluster.list(self.context, filters=filters)

            mock_get_list.assert_called_once_with(self.context, sort_key=None,
                                                  sort_dir=None,
                                                  filters=filters, limit=None,
                                                  marker=None)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(clusters, HasLength(1))
            self.assertIsInstance(clusters[0], objects.Cluster)
            self.assertEqual(self.context, clusters[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_cluster',
                               autospec=True) as mock_create_cluster:
            mock_create_cluster.return_value = self.fake_cluster
            cluster = objects.Cluster(self.context, **self.fake_cluster)
            cluster.create()
            mock_create_cluster.assert_called_once_with(self.fake_cluster)
            self.assertEqual(self.context, cluster._context)

    def test_destroy(self):
        uuid = self.fake_cluster['uuid']
        with mock.patch.object(self.dbapi, 'get_cluster_by_uuid',
                               autospec=True) as mock_get_cluster:
            mock_get_cluster.return_value = self.fake_cluster
            with mock.patch.object(self.dbapi, 'destroy_cluster',
                                   autospec=True) as mock_destroy_cluster:
                cluster = objects.Cluster.get_by_uuid(self.context, uuid)
                cluster.destroy()
                mock_get_cluster.assert_called_once_with(self.context, uuid)
                mock_destroy_cluster.assert_called_once_with(uuid)
                self.assertEqual(self.context, cluster._context)

    def test_save(self):
        uuid = self.fake_cluster['uuid']
        with mock.patch.object(self.dbapi, 'get_cluster_by_uuid',
                               autospec=True) as mock_get_cluster:
            mock_get_cluster.return_value = self.fake_cluster
            with mock.patch.object(self.dbapi, 'update_cluster',
                                   autospec=True) as mock_update_cluster:
                cluster = objects.Cluster.get_by_uuid(self.context, uuid)
                cluster.status = 'DELETE_IN_PROGRESS'
                cluster.save()

                mock_get_cluster.assert_called_once_with(self.context, uuid)
                mock_update_cluster.assert_called_once_with(
                    uuid, {'status': 'DELETE_IN_PROGRESS'})
                self.assertEqual(self.context, cluster._context)

    def test_refresh(self):
        uuid = self.fake_cluster['uuid']
        new_uuid = uuidutils.generate_uuid()
        returns = [dict(self.fake_cluster, uuid=uuid),
                   dict(self.fake_cluster, uuid=new_uuid)]
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        with mock.patch.object(self.dbapi, 'get_cluster_by_uuid',
                               side_effect=returns,
                               autospec=True) as mock_get_cluster:
            cluster = objects.Cluster.get_by_uuid(self.context, uuid)
            self.assertEqual(uuid, cluster.uuid)
            cluster.refresh()
            self.assertEqual(new_uuid, cluster.uuid)
            self.assertEqual(expected, mock_get_cluster.call_args_list)
            self.assertEqual(self.context, cluster._context)
