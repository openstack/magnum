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
from unittest.mock import patch

from heatclient import exc as heatexc
from oslo_utils import uuidutils

import magnum.conf
from magnum.drivers.heat import driver as heat_driver
from magnum.drivers.k8s_fedora_coreos_v1 import driver as k8s_fcos_dr
from magnum import objects
from magnum.objects.fields import ClusterStatus as cluster_status
from magnum.tests import base
from magnum.tests.unit.db import utils

CONF = magnum.conf.CONF


class TestHeatPoller(base.TestCase):

    def setUp(self):
        super(TestHeatPoller, self).setUp()
        self.mock_stacks = dict()
        self.def_ngs = list()

    def _create_nodegroup(self, cluster, uuid, stack_id, name=None, role=None,
                          is_default=False, stack_status=None,
                          status_reason=None, stack_params=None,
                          stack_missing=False):
        """Create a new nodegroup

        Util that creates a new non-default ng, adds it to the cluster
        and creates the corresponding mock stack.
        """
        role = 'worker' if role is None else role
        ng = mock.MagicMock(uuid=uuid, role=role, is_default=is_default,
                            stack_id=stack_id)
        if name is not None:
            type(ng).name = name

        cluster.nodegroups.append(ng)

        if stack_status is None:
            stack_status = cluster_status.CREATE_COMPLETE

        if status_reason is None:
            status_reason = 'stack created'

        stack_params = dict() if stack_params is None else stack_params

        stack = mock.MagicMock(stack_status=stack_status,
                               stack_status_reason=status_reason,
                               parameters=stack_params)
        # In order to simulate a stack not found from osc we don't add the
        # stack in the dict.
        if not stack_missing:
            self.mock_stacks.update({stack_id: stack})
        else:
            # In case the stack is missing we need
            # to set the status to the ng, so that
            # _sync_missing_heat_stack knows which
            # was the previous state.
            ng.status = stack_status

        return ng

    @patch('magnum.conductor.utils.retrieve_cluster_template')
    @patch('oslo_config.cfg')
    @patch('magnum.common.clients.OpenStackClients')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def setup_poll_test(self, mock_driver, mock_openstack_client, cfg,
                        mock_retrieve_cluster_template,
                        default_stack_status=None, status_reason=None,
                        stack_params=None, stack_missing=False):
        cfg.CONF.cluster_heat.max_attempts = 10

        if default_stack_status is None:
            default_stack_status = cluster_status.CREATE_COMPLETE

        cluster = mock.MagicMock(nodegroups=list(),
                                 uuid=uuidutils.generate_uuid())

        def_worker = self._create_nodegroup(cluster, 'worker_ng', 'stack1',
                                            name='worker_ng', role='worker',
                                            is_default=True,
                                            stack_status=default_stack_status,
                                            status_reason=status_reason,
                                            stack_params=stack_params,
                                            stack_missing=stack_missing)
        def_master = self._create_nodegroup(cluster, 'master_ng', 'stack1',
                                            name='master_ng', role='master',
                                            is_default=True,
                                            stack_status=default_stack_status,
                                            status_reason=status_reason,
                                            stack_params=stack_params,
                                            stack_missing=stack_missing)

        cluster.default_ng_worker = def_worker
        cluster.default_ng_master = def_master

        self.def_ngs = [def_worker, def_master]

        def get_ng_stack(stack_id, resolve_outputs=False):
            try:
                return self.mock_stacks[stack_id]
            except KeyError:
                # In this case we intentionally didn't add the stack
                # to the mock_stacks dict to simulte a not found error.
                # For this reason raise heat NotFound exception.
                raise heatexc.NotFound("stack not found")

        cluster_template_dict = utils.get_test_cluster_template(
            coe='kubernetes')
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get = get_ng_stack
        mock_openstack_client.heat.return_value = mock_heat_client
        cluster_template = objects.ClusterTemplate(self.context,
                                                   **cluster_template_dict)
        mock_retrieve_cluster_template.return_value = cluster_template
        mock_driver.return_value = k8s_fcos_dr.Driver()
        poller = heat_driver.HeatPoller(mock_openstack_client,
                                        mock.MagicMock(), cluster,
                                        k8s_fcos_dr.Driver())
        poller.get_version_info = mock.MagicMock()
        return (cluster, poller)

    def test_poll_and_check_creating(self):
        cluster, poller = self.setup_poll_test(
            default_stack_status=cluster_status.CREATE_IN_PROGRESS)

        cluster.status = cluster_status.CREATE_IN_PROGRESS
        poller.poll_and_check()

        for ng in cluster.nodegroups:
            self.assertEqual(cluster_status.CREATE_IN_PROGRESS, ng.status)

        self.assertEqual(cluster_status.CREATE_IN_PROGRESS, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_poll_and_check_create_complete(self):
        cluster, poller = self.setup_poll_test()

        cluster.status = cluster_status.CREATE_IN_PROGRESS
        poller.poll_and_check()

        for ng in cluster.nodegroups:
            self.assertEqual(cluster_status.CREATE_COMPLETE, ng.status)
            self.assertEqual('stack created', ng.status_reason)
            self.assertEqual(1, ng.save.call_count)

        self.assertEqual(cluster_status.CREATE_COMPLETE, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_poll_and_check_create_failed(self):
        cluster, poller = self.setup_poll_test(
            default_stack_status=cluster_status.CREATE_FAILED)

        cluster.status = cluster_status.CREATE_IN_PROGRESS
        self.assertIsNone(poller.poll_and_check())

        for ng in cluster.nodegroups:
            self.assertEqual(cluster_status.CREATE_FAILED, ng.status)
            # Two calls to save since the stack ouptputs are synced too.
            self.assertEqual(2, ng.save.call_count)

        self.assertEqual(cluster_status.CREATE_FAILED, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_poll_and_check_updating(self):
        cluster, poller = self.setup_poll_test(
            default_stack_status=cluster_status.UPDATE_IN_PROGRESS)

        cluster.status = cluster_status.UPDATE_IN_PROGRESS
        poller.poll_and_check()

        for ng in cluster.nodegroups:
            self.assertEqual(cluster_status.UPDATE_IN_PROGRESS, ng.status)
            self.assertEqual(1, ng.save.call_count)

        self.assertEqual(cluster_status.UPDATE_IN_PROGRESS, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_poll_and_check_update_complete(self):
        stack_params = {
            'number_of_minions': 2,
            'number_of_masters': 1
        }
        cluster, poller = self.setup_poll_test(
            default_stack_status=cluster_status.UPDATE_COMPLETE,
            stack_params=stack_params)

        cluster.status = cluster_status.UPDATE_IN_PROGRESS
        self.assertIsNone(poller.poll_and_check())

        for ng in cluster.nodegroups:
            self.assertEqual(cluster_status.UPDATE_COMPLETE, ng.status)

        self.assertEqual(2, cluster.default_ng_worker.save.call_count)
        self.assertEqual(2, cluster.default_ng_master.save.call_count)
        self.assertEqual(2, cluster.default_ng_worker.node_count)
        self.assertEqual(1, cluster.default_ng_master.node_count)

        self.assertEqual(cluster_status.UPDATE_COMPLETE, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_poll_and_check_update_failed(self):
        stack_params = {
            'number_of_minions': 2,
            'number_of_masters': 1
        }
        cluster, poller = self.setup_poll_test(
            default_stack_status=cluster_status.UPDATE_FAILED,
            stack_params=stack_params)

        cluster.status = cluster_status.UPDATE_IN_PROGRESS
        poller.poll_and_check()

        for ng in cluster.nodegroups:
            self.assertEqual(cluster_status.UPDATE_FAILED, ng.status)
            # We have several calls to save because the stack outputs are
            # stored too.
            self.assertEqual(3, ng.save.call_count)

        self.assertEqual(2, cluster.default_ng_worker.node_count)
        self.assertEqual(1, cluster.default_ng_master.node_count)

        self.assertEqual(cluster_status.UPDATE_FAILED, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_poll_and_check_deleting(self):
        cluster, poller = self.setup_poll_test(
            default_stack_status=cluster_status.DELETE_IN_PROGRESS)

        cluster.status = cluster_status.DELETE_IN_PROGRESS
        poller.poll_and_check()

        for ng in cluster.nodegroups:
            self.assertEqual(cluster_status.DELETE_IN_PROGRESS, ng.status)
            # We have two calls to save because the stack outputs are
            # stored too.
            self.assertEqual(1, ng.save.call_count)

        self.assertEqual(cluster_status.DELETE_IN_PROGRESS, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_poll_and_check_deleted(self):
        cluster, poller = self.setup_poll_test(
            default_stack_status=cluster_status.DELETE_COMPLETE)

        cluster.status = cluster_status.DELETE_IN_PROGRESS
        self.assertIsNone(poller.poll_and_check())

        self.assertEqual(cluster_status.DELETE_COMPLETE,
                         cluster.default_ng_worker.status)
        self.assertEqual(1, cluster.default_ng_worker.save.call_count)
        self.assertEqual(0, cluster.default_ng_worker.destroy.call_count)

        self.assertEqual(cluster_status.DELETE_COMPLETE,
                         cluster.default_ng_master.status)
        self.assertEqual(1, cluster.default_ng_master.save.call_count)
        self.assertEqual(0, cluster.default_ng_master.destroy.call_count)

        self.assertEqual(cluster_status.DELETE_COMPLETE, cluster.status)
        self.assertEqual(1, cluster.save.call_count)
        self.assertEqual(0, cluster.destroy.call_count)

    def test_poll_and_check_delete_failed(self):
        cluster, poller = self.setup_poll_test(
            default_stack_status=cluster_status.DELETE_FAILED)

        cluster.status = cluster_status.DELETE_IN_PROGRESS
        poller.poll_and_check()

        self.assertEqual(cluster_status.DELETE_FAILED,
                         cluster.default_ng_worker.status)
        # We have two calls to save because the stack outputs are
        # stored too.
        self.assertEqual(2, cluster.default_ng_worker.save.call_count)
        self.assertEqual(0, cluster.default_ng_worker.destroy.call_count)

        self.assertEqual(cluster_status.DELETE_FAILED,
                         cluster.default_ng_master.status)
        # We have two calls to save because the stack outputs are
        # stored too.
        self.assertEqual(2, cluster.default_ng_master.save.call_count)
        self.assertEqual(0, cluster.default_ng_master.destroy.call_count)

        self.assertEqual(cluster_status.DELETE_FAILED, cluster.status)
        self.assertEqual(1, cluster.save.call_count)
        self.assertEqual(0, cluster.destroy.call_count)

    def test_poll_done_rollback_complete(self):
        stack_params = {
            'number_of_minions': 1,
            'number_of_masters': 1
        }
        cluster, poller = self.setup_poll_test(
            default_stack_status=cluster_status.ROLLBACK_COMPLETE,
            stack_params=stack_params)

        self.assertIsNone(poller.poll_and_check())

        self.assertEqual(1, cluster.save.call_count)
        self.assertEqual(cluster_status.ROLLBACK_COMPLETE, cluster.status)
        self.assertEqual(1, cluster.default_ng_worker.node_count)
        self.assertEqual(1, cluster.default_ng_master.node_count)

    def test_poll_done_rollback_failed(self):
        stack_params = {
            'number_of_minions': 1,
            'number_of_masters': 1
        }
        cluster, poller = self.setup_poll_test(
            default_stack_status=cluster_status.ROLLBACK_FAILED,
            stack_params=stack_params)

        self.assertIsNone(poller.poll_and_check())

        self.assertEqual(1, cluster.save.call_count)
        self.assertEqual(cluster_status.ROLLBACK_FAILED, cluster.status)
        self.assertEqual(1, cluster.default_ng_worker.node_count)
        self.assertEqual(1, cluster.default_ng_master.node_count)

    def test_poll_and_check_new_ng_creating(self):
        cluster, poller = self.setup_poll_test()

        ng = self._create_nodegroup(
            cluster, 'ng1', 'stack2',
            stack_status=cluster_status.CREATE_IN_PROGRESS)

        cluster.status = cluster_status.UPDATE_IN_PROGRESS
        poller.poll_and_check()

        for def_ng in self.def_ngs:
            self.assertEqual(cluster_status.CREATE_COMPLETE, def_ng.status)
            self.assertEqual(1, def_ng.save.call_count)

        self.assertEqual(cluster_status.CREATE_IN_PROGRESS, ng.status)
        self.assertEqual(1, ng.save.call_count)
        self.assertEqual(cluster_status.UPDATE_IN_PROGRESS, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_poll_and_check_new_ng_created(self):
        cluster, poller = self.setup_poll_test()

        ng = self._create_nodegroup(cluster, 'ng1', 'stack2')

        cluster.status = cluster_status.UPDATE_IN_PROGRESS
        poller.poll_and_check()

        for def_ng in self.def_ngs:
            self.assertEqual(cluster_status.CREATE_COMPLETE, def_ng.status)
            self.assertEqual(1, def_ng.save.call_count)

        self.assertEqual(cluster_status.CREATE_COMPLETE, ng.status)
        self.assertEqual(1, ng.save.call_count)

        self.assertEqual(cluster_status.UPDATE_COMPLETE, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_poll_and_check_new_ng_create_failed(self):
        cluster, poller = self.setup_poll_test()

        ng = self._create_nodegroup(
            cluster, 'ng1', 'stack2',
            stack_status=cluster_status.CREATE_FAILED,
            status_reason='stack failed')

        cluster.status = cluster_status.UPDATE_IN_PROGRESS
        poller.poll_and_check()

        for def_ng in self.def_ngs:
            self.assertEqual(cluster_status.CREATE_COMPLETE, def_ng.status)
            self.assertEqual('stack created', def_ng.status_reason)
            self.assertEqual(1, def_ng.save.call_count)

        self.assertEqual(cluster_status.CREATE_FAILED, ng.status)
        self.assertEqual('stack failed', ng.status_reason)
        self.assertEqual(2, ng.save.call_count)

        self.assertEqual(cluster_status.UPDATE_FAILED, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_poll_and_check_new_ng_updated(self):
        cluster, poller = self.setup_poll_test()

        stack_params = {'number_of_minions': 3}
        ng = self._create_nodegroup(
            cluster, 'ng1', 'stack2',
            stack_status=cluster_status.UPDATE_COMPLETE,
            stack_params=stack_params)

        cluster.status = cluster_status.UPDATE_IN_PROGRESS
        poller.poll_and_check()

        for def_ng in self.def_ngs:
            self.assertEqual(cluster_status.CREATE_COMPLETE, def_ng.status)
            self.assertEqual(1, def_ng.save.call_count)

        self.assertEqual(cluster_status.UPDATE_COMPLETE, ng.status)
        self.assertEqual(3, ng.node_count)
        self.assertEqual(2, ng.save.call_count)

        self.assertEqual(cluster_status.UPDATE_COMPLETE, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_poll_and_check_new_ng_update_failed(self):
        cluster, poller = self.setup_poll_test()

        stack_params = {'number_of_minions': 3}
        ng = self._create_nodegroup(
            cluster, 'ng1', 'stack2',
            stack_status=cluster_status.UPDATE_FAILED,
            stack_params=stack_params)

        cluster.status = cluster_status.UPDATE_IN_PROGRESS
        poller.poll_and_check()

        for def_ng in self.def_ngs:
            self.assertEqual(cluster_status.CREATE_COMPLETE, def_ng.status)
            self.assertEqual(1, def_ng.save.call_count)

        self.assertEqual(cluster_status.UPDATE_FAILED, ng.status)
        self.assertEqual(3, ng.node_count)
        self.assertEqual(3, ng.save.call_count)

        self.assertEqual(cluster_status.UPDATE_FAILED, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_poll_and_check_new_ng_deleting(self):
        cluster, poller = self.setup_poll_test()

        ng = self._create_nodegroup(
            cluster, 'ng1', 'stack2',
            stack_status=cluster_status.DELETE_IN_PROGRESS)

        cluster.status = cluster_status.UPDATE_IN_PROGRESS
        poller.poll_and_check()

        for def_ng in self.def_ngs:
            self.assertEqual(cluster_status.CREATE_COMPLETE, def_ng.status)
            self.assertEqual(1, def_ng.save.call_count)

        self.assertEqual(cluster_status.DELETE_IN_PROGRESS, ng.status)
        self.assertEqual(1, ng.save.call_count)

        self.assertEqual(cluster_status.UPDATE_IN_PROGRESS, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_poll_and_check_new_ng_deleted(self):
        cluster, poller = self.setup_poll_test()

        ng = self._create_nodegroup(
            cluster, 'ng1', 'stack2',
            stack_status=cluster_status.DELETE_COMPLETE)

        cluster.status = cluster_status.UPDATE_IN_PROGRESS
        poller.poll_and_check()

        for def_ng in self.def_ngs:
            self.assertEqual(cluster_status.CREATE_COMPLETE, def_ng.status)
            self.assertEqual(1, def_ng.save.call_count)

        self.assertEqual(1, ng.destroy.call_count)

        self.assertEqual(cluster_status.UPDATE_COMPLETE, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_poll_and_check_new_ng_delete_failed(self):
        cluster, poller = self.setup_poll_test()

        ng = self._create_nodegroup(
            cluster, 'ng1', 'stack2',
            stack_status=cluster_status.DELETE_FAILED)

        cluster.status = cluster_status.UPDATE_IN_PROGRESS
        poller.poll_and_check()

        for def_ng in self.def_ngs:
            self.assertEqual(cluster_status.CREATE_COMPLETE, def_ng.status)
            self.assertEqual(1, def_ng.save.call_count)

        self.assertEqual(cluster_status.DELETE_FAILED, ng.status)
        self.assertEqual(2, ng.save.call_count)
        self.assertEqual(0, ng.destroy.call_count)

        self.assertEqual(cluster_status.UPDATE_FAILED, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_poll_and_check_new_ng_rollback_complete(self):
        cluster, poller = self.setup_poll_test()

        stack_params = {
            'number_of_minions': 2,
            'number_of_masters': 0
        }
        ng = self._create_nodegroup(
            cluster, 'ng1', 'stack2',
            stack_status=cluster_status.ROLLBACK_COMPLETE,
            stack_params=stack_params)

        cluster.status = cluster_status.UPDATE_IN_PROGRESS
        poller.poll_and_check()

        for def_ng in self.def_ngs:
            self.assertEqual(cluster_status.CREATE_COMPLETE, def_ng.status)
            self.assertEqual(1, def_ng.save.call_count)

        self.assertEqual(cluster_status.ROLLBACK_COMPLETE, ng.status)
        self.assertEqual(2, ng.node_count)
        self.assertEqual(3, ng.save.call_count)
        self.assertEqual(0, ng.destroy.call_count)

        self.assertEqual(cluster_status.UPDATE_COMPLETE, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_poll_and_check_new_ng_rollback_failed(self):
        cluster, poller = self.setup_poll_test()

        stack_params = {
            'number_of_minions': 2,
            'number_of_masters': 0
        }
        ng = self._create_nodegroup(
            cluster, 'ng1', 'stack2',
            stack_status=cluster_status.ROLLBACK_FAILED,
            stack_params=stack_params)

        cluster.status = cluster_status.UPDATE_IN_PROGRESS
        poller.poll_and_check()

        for def_ng in self.def_ngs:
            self.assertEqual(cluster_status.CREATE_COMPLETE, def_ng.status)
            self.assertEqual(1, def_ng.save.call_count)

        self.assertEqual(cluster_status.ROLLBACK_FAILED, ng.status)
        self.assertEqual(2, ng.node_count)
        self.assertEqual(3, ng.save.call_count)
        self.assertEqual(0, ng.destroy.call_count)

        self.assertEqual(cluster_status.UPDATE_FAILED, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_poll_and_check_multiple_new_ngs(self):
        cluster, poller = self.setup_poll_test()

        ng1 = self._create_nodegroup(
            cluster, 'ng1', 'stack2',
            stack_status=cluster_status.CREATE_COMPLETE)
        ng2 = self._create_nodegroup(
            cluster, 'ng2', 'stack3',
            stack_status=cluster_status.UPDATE_IN_PROGRESS)

        cluster.status = cluster_status.UPDATE_IN_PROGRESS
        poller.poll_and_check()

        for def_ng in self.def_ngs:
            self.assertEqual(cluster_status.CREATE_COMPLETE, def_ng.status)
            self.assertEqual(1, def_ng.save.call_count)

        self.assertEqual(cluster_status.CREATE_COMPLETE, ng1.status)
        self.assertEqual(1, ng1.save.call_count)
        self.assertEqual(cluster_status.UPDATE_IN_PROGRESS, ng2.status)
        self.assertEqual(1, ng2.save.call_count)

        self.assertEqual(cluster_status.UPDATE_IN_PROGRESS, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_poll_and_check_multiple_ngs_failed_and_updating(self):
        cluster, poller = self.setup_poll_test()

        ng1 = self._create_nodegroup(
            cluster, 'ng1', 'stack2',
            stack_status=cluster_status.CREATE_FAILED)
        ng2 = self._create_nodegroup(
            cluster, 'ng2', 'stack3',
            stack_status=cluster_status.UPDATE_IN_PROGRESS)

        cluster.status = cluster_status.UPDATE_IN_PROGRESS
        poller.poll_and_check()

        for def_ng in self.def_ngs:
            self.assertEqual(cluster_status.CREATE_COMPLETE, def_ng.status)
            self.assertEqual(1, def_ng.save.call_count)

        self.assertEqual(cluster_status.CREATE_FAILED, ng1.status)
        self.assertEqual(2, ng1.save.call_count)
        self.assertEqual(cluster_status.UPDATE_IN_PROGRESS, ng2.status)
        self.assertEqual(1, ng2.save.call_count)

        self.assertEqual(cluster_status.UPDATE_IN_PROGRESS, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    @patch('magnum.drivers.heat.driver.trust_manager')
    @patch('magnum.drivers.heat.driver.cert_manager')
    def test_delete_complete(self, cert_manager, trust_manager):
        cluster, poller = self.setup_poll_test()
        poller._delete_complete()
        self.assertEqual(
            1, cert_manager.delete_certificates_from_cluster.call_count)
        self.assertEqual(1, trust_manager.delete_trustee_and_trust.call_count)

    @patch('magnum.drivers.heat.driver.LOG')
    def test_nodegroup_failed(self, logger):
        cluster, poller = self.setup_poll_test(
            default_stack_status=cluster_status.CREATE_FAILED)

        self._create_nodegroup(cluster, 'ng1', 'stack2',
                               stack_status=cluster_status.CREATE_FAILED)
        poller.poll_and_check()
        # Verify that we have one log for each failed nodegroup
        self.assertEqual(3, logger.error.call_count)

    def test_stack_not_found_creating(self):
        cluster, poller = self.setup_poll_test(
            default_stack_status=cluster_status.CREATE_IN_PROGRESS,
            stack_missing=True)
        poller.poll_and_check()
        for ng in cluster.nodegroups:
            self.assertEqual(cluster_status.CREATE_FAILED, ng.status)

    def test_stack_not_found_updating(self):
        cluster, poller = self.setup_poll_test(
            default_stack_status=cluster_status.UPDATE_IN_PROGRESS,
            stack_missing=True)
        poller.poll_and_check()
        for ng in cluster.nodegroups:
            self.assertEqual(cluster_status.UPDATE_FAILED, ng.status)

    def test_stack_not_found_deleting(self):
        cluster, poller = self.setup_poll_test(
            default_stack_status=cluster_status.DELETE_IN_PROGRESS,
            stack_missing=True)
        poller.poll_and_check()
        for ng in cluster.nodegroups:
            self.assertEqual(cluster_status.DELETE_COMPLETE, ng.status)

    def test_stack_not_found_new_ng_creating(self):
        cluster, poller = self.setup_poll_test()
        ng = self._create_nodegroup(
            cluster, 'ng1', 'stack2',
            stack_status=cluster_status.CREATE_IN_PROGRESS, stack_missing=True)
        poller.poll_and_check()
        for def_ng in self.def_ngs:
            self.assertEqual(cluster_status.CREATE_COMPLETE, def_ng.status)
        self.assertEqual(cluster_status.CREATE_FAILED, ng.status)

    def test_stack_not_found_new_ng_updating(self):
        cluster, poller = self.setup_poll_test()
        ng = self._create_nodegroup(
            cluster, 'ng1', 'stack2',
            stack_status=cluster_status.UPDATE_IN_PROGRESS, stack_missing=True)
        poller.poll_and_check()
        for def_ng in self.def_ngs:
            self.assertEqual(cluster_status.CREATE_COMPLETE, def_ng.status)
        self.assertEqual(cluster_status.UPDATE_FAILED, ng.status)

    def test_stack_not_found_new_ng_deleting(self):
        cluster, poller = self.setup_poll_test()
        ng = self._create_nodegroup(
            cluster, 'ng1', 'stack2',
            stack_status=cluster_status.DELETE_IN_PROGRESS, stack_missing=True)
        poller.poll_and_check()
        for def_ng in self.def_ngs:
            self.assertEqual(cluster_status.CREATE_COMPLETE, def_ng.status)
        self.assertEqual(cluster_status.DELETE_COMPLETE, ng.status)

    def test_poll_and_check_failed_default_ng(self):
        cluster, poller = self.setup_poll_test(
            default_stack_status=cluster_status.UPDATE_FAILED)

        ng = self._create_nodegroup(
            cluster, 'ng', 'stack2',
            stack_status=cluster_status.UPDATE_COMPLETE)

        cluster.status = cluster_status.UPDATE_IN_PROGRESS
        poller.poll_and_check()

        for def_ng in self.def_ngs:
            self.assertEqual(cluster_status.UPDATE_FAILED, def_ng.status)
            self.assertEqual(2, def_ng.save.call_count)

        self.assertEqual(cluster_status.UPDATE_COMPLETE, ng.status)
        self.assertEqual(1, ng.save.call_count)

        self.assertEqual(cluster_status.UPDATE_FAILED, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_poll_and_check_rollback_failed_default_ng(self):
        cluster, poller = self.setup_poll_test(
            default_stack_status=cluster_status.ROLLBACK_FAILED)

        ng = self._create_nodegroup(
            cluster, 'ng', 'stack2',
            stack_status=cluster_status.UPDATE_COMPLETE)

        cluster.status = cluster_status.UPDATE_IN_PROGRESS
        poller.poll_and_check()

        for def_ng in self.def_ngs:
            self.assertEqual(cluster_status.ROLLBACK_FAILED, def_ng.status)
            self.assertEqual(2, def_ng.save.call_count)

        self.assertEqual(cluster_status.UPDATE_COMPLETE, ng.status)
        self.assertEqual(1, ng.save.call_count)

        self.assertEqual(cluster_status.UPDATE_FAILED, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_poll_and_check_rollback_failed_def_ng(self):
        cluster, poller = self.setup_poll_test(
            default_stack_status=cluster_status.DELETE_FAILED)

        ng = self._create_nodegroup(
            cluster, 'ng', 'stack2',
            stack_status=cluster_status.DELETE_IN_PROGRESS)

        cluster.status = cluster_status.DELETE_IN_PROGRESS
        poller.poll_and_check()

        for def_ng in self.def_ngs:
            self.assertEqual(cluster_status.DELETE_FAILED, def_ng.status)
            self.assertEqual(2, def_ng.save.call_count)

        self.assertEqual(cluster_status.DELETE_IN_PROGRESS, ng.status)
        self.assertEqual(1, ng.save.call_count)

        self.assertEqual(cluster_status.DELETE_IN_PROGRESS, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_poll_and_check_delete_failed_def_ng(self):
        cluster, poller = self.setup_poll_test(
            default_stack_status=cluster_status.DELETE_FAILED)

        ng = self._create_nodegroup(
            cluster, 'ng', 'stack2',
            stack_status=cluster_status.DELETE_COMPLETE)

        cluster.status = cluster_status.DELETE_IN_PROGRESS
        poller.poll_and_check()

        for def_ng in self.def_ngs:
            self.assertEqual(cluster_status.DELETE_FAILED, def_ng.status)
            self.assertEqual(2, def_ng.save.call_count)

        # Check that the non-default ng was deleted
        self.assertEqual(1, ng.destroy.call_count)

        self.assertEqual(cluster_status.DELETE_FAILED, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

        self.assertIn('worker_ng', cluster.status_reason)
        self.assertIn('master_ng', cluster.status_reason)
