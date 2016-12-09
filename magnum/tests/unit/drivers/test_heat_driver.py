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

import mock
from mock import patch
from oslo_service import loopingcall
from pycadf import cadftaxonomy as taxonomy

import magnum.conf
from magnum.drivers.heat import driver as heat_driver
from magnum.drivers.k8s_fedora_atomic_v1 import driver as k8s_atomic_dr
from magnum import objects
from magnum.objects.fields import ClusterStatus as cluster_status
from magnum.tests import base
from magnum.tests import fake_notifier
from magnum.tests.unit.db import utils

CONF = magnum.conf.CONF


class TestHeatPoller(base.TestCase):

    @patch('magnum.conductor.utils.retrieve_cluster_template')
    @patch('oslo_config.cfg')
    @patch('magnum.common.clients.OpenStackClients')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def setup_poll_test(self, mock_driver, mock_openstack_client, cfg,
                        mock_retrieve_cluster_template):
        cfg.CONF.cluster_heat.max_attempts = 10

        cluster = mock.MagicMock()
        cluster_template_dict = utils.get_test_cluster_template(
            coe='kubernetes')
        mock_heat_stack = mock.MagicMock()
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client.heat.return_value = mock_heat_client
        cluster_template = objects.ClusterTemplate(self.context,
                                                   **cluster_template_dict)
        mock_retrieve_cluster_template.return_value = cluster_template
        mock_driver.return_value = k8s_atomic_dr.Driver()
        poller = heat_driver.HeatPoller(mock_openstack_client, cluster,
                                        k8s_atomic_dr.Driver())
        poller.get_version_info = mock.MagicMock()
        return (mock_heat_stack, cluster, poller)

    def test_poll_and_check_send_notification(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()
        mock_heat_stack.stack_status = cluster_status.CREATE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        mock_heat_stack.stack_status = cluster_status.CREATE_FAILED
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        mock_heat_stack.stack_status = cluster_status.DELETE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        mock_heat_stack.stack_status = cluster_status.DELETE_FAILED
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        mock_heat_stack.stack_status = cluster_status.UPDATE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        mock_heat_stack.stack_status = cluster_status.UPDATE_FAILED
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(6, poller.attempts)
        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(6, len(notifications))
        self.assertEqual(
            'magnum.cluster.create', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_SUCCESS, notifications[0].payload['outcome'])
        self.assertEqual(
            'magnum.cluster.create', notifications[1].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[1].payload['outcome'])
        self.assertEqual(
            'magnum.cluster.delete', notifications[2].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_SUCCESS, notifications[2].payload['outcome'])
        self.assertEqual(
            'magnum.cluster.delete', notifications[3].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[3].payload['outcome'])
        self.assertEqual(
            'magnum.cluster.update', notifications[4].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_SUCCESS, notifications[4].payload['outcome'])
        self.assertEqual(
            'magnum.cluster.update', notifications[5].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[5].payload['outcome'])

    def test_poll_no_save(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        cluster.status = cluster_status.CREATE_IN_PROGRESS
        mock_heat_stack.stack_status = cluster_status.CREATE_IN_PROGRESS
        poller.poll_and_check()

        self.assertEqual(0, cluster.save.call_count)
        self.assertEqual(1, poller.attempts)

    def test_poll_save(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        cluster.status = cluster_status.CREATE_IN_PROGRESS
        mock_heat_stack.stack_status = cluster_status.CREATE_FAILED
        mock_heat_stack.stack_status_reason = 'Create failed'
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(2, cluster.save.call_count)
        self.assertEqual(cluster_status.CREATE_FAILED, cluster.status)
        self.assertEqual('Create failed', cluster.status_reason)
        self.assertEqual(1, poller.attempts)

    def test_poll_done(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.DELETE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        mock_heat_stack.stack_status = cluster_status.CREATE_FAILED
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        self.assertEqual(2, poller.attempts)

    def test_poll_done_by_update(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.UPDATE_COMPLETE
        mock_heat_stack.parameters = {'number_of_minions': 2}
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(1, cluster.save.call_count)
        self.assertEqual(cluster_status.UPDATE_COMPLETE, cluster.status)
        self.assertEqual(2, cluster.node_count)
        self.assertEqual(1, poller.attempts)

    def test_poll_done_by_update_failed(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.UPDATE_FAILED
        mock_heat_stack.parameters = {'number_of_minions': 2}
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(2, cluster.save.call_count)
        self.assertEqual(cluster_status.UPDATE_FAILED, cluster.status)
        self.assertEqual(2, cluster.node_count)
        self.assertEqual(1, poller.attempts)

    def test_poll_done_by_rollback_complete(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.ROLLBACK_COMPLETE
        mock_heat_stack.parameters = {'number_of_minions': 1}
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(2, cluster.save.call_count)
        self.assertEqual(cluster_status.ROLLBACK_COMPLETE, cluster.status)
        self.assertEqual(1, cluster.node_count)
        self.assertEqual(1, poller.attempts)

    def test_poll_done_by_rollback_failed(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.ROLLBACK_FAILED
        mock_heat_stack.parameters = {'number_of_minions': 1}
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(2, cluster.save.call_count)
        self.assertEqual(cluster_status.ROLLBACK_FAILED, cluster.status)
        self.assertEqual(1, cluster.node_count)
        self.assertEqual(1, poller.attempts)

    def test_poll_destroy(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.DELETE_FAILED
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        # Destroy method is not called when stack delete failed
        self.assertEqual(0, cluster.destroy.call_count)

        mock_heat_stack.stack_status = cluster_status.DELETE_IN_PROGRESS
        poller.poll_and_check()
        self.assertEqual(0, cluster.destroy.call_count)
        self.assertEqual(cluster_status.DELETE_IN_PROGRESS, cluster.status)

        mock_heat_stack.stack_status = cluster_status.DELETE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        # The cluster status should still be DELETE_IN_PROGRESS, because
        # the destroy() method may be failed. If success, this cluster record
        # will delete directly, change status is meaningless.
        self.assertEqual(cluster_status.DELETE_IN_PROGRESS, cluster.status)
        self.assertEqual(1, cluster.destroy.call_count)

    def test_poll_delete_in_progress_timeout_set(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.DELETE_IN_PROGRESS
        mock_heat_stack.timeout_mins = 60
        # timeout only affects stack creation so expecting this
        # to process normally
        poller.poll_and_check()

    def test_poll_delete_in_progress_max_attempts_reached(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.DELETE_IN_PROGRESS
        poller.attempts = CONF.cluster_heat.max_attempts
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

    def test_poll_create_in_prog_max_att_reached_no_timeout(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.CREATE_IN_PROGRESS
        poller.attempts = CONF.cluster_heat.max_attempts
        mock_heat_stack.timeout_mins = None
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

    def test_poll_create_in_prog_max_att_reached_timeout_set(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.CREATE_IN_PROGRESS
        poller.attempts = CONF.cluster_heat.max_attempts
        mock_heat_stack.timeout_mins = 60
        # since the timeout is set the max attempts gets ignored since
        # the timeout will eventually stop the poller either when
        # the stack gets created or the timeout gets reached
        poller.poll_and_check()

    def test_poll_create_in_prog_max_att_reached_timed_out(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.CREATE_FAILED
        poller.attempts = CONF.cluster_heat.max_attempts
        mock_heat_stack.timeout_mins = 60
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

    def test_poll_create_in_prog_max_att_not_reached_no_timeout(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.CREATE_IN_PROGRESS
        mock_heat_stack.timeout.mins = None
        poller.poll_and_check()

    def test_poll_create_in_prog_max_att_not_reached_timeout_set(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.CREATE_IN_PROGRESS
        mock_heat_stack.timeout_mins = 60
        poller.poll_and_check()

    def test_poll_create_in_prog_max_att_not_reached_timed_out(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.CREATE_FAILED
        mock_heat_stack.timeout_mins = 60
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

    def test_poll_node_count(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.parameters = {'number_of_minions': 1}
        mock_heat_stack.stack_status = cluster_status.CREATE_IN_PROGRESS
        poller.poll_and_check()

        self.assertEqual(1, cluster.node_count)

    def test_poll_node_count_by_update(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.parameters = {'number_of_minions': 2}
        mock_heat_stack.stack_status = cluster_status.UPDATE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(2, cluster.node_count)

    @patch('magnum.drivers.heat.driver.trust_manager')
    @patch('magnum.drivers.heat.driver.cert_manager')
    def test_delete_complete(self, cert_manager, trust_manager):
        mock_heat_stack, cluster, poller = self.setup_poll_test()
        poller._delete_complete()
        self.assertEqual(1, cluster.destroy.call_count)
        self.assertEqual(
            1, cert_manager.delete_certificates_from_cluster.call_count)
        self.assertEqual(1,
                         trust_manager.delete_trustee_and_trust.call_count)

    def test_create_or_complete(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()
        mock_heat_stack.stack_status = cluster_status.CREATE_COMPLETE
        mock_heat_stack.stack_status_reason = 'stack complete'
        poller._sync_cluster_and_template_status(mock_heat_stack)
        self.assertEqual('stack complete', cluster.status_reason)
        self.assertEqual(cluster_status.CREATE_COMPLETE, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_sync_cluster_status(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()
        mock_heat_stack.stack_status = cluster_status.CREATE_IN_PROGRESS
        mock_heat_stack.stack_status_reason = 'stack incomplete'
        poller._sync_cluster_status(mock_heat_stack)
        self.assertEqual('stack incomplete', cluster.status_reason)
        self.assertEqual(cluster_status.CREATE_IN_PROGRESS, cluster.status)

    @patch('magnum.drivers.heat.driver.LOG')
    def test_cluster_failed(self, logger):
        mock_heat_stack, cluster, poller = self.setup_poll_test()
        poller._sync_cluster_and_template_status(mock_heat_stack)
        poller._cluster_failed(mock_heat_stack)
        self.assertEqual(1, logger.error.call_count)
