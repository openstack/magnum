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

from heatclient import exc as heat_exc
import mock

from magnum.common import context
from magnum.common.rpc_service import CONF
from magnum.db.sqlalchemy import api as dbapi
from magnum import objects
from magnum.objects.fields import ClusterStatus as cluster_status
from magnum.service import periodic
from magnum.tests import base
from magnum.tests.unit.db import utils


class fake_stack(object):
    def __init__(self, **kw):
        for key, val in kw.items():
            setattr(self, key, val)


class PeriodicTestCase(base.TestCase):

    def setUp(self):
        super(PeriodicTestCase, self).setUp()

        ctx = context.make_admin_context()

        # Can be identical for all clusters.
        trust_attrs = {
            'trustee_username': '5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            'trustee_password': 'ain7einaebooVaig6d',
            'trust_id': '39d920ca-67c6-4047-b57a-01e9e16bb96f',
            }

        trust_attrs.update({'id': 1, 'stack_id': '11',
                           'status': cluster_status.CREATE_IN_PROGRESS})
        cluster1 = utils.get_test_cluster(**trust_attrs)
        trust_attrs.update({'id': 2, 'stack_id': '22',
                           'status': cluster_status.DELETE_IN_PROGRESS})
        cluster2 = utils.get_test_cluster(**trust_attrs)
        trust_attrs.update({'id': 3, 'stack_id': '33',
                           'status': cluster_status.UPDATE_IN_PROGRESS})
        cluster3 = utils.get_test_cluster(**trust_attrs)
        trust_attrs.update({'id': 4, 'stack_id': '44',
                           'status': cluster_status.CREATE_COMPLETE})
        cluster4 = utils.get_test_cluster(**trust_attrs)
        trust_attrs.update({'id': 5, 'stack_id': '55',
                           'status': cluster_status.ROLLBACK_IN_PROGRESS})
        cluster5 = utils.get_test_cluster(**trust_attrs)

        self.cluster1 = objects.Cluster(ctx, **cluster1)
        self.cluster2 = objects.Cluster(ctx, **cluster2)
        self.cluster3 = objects.Cluster(ctx, **cluster3)
        self.cluster4 = objects.Cluster(ctx, **cluster4)
        self.cluster5 = objects.Cluster(ctx, **cluster5)

    @mock.patch.object(objects.Cluster, 'list')
    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch.object(dbapi.Connection, 'destroy_cluster')
    @mock.patch.object(dbapi.Connection, 'update_cluster')
    def test_sync_cluster_status_changes(self, mock_db_update, mock_db_destroy,
                                         mock_oscc, mock_cluster_list):
        mock_heat_client = mock.MagicMock()
        stack1 = fake_stack(
            id='11', stack_status=cluster_status.CREATE_COMPLETE,
            stack_status_reason='fake_reason_11')
        stack3 = fake_stack(
            id='33', stack_status=cluster_status.UPDATE_COMPLETE,
            stack_status_reason='fake_reason_33')
        stack5 = fake_stack(
            id='55', stack_status=cluster_status.ROLLBACK_COMPLETE,
            stack_status_reason='fake_reason_55')
        mock_heat_client.stacks.list.return_value = [stack1, stack3, stack5]
        get_stacks = {'11': stack1, '33': stack3, '55': stack5}

        def stack_get_sideefect(arg):
            if arg == '22':
                raise heat_exc.HTTPNotFound
            return get_stacks[arg]

        mock_heat_client.stacks.get.side_effect = stack_get_sideefect
        mock_osc = mock_oscc.return_value
        mock_osc.heat.return_value = mock_heat_client
        mock_cluster_list.return_value = [self.cluster1, self.cluster2,
                                          self.cluster3, self.cluster5]

        mock_keystone_client = mock.MagicMock()
        mock_keystone_client.client.project_id = "fake_project"
        mock_osc.keystone.return_value = mock_keystone_client

        periodic.MagnumPeriodicTasks(CONF).sync_cluster_status(None)

        self.assertEqual(cluster_status.CREATE_COMPLETE, self.cluster1.status)
        self.assertEqual('fake_reason_11', self.cluster1.status_reason)
        mock_db_destroy.assert_called_once_with(self.cluster2.uuid)
        self.assertEqual(cluster_status.UPDATE_COMPLETE, self.cluster3.status)
        self.assertEqual('fake_reason_33', self.cluster3.status_reason)
        self.assertEqual(cluster_status.ROLLBACK_COMPLETE,
                         self.cluster5.status)
        self.assertEqual('fake_reason_55', self.cluster5.status_reason)

    @mock.patch.object(objects.Cluster, 'list')
    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_sync_auth_fail(self, mock_oscc, mock_cluster_list):
        """Tests handling for unexpected exceptions in _get_cluster_stacks()

        It does this by raising an a HTTPUnauthorized exception in Heat client.
        The affected stack thus missing from the stack list should not lead to
        cluster state changing in this case. Likewise, subsequent clusters
        should still change state, despite the affected cluster being skipped.
        """
        stack1 = fake_stack(id='11',
                            stack_status=cluster_status.CREATE_COMPLETE)

        mock_heat_client = mock.MagicMock()

        def stack_get_sideefect(arg):
            raise heat_exc.HTTPUnauthorized

        mock_heat_client.stacks.get.side_effect = stack_get_sideefect
        mock_heat_client.stacks.list.return_value = [stack1]
        mock_osc = mock_oscc.return_value
        mock_osc.heat.return_value = mock_heat_client
        mock_cluster_list.return_value = [self.cluster1]
        periodic.MagnumPeriodicTasks(CONF).sync_cluster_status(None)

        self.assertEqual(cluster_status.CREATE_IN_PROGRESS,
                         self.cluster1.status)

    @mock.patch.object(objects.Cluster, 'list')
    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_sync_cluster_status_not_changes(self, mock_oscc,
                                             mock_cluster_list):
        mock_heat_client = mock.MagicMock()
        stack1 = fake_stack(id='11',
                            stack_status=cluster_status.CREATE_IN_PROGRESS)
        stack2 = fake_stack(id='22',
                            stack_status=cluster_status.DELETE_IN_PROGRESS)
        stack3 = fake_stack(id='33',
                            stack_status=cluster_status.UPDATE_IN_PROGRESS)
        stack5 = fake_stack(id='55',
                            stack_status=cluster_status.ROLLBACK_IN_PROGRESS)
        get_stacks = {'11': stack1, '22': stack2, '33': stack3, '55': stack5}

        def stack_get_sideefect(arg):
            if arg == '22':
                raise heat_exc.HTTPNotFound
            return get_stacks[arg]

        mock_heat_client.stacks.get.side_effect = stack_get_sideefect
        mock_heat_client.stacks.list.return_value = [stack1, stack2, stack3,
                                                     stack5]
        mock_osc = mock_oscc.return_value
        mock_osc.heat.return_value = mock_heat_client
        mock_cluster_list.return_value = [self.cluster1, self.cluster2,
                                          self.cluster3, self.cluster5]
        periodic.MagnumPeriodicTasks(CONF).sync_cluster_status(None)

        self.assertEqual(cluster_status.CREATE_IN_PROGRESS,
                         self.cluster1.status)
        self.assertEqual(cluster_status.DELETE_IN_PROGRESS,
                         self.cluster2.status)
        self.assertEqual(cluster_status.UPDATE_IN_PROGRESS,
                         self.cluster3.status)
        self.assertEqual(cluster_status.ROLLBACK_IN_PROGRESS,
                         self.cluster5.status)

    @mock.patch.object(objects.Cluster, 'list')
    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch.object(dbapi.Connection, 'destroy_cluster')
    @mock.patch.object(dbapi.Connection, 'update_cluster')
    def test_sync_cluster_status_heat_not_found(self, mock_db_update,
                                                mock_db_destroy, mock_oscc,
                                                mock_cluster_list):
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.list.return_value = []
        mock_osc = mock_oscc.return_value
        mock_osc.heat.return_value = mock_heat_client
        mock_cluster_list.return_value = [self.cluster1, self.cluster2,
                                          self.cluster3]

        mock_keystone_client = mock.MagicMock()
        mock_keystone_client.client.project_id = "fake_project"
        mock_osc.keystone.return_value = mock_keystone_client

        periodic.MagnumPeriodicTasks(CONF).sync_cluster_status(None)

        self.assertEqual(cluster_status.CREATE_FAILED, self.cluster1.status)
        self.assertEqual('Stack with id 11 not found in Heat.',
                         self.cluster1.status_reason)
        mock_db_destroy.assert_called_once_with(self.cluster2.uuid)
        self.assertEqual(cluster_status.UPDATE_FAILED, self.cluster3.status)
        self.assertEqual('Stack with id 33 not found in Heat.',
                         self.cluster3.status_reason)

    @mock.patch('magnum.conductor.monitors.create_monitor')
    @mock.patch('magnum.objects.Cluster.list')
    @mock.patch('magnum.common.rpc.get_notifier')
    @mock.patch('magnum.common.context.make_admin_context')
    def test_send_cluster_metrics(self, mock_make_admin_context,
                                  mock_get_notifier, mock_cluster_list,
                                  mock_create_monitor):
        """Test if RPC notifier receives the expected message"""
        mock_make_admin_context.return_value = self.context
        notifier = mock.MagicMock()
        mock_get_notifier.return_value = notifier
        mock_cluster_list.return_value = [self.cluster1, self.cluster2,
                                          self.cluster3, self.cluster4]
        monitor = mock.MagicMock()
        monitor.get_metric_names.return_value = ['metric1', 'metric2']
        monitor.compute_metric_value.return_value = 30
        monitor.get_metric_unit.return_value = '%'
        mock_create_monitor.return_value = monitor

        periodic.MagnumPeriodicTasks(CONF)._send_cluster_metrics(self.context)

        expected_event_type = 'magnum.cluster.metrics.update'
        expected_metrics = [
            {
                'name': 'metric1',
                'value': 30,
                'unit': '%',
            },
            {
                'name': 'metric2',
                'value': 30,
                'unit': '%',
            },
        ]
        expected_msg = {
            'user_id': self.cluster4.user_id,
            'project_id': self.cluster4.project_id,
            'resource_id': self.cluster4.uuid,
            'metrics': expected_metrics
        }

        self.assertEqual(1, mock_create_monitor.call_count)
        notifier.info.assert_called_once_with(
            self.context, expected_event_type, expected_msg)

    @mock.patch('magnum.conductor.monitors.create_monitor')
    @mock.patch('magnum.objects.Cluster.list')
    @mock.patch('magnum.common.rpc.get_notifier')
    @mock.patch('magnum.common.context.make_admin_context')
    def test_send_cluster_metrics_compute_metric_raise(
            self, mock_make_admin_context, mock_get_notifier,
            mock_cluster_list, mock_create_monitor):
        mock_make_admin_context.return_value = self.context
        notifier = mock.MagicMock()
        mock_get_notifier.return_value = notifier
        mock_cluster_list.return_value = [self.cluster4]
        monitor = mock.MagicMock()
        monitor.get_metric_names.return_value = ['metric1', 'metric2']
        monitor.compute_metric_value.side_effect = Exception(
            "error on computing metric")
        mock_create_monitor.return_value = monitor

        periodic.MagnumPeriodicTasks(CONF)._send_cluster_metrics(self.context)

        expected_event_type = 'magnum.cluster.metrics.update'
        expected_msg = {
            'user_id': self.cluster4.user_id,
            'project_id': self.cluster4.project_id,
            'resource_id': self.cluster4.uuid,
            'metrics': []
        }
        self.assertEqual(1, mock_create_monitor.call_count)
        notifier.info.assert_called_once_with(
            self.context, expected_event_type, expected_msg)

    @mock.patch('magnum.conductor.monitors.create_monitor')
    @mock.patch('magnum.objects.Cluster.list')
    @mock.patch('magnum.common.rpc.get_notifier')
    @mock.patch('magnum.common.context.make_admin_context')
    def test_send_cluster_metrics_pull_data_raise(
            self, mock_make_admin_context, mock_get_notifier,
            mock_cluster_list, mock_create_monitor):
        mock_make_admin_context.return_value = self.context
        notifier = mock.MagicMock()
        mock_get_notifier.return_value = notifier
        mock_cluster_list.return_value = [self.cluster4]
        monitor = mock.MagicMock()
        monitor.pull_data.side_effect = Exception("error on pulling data")
        mock_create_monitor.return_value = monitor

        periodic.MagnumPeriodicTasks(CONF)._send_cluster_metrics(self.context)

        self.assertEqual(1, mock_create_monitor.call_count)
        self.assertEqual(0, notifier.info.call_count)

    @mock.patch('magnum.conductor.monitors.create_monitor')
    @mock.patch('magnum.objects.Cluster.list')
    @mock.patch('magnum.common.rpc.get_notifier')
    @mock.patch('magnum.common.context.make_admin_context')
    def test_send_cluster_metrics_monitor_none(
            self, mock_make_admin_context, mock_get_notifier,
            mock_cluster_list, mock_create_monitor):
        mock_make_admin_context.return_value = self.context
        notifier = mock.MagicMock()
        mock_get_notifier.return_value = notifier
        mock_cluster_list.return_value = [self.cluster4]
        mock_create_monitor.return_value = None

        periodic.MagnumPeriodicTasks(CONF)._send_cluster_metrics(self.context)

        self.assertEqual(1, mock_create_monitor.call_count)
        self.assertEqual(0, notifier.info.call_count)
