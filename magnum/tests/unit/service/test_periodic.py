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
from magnum.common import exception
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


class fake_stack(object):
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

        # Can be identical for all clusters.
        trust_attrs = {
            'trustee_username': '5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            'trustee_password': 'ain7einaebooVaig6d',
            'trust_id': '39d920ca-67c6-4047-b57a-01e9e16bb96f',
            }

        uuid = uuidutils.generate_uuid()
        trust_attrs.update({'id': 1, 'stack_id': '11', 'uuid': uuid,
                            'status': cluster_status.CREATE_IN_PROGRESS,
                            'status_reason': 'no change',
                            'keypair': 'keipair1', 'health_status': None})
        cluster1 = utils.get_test_cluster(**trust_attrs)
        ngs1 = utils.get_nodegroups_for_cluster()
        uuid = uuidutils.generate_uuid()
        trust_attrs.update({'id': 2, 'stack_id': '22', 'uuid': uuid,
                            'status': cluster_status.DELETE_IN_PROGRESS,
                            'status_reason': 'no change',
                            'keypair': 'keipair1', 'health_status': None})
        cluster2 = utils.get_test_cluster(**trust_attrs)
        ngs2 = utils.get_nodegroups_for_cluster()
        uuid = uuidutils.generate_uuid()
        trust_attrs.update({'id': 3, 'stack_id': '33', 'uuid': uuid,
                            'status': cluster_status.UPDATE_IN_PROGRESS,
                            'status_reason': 'no change',
                            'keypair': 'keipair1', 'health_status': None})
        cluster3 = utils.get_test_cluster(**trust_attrs)
        ngs3 = utils.get_nodegroups_for_cluster()
        uuid = uuidutils.generate_uuid()
        trust_attrs.update({'id': 4, 'stack_id': '44', 'uuid': uuid,
                            'status': cluster_status.DELETE_IN_PROGRESS,
                            'status_reason': 'no change',
                            'keypair': 'keipair1', 'health_status': None})
        cluster4 = utils.get_test_cluster(**trust_attrs)
        ngs4 = utils.get_nodegroups_for_cluster()
        uuid = uuidutils.generate_uuid()
        trust_attrs.update({'id': 5, 'stack_id': '55', 'uuid': uuid,
                            'status': cluster_status.ROLLBACK_IN_PROGRESS,
                            'status_reason': 'no change',
                            'keypair': 'keipair1', 'health_status': None})
        cluster5 = utils.get_test_cluster(**trust_attrs)
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

        # these tests are based on the basic behavior of our standard
        # Heat-based drivers, but drivers based on other orchestration
        # methods should generally behave in a similar fashion as far
        # as the actual calls go. It is up to the driver implementor
        # to ensure their implementation of update_cluster_status behaves
        # as expected regardless of how the periodic updater task works
        self.mock_heat_client = mock.MagicMock()
        self.stack1 = fake_stack(
            id='11', stack_status=cluster_status.CREATE_COMPLETE,
            stack_status_reason='fake_reason_11')
        self.stack2 = fake_stack(
            id='22', stack_status=cluster_status.DELETE_IN_PROGRESS,
            stack_status_reason='fake_reason_11')
        self.stack3 = fake_stack(
            id='33', stack_status=cluster_status.UPDATE_COMPLETE,
            stack_status_reason='fake_reason_33')
        self.stack5 = fake_stack(
            id='55', stack_status=cluster_status.ROLLBACK_COMPLETE,
            stack_status_reason='fake_reason_55')
        self.mock_heat_client.stacks.list.return_value = [
            self.stack1, self.stack2, self.stack3, self.stack5]

        self.get_stacks = {
            '11': self.stack1,
            '22': self.stack2,
            '33': self.stack3,
            '55': self.stack5
        }

        self.mock_driver = mock.MagicMock(spec=driver.Driver)

        def _mock_update_status(context, cluster):
            try:
                stack = self.get_stacks[cluster.stack_id]
            except KeyError:
                cluster.status_reason = "Stack %s not found" % cluster.stack_id
                if cluster.status == "DELETE_IN_PROGRESS":
                    cluster.status = cluster_status.DELETE_COMPLETE
                else:
                    cluster.status = cluster.status.replace("IN_PROGRESS",
                                                            "FAILED")
                    cluster.status = cluster.status.replace("COMPLETE",
                                                            "FAILED")
            else:
                if cluster.status != stack.stack_status:
                    cluster.status = stack.stack_status
                    cluster.status_reason = stack.stack_status_reason

        self.mock_driver.update_cluster_status.side_effect = (
            _mock_update_status)

    @mock.patch('magnum.drivers.common.driver.Driver.get_driver_for_cluster')
    def test_update_status_non_trusts_error(self, mock_get_driver):
        mock_get_driver.return_value = self.mock_driver
        trust_ex = ("Unknown Keystone error")
        self.mock_driver.update_cluster_status.side_effect = \
            exception.AuthorizationFailure(client='keystone', message=trust_ex)
        self.assertRaises(
            exception.AuthorizationFailure,
            periodic.ClusterUpdateJob(
                self.context, self.cluster1).update_status
        )
        self.assertEqual(1, self.mock_driver.update_cluster_status.call_count)

    @mock.patch('magnum.drivers.common.driver.Driver.get_driver_for_cluster')
    def test_update_status_trusts_not_found(self, mock_get_driver):
        mock_get_driver.return_value = self.mock_driver
        trust_ex = ("Could not find trust: %s" % self.cluster1.trust_id)
        self.mock_driver.update_cluster_status.side_effect = \
            exception.AuthorizationFailure(client='keystone', message=trust_ex)
        self.assertRaises(
            exception.AuthorizationFailure,
            periodic.ClusterUpdateJob(
                self.context, self.cluster1).update_status
        )
        self.assertEqual(2, self.mock_driver.update_cluster_status.call_count)

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

        self.stack1.stack_status = self.cluster1.status
        self.stack2.stack_status = self.cluster2.status
        self.stack3.stack_status = self.cluster3.status
        self.stack5.stack_status = self.cluster5.status
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
    def test_sync_cluster_status_heat_not_found(self, mock_ng_destroy,
                                                mock_db_destroy,
                                                mock_cluster_list,
                                                mock_get_driver):
        self.get_stacks.clear()
        mock_get_driver.return_value = self.mock_driver
        mock_cluster_list.return_value = [self.cluster1, self.cluster2,
                                          self.cluster3, self.cluster4,
                                          self.cluster5]

        with mock.patch.object(dbapi.Connection, 'list_cluster_nodegroups',
                               mock_nodegroup_list):
            periodic.MagnumPeriodicTasks(CONF).sync_cluster_status(None)

            self.assertEqual(cluster_status.CREATE_FAILED,
                             self.cluster1.status)
            self.assertEqual('Stack 11 not found', self.cluster1.status_reason)
            self.assertEqual(cluster_status.UPDATE_FAILED,
                             self.cluster3.status)
            self.assertEqual('Stack 33 not found', self.cluster3.status_reason)
            self.assertEqual(cluster_status.ROLLBACK_FAILED,
                             self.cluster5.status)
            self.assertEqual('Stack 55 not found', self.cluster5.status_reason)
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
