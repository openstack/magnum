# Copyright 2015 Intel, Inc
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from unittest import mock

from oslo_utils import uuidutils

from magnum.common import context
from magnum.common.rpc_service import CONF
from magnum.db.sqlalchemy import api as dbapi
from magnum.drivers.common import driver
from magnum.drivers.common import k8s_monitor
from magnum import objects
from magnum.objects.fields import ClusterHealthStatus as cluster_health_status
from magnum.objects.fields import ClusterStatus as cluster_status
from magnum.service import periodic
from magnum.tests import base
from magnum.tests import fake_notifier
from magnum.tests import fakes
from magnum.tests.unit.db import utils


class fake_status(object):
    def __init__(self, **kw):
        for key, val in kw.items():
            setattr(self, key, val)


# This dictionary will be populated by setUp to help mock
# the nodegroup list magnum.db.api.get_cluster_nodergoups.
cluster_ngs = {}


def mock_nodegroup_list(cls, dummy_context, cluster_id, **kwargs):
    try:
        return cluster_ngs[cluster_id]
    except KeyError:
        return []


class PeriodicTestCase(base.TestCase):

    def setUp(self):
        super(PeriodicTestCase, self).setUp()

        self.context = context.make_admin_context()

        uuid1 = uuidutils.generate_uuid()
        cluster_attrs = {'id': 1, 'uuid': uuid1,
                         'status': cluster_status.CREATE_IN_PROGRESS,
                         'status_reason': 'no change',
                         'keypair': 'keipair1', 'health_status': None}
        cluster1 = utils.get_test_cluster(**cluster_attrs)
        ngs1 = utils.get_nodegroups_for_cluster()
        uuid2 = uuidutils.generate_uuid()
        cluster_attrs.update({'id': 2, 'uuid': uuid2,
                              'status': cluster_status.DELETE_IN_PROGRESS})
        cluster2 = utils.get_test_cluster(**cluster_attrs)
        ngs2 = utils.get_nodegroups_for_cluster()
        uuid3 = uuidutils.generate_uuid()
        cluster_attrs.update({'id': 3, 'uuid': uuid3,
                              'status': cluster_status.UPDATE_IN_PROGRESS})
        cluster3 = utils.get_test_cluster(**cluster_attrs)
        ngs3 = utils.get_nodegroups_for_cluster()
        uuid4 = uuidutils.generate_uuid()
        cluster_attrs.update({'id': 4, 'uuid': uuid4,
                              'status': cluster_status.DELETE_IN_PROGRESS})
        cluster4 = utils.get_test_cluster(**cluster_attrs)
        ngs4 = utils.get_nodegroups_for_cluster()
        uuid5 = uuidutils.generate_uuid()
        cluster_attrs.update({'id': 5, 'uuid': uuid5,
                              'status': cluster_status.ROLLBACK_IN_PROGRESS})
        cluster5 = utils.get_test_cluster(**cluster_attrs)
        ngs5 = utils.get_nodegroups_for_cluster()

        self.nodegroups1 = [
            objects.NodeGroup(self.context, **ngs1['master']),
            objects.NodeGroup(self.context, **ngs1['worker'])
        ]
        self.nodegroups2 = [
            objects.NodeGroup(self.context, **ngs2['master']),
            objects.NodeGroup(self.context, **ngs2['worker'])
        ]
        self.nodegroups3 = [
            objects.NodeGroup(self.context, **ngs3['master']),
            objects.NodeGroup(self.context, **ngs3['worker'])
        ]
        self.nodegroups4 = [
            objects.NodeGroup(self.context, **ngs4['master']),
            objects.NodeGroup(self.context, **ngs4['worker'])
        ]
        self.nodegroups5 = [
            objects.NodeGroup(self.context, **ngs5['master']),
            objects.NodeGroup(self.context, **ngs5['worker'])
        ]

        self.cluster1 = objects.Cluster(self.context, **cluster1)
        self.cluster2 = objects.Cluster(self.context, **cluster2)
        self.cluster3 = objects.Cluster(self.context, **cluster3)
        self.cluster4 = objects.Cluster(self.context, **cluster4)
        self.cluster5 = objects.Cluster(self.context, **cluster5)

        # This is used to mock the get_cluster_nodegroups from magnum.db.api.
        # It's not the greatest way to do it, But we have to populate the
        # dictionary in the runtime (or have statically defined uuids per NG).
        global cluster_ngs
        cluster_ngs = {
            self.cluster1.uuid: self.nodegroups1,
            self.cluster2.uuid: self.nodegroups2,
            self.cluster3.uuid: self.nodegroups3,
            self.cluster4.uuid: self.nodegroups4,
            self.cluster5.uuid: self.nodegroups5
        }

        self.new_status1 = fake_status(
            status=cluster_status.CREATE_COMPLETE,
            status_reason='fake_reason_11')
        self.new_status2 = fake_status(
            status=cluster_status.DELETE_IN_PROGRESS,
            status_reason='fake_reason_11')
        self.new_status3 = fake_status(
            status=cluster_status.UPDATE_COMPLETE,
            status_reason='fake_reason_33')
        self.new_status5 = fake_status(
            status=cluster_status.ROLLBACK_COMPLETE,
            status_reason='fake_reason_55')

        self.new_statuses = {
            uuid1: self.new_status1,
            uuid2: self.new_status2,
            uuid3: self.new_status3,
            uuid5: self.new_status5
        }

        self.mock_driver = mock.MagicMock(spec=driver.Driver)

        def _mock_update_status(context, cluster):
            try:
                new_status = self.new_statuses[cluster.uuid]
            except KeyError:
                cluster.status_reason = "Cluster %s not found" % cluster.uuid
                if cluster.status == "DELETE_IN_PROGRESS":
                    cluster.status = cluster_status.DELETE_COMPLETE
                else:
                    cluster.status = cluster.status.replace("IN_PROGRESS",
                                                            "FAILED")
                    cluster.status = cluster.status.replace("COMPLETE",
                                                            "FAILED")
            else:
                if cluster.status != new_status.status:
                    cluster.status = new_status.status
                    cluster.status_reason = new_status.status_reason

        self.mock_driver.update_cluster_status.side_effect = (
            _mock_update_status)

    @mock.patch('oslo_service.loopingcall.FixedIntervalLoopingCall',
                new=fakes.FakeLoopingCall)
    @mock.patch('magnum.drivers.common.driver.Driver.get_driver_for_cluster')
    @mock.patch('magnum.objects.Cluster.list')
    @mock.patch.object(dbapi.Connection, 'destroy_nodegroup')
    @mock.patch.object(dbapi.Connection, 'destroy_cluster')
    def test_sync_cluster_status_changes(self, mock_db_destroy,
                                         mock_ng_destroy,
                                         mock_cluster_list,
                                         mock_get_driver):

        mock_cluster_list.return_value = [self.cluster1, self.cluster2,
                                          self.cluster3, self.cluster4,
                                          self.cluster5]
        mock_get_driver.return_value = self.mock_driver

        with mock.patch.object(dbapi.Connection, 'list_cluster_nodegroups',
                               mock_nodegroup_list):
            periodic.MagnumPeriodicTasks(CONF).sync_cluster_status(None)

            self.assertEqual(cluster_status.CREATE_COMPLETE,
                             self.cluster1.status)
            self.assertEqual('fake_reason_11', self.cluster1.status_reason)
            # make sure cluster 2 didn't change
            self.assertEqual(cluster_status.DELETE_IN_PROGRESS,
                             self.cluster2.status)
            self.assertEqual('no change', self.cluster2.status_reason)
            self.assertEqual(cluster_status.UPDATE_COMPLETE,
                             self.cluster3.status)
            self.assertEqual('fake_reason_33', self.cluster3.status_reason)
            self.assertEqual(2, mock_ng_destroy.call_count)
            mock_db_destroy.assert_called_once_with(self.cluster4.uuid)
            self.assertEqual(cluster_status.ROLLBACK_COMPLETE,
                             self.cluster5.status)
            self.assertEqual('fake_reason_55', self.cluster5.status_reason)
            notifications = fake_notifier.NOTIFICATIONS
            self.assertEqual(4, len(notifications))

    @mock.patch('oslo_service.loopingcall.FixedIntervalLoopingCall',
                new=fakes.FakeLoopingCall)
    @mock.patch('magnum.drivers.common.driver.Driver.get_driver_for_cluster')
    @mock.patch('magnum.objects.Cluster.list')
    def test_sync_cluster_status_not_changes(self, mock_cluster_list,
                                             mock_get_driver):

        self.new_status1.status = self.cluster1.status
        self.new_status2.status = self.cluster2.status
        self.new_status3.status = self.cluster3.status
        self.new_status5.status = self.cluster5.status
        mock_cluster_list.return_value = [self.cluster1, self.cluster2,
                                          self.cluster3, self.cluster5]
        mock_get_driver.return_value = self.mock_driver

        periodic.MagnumPeriodicTasks(CONF).sync_cluster_status(None)

        self.assertEqual(cluster_status.CREATE_IN_PROGRESS,
                         self.cluster1.status)
        self.assertEqual('no change', self.cluster1.status_reason)
        self.assertEqual(cluster_status.DELETE_IN_PROGRESS,
                         self.cluster2.status)
        self.assertEqual('no change', self.cluster2.status_reason)
        self.assertEqual(cluster_status.UPDATE_IN_PROGRESS,
                         self.cluster3.status)
        self.assertEqual('no change', self.cluster3.status_reason)
        self.assertEqual(cluster_status.ROLLBACK_IN_PROGRESS,
                         self.cluster5.status)
        self.assertEqual('no change', self.cluster5.status_reason)
        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(0, len(notifications))

    @mock.patch('oslo_service.loopingcall.FixedIntervalLoopingCall',
                new=fakes.FakeLoopingCall)
    @mock.patch('magnum.drivers.common.driver.Driver.get_driver_for_cluster')
    @mock.patch('magnum.objects.Cluster.list')
    @mock.patch.object(dbapi.Connection, 'destroy_cluster')
    @mock.patch.object(dbapi.Connection, 'destroy_nodegroup')
    def test_sync_cluster_status_not_found(self, mock_ng_destroy,
                                           mock_db_destroy,
                                           mock_cluster_list,
                                           mock_get_driver):
        self.new_statuses.clear()
        mock_get_driver.return_value = self.mock_driver
        mock_cluster_list.return_value = [self.cluster1, self.cluster2,
                                          self.cluster3, self.cluster4,
                                          self.cluster5]

        with mock.patch.object(dbapi.Connection, 'list_cluster_nodegroups',
                               mock_nodegroup_list):
            periodic.MagnumPeriodicTasks(CONF).sync_cluster_status(None)

            self.assertEqual(cluster_status.CREATE_FAILED,
                             self.cluster1.status)
            self.assertEqual('Cluster %s not found' % self.cluster1.uuid,
                             self.cluster1.status_reason)
            self.assertEqual(cluster_status.UPDATE_FAILED,
                             self.cluster3.status)
            self.assertEqual('Cluster %s not found' % self.cluster3.uuid,
                             self.cluster3.status_reason)
            self.assertEqual(cluster_status.ROLLBACK_FAILED,
                             self.cluster5.status)
            self.assertEqual('Cluster %s not found' % self.cluster5.uuid,
                             self.cluster5.status_reason)
            mock_db_destroy.assert_has_calls([
                mock.call(self.cluster2.uuid),
                mock.call(self.cluster4.uuid)
            ])
            self.assertEqual(2, mock_db_destroy.call_count)
            notifications = fake_notifier.NOTIFICATIONS
            self.assertEqual(5, len(notifications))

    @mock.patch('oslo_service.loopingcall.FixedIntervalLoopingCall',
                new=fakes.FakeLoopingCall)
    @mock.patch('magnum.conductor.monitors.create_monitor')
    @mock.patch('magnum.objects.Cluster.list')
    @mock.patch('magnum.common.rpc.get_notifier')
    @mock.patch('magnum.common.context.make_admin_context')
    def test_sync_cluster_health_status(self, mock_make_admin_context,
                                        mock_get_notifier, mock_cluster_list,
                                        mock_create_monitor):
        """Test sync cluster health status"""
        mock_make_admin_context.return_value = self.context
        notifier = mock.MagicMock()
        mock_get_notifier.return_value = notifier
        mock_cluster_list.return_value = [self.cluster4]
        self.cluster4.status = cluster_status.CREATE_COMPLETE
        health = {'health_status': cluster_health_status.UNHEALTHY,
                  'health_status_reason': {'api': 'ok', 'node-0.Ready': False}}
        monitor = mock.MagicMock(spec=k8s_monitor.K8sMonitor, name='test',
                                 data=health)
        mock_create_monitor.return_value = monitor
        periodic.MagnumPeriodicTasks(CONF).sync_cluster_health_status(
            self.context)

        self.assertEqual(cluster_health_status.UNHEALTHY,
                         self.cluster4.health_status)
        self.assertEqual({'api': 'ok', 'node-0.Ready': 'False'},
                         self.cluster4.health_status_reason)
