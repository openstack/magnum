# -*- coding: utf-8 -*-

# Copyright 2014 NEC Corporation.  All rights reserved.
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
from unittest.mock import patch

from heatclient import exc
from oslo_service import loopingcall
from pycadf import cadftaxonomy as taxonomy

from magnum.common import exception
from magnum.conductor.handlers import cluster_conductor
import magnum.conf
from magnum.drivers.k8s_fedora_coreos_v1 import driver as k8s_fcos_dr
from magnum import objects
from magnum.objects.fields import ClusterHealthStatus
from magnum.objects.fields import ClusterStatus as cluster_status
from magnum.tests import fake_notifier
from magnum.tests.unit.db import base as db_base
from magnum.tests.unit.db import utils

CONF = magnum.conf.CONF


class TestHandler(db_base.DbTestCase):

    def setUp(self):
        super(TestHandler, self).setUp()
        self.handler = cluster_conductor.Handler()
        cluster_template_dict = utils.get_test_cluster_template()
        self.cluster_template = objects.ClusterTemplate(
            self.context, **cluster_template_dict)
        self.cluster_template.create()
        self.cluster_dict = utils.get_test_cluster(node_count=1)
        self.nodegroups_dict = utils.get_nodegroups_for_cluster(
            node_count=1)
        del self.nodegroups_dict['master']['id']
        del self.nodegroups_dict['worker']['id']
        self.cluster = objects.Cluster(self.context, **self.cluster_dict)
        self.master_count = self.cluster.master_count
        self.node_count = self.cluster.node_count
        self.cluster.create()
        self.master = objects.NodeGroup(
            self.context, **self.nodegroups_dict['master'])
        self.worker = objects.NodeGroup(
            self.context, **self.nodegroups_dict['worker'])

    @patch('magnum.conductor.scale_manager.get_scale_manager')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    @patch('magnum.common.clients.OpenStackClients')
    def test_update_node_count_success(
            self, mock_openstack_client_class,
            mock_driver,
            mock_scale_manager):

        mock_heat_stack = mock.MagicMock()
        mock_heat_stack.stack_status = cluster_status.CREATE_COMPLETE
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client = mock_openstack_client_class.return_value
        mock_openstack_client.heat.return_value = mock_heat_client
        mock_dr = mock.MagicMock()
        mock_driver.return_value = mock_dr

        node_count = 2
        self.master.create()
        self.worker.create()
        self.cluster.status = cluster_status.CREATE_COMPLETE
        self.handler.cluster_update(self.context, self.cluster, node_count,
                                    ClusterHealthStatus.UNKNOWN, {})

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'magnum.cluster.update', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])

        mock_dr.update_cluster.assert_called_once_with(
            self.context, self.cluster, mock_scale_manager.return_value,
            False)
        cluster = objects.Cluster.get_by_uuid(self.context, self.cluster.uuid)
        self.assertEqual(2, cluster.node_count)
        self.assertEqual(2, cluster.default_ng_worker.node_count)

    @patch('magnum.common.clients.OpenStackClients')
    def test_update_node_count_failure(
            self, mock_openstack_client_class):

        mock_heat_stack = mock.MagicMock()
        mock_heat_stack.stack_status = cluster_status.CREATE_FAILED
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client = mock_openstack_client_class.return_value
        mock_openstack_client.heat.return_value = mock_heat_client

        node_count = 2
        self.master.create()
        self.worker.create()
        self.cluster.status = cluster_status.CREATE_FAILED
        self.assertRaises(exception.NotSupported, self.handler.cluster_update,
                          self.context, self.cluster, node_count,
                          ClusterHealthStatus.UNKNOWN, {})

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'magnum.cluster.update', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[0].payload['outcome'])

        cluster = objects.Cluster.get(self.context, self.cluster.uuid)
        self.assertEqual(1, self.worker.node_count)
        self.assertEqual(1, cluster.node_count)

    @patch('magnum.conductor.scale_manager.get_scale_manager')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    @patch('magnum.common.clients.OpenStackClients')
    def _test_update_cluster_status_complete(
            self, expect_status, mock_openstack_client_class,
            mock_driver, mock_scale_manager):

        mock_heat_stack = mock.MagicMock()
        mock_heat_stack.stack_status = expect_status
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client = mock_openstack_client_class.return_value
        mock_openstack_client.heat.return_value = mock_heat_client
        mock_dr = mock.MagicMock()
        mock_driver.return_value = mock_dr

        node_count = 2
        self.cluster.status = cluster_status.CREATE_COMPLETE
        self.master.create()
        self.worker.create()
        self.handler.cluster_update(self.context, self.cluster, node_count,
                                    ClusterHealthStatus.UNKNOWN, {})

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'magnum.cluster.update', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])

        mock_dr.update_cluster.assert_called_once_with(
            self.context, self.cluster, mock_scale_manager.return_value, False)
        cluster = objects.Cluster.get(self.context, self.cluster.uuid)
        self.assertEqual(2, cluster.node_count)
        self.assertEqual(2, cluster.default_ng_worker.node_count)

    def test_update_cluster_status_update_complete(self):
        self._test_update_cluster_status_complete(
            cluster_status.UPDATE_COMPLETE)

    def test_update_cluster_status_resume_complete(self):
        self._test_update_cluster_status_complete(
            cluster_status.RESUME_COMPLETE)

    def test_update_cluster_status_restore_complete(self):
        self._test_update_cluster_status_complete(
            cluster_status.RESTORE_COMPLETE)

    def test_update_cluster_status_rollback_complete(self):
        self._test_update_cluster_status_complete(
            cluster_status.ROLLBACK_COMPLETE)

    def test_update_cluster_status_snapshot_complete(self):
        self._test_update_cluster_status_complete(
            cluster_status.SNAPSHOT_COMPLETE)

    def test_update_cluster_status_check_complete(self):
        self._test_update_cluster_status_complete(
            cluster_status.CHECK_COMPLETE)

    def test_update_cluster_status_adopt_complete(self):
        self._test_update_cluster_status_complete(
            cluster_status.ADOPT_COMPLETE)

    @patch('magnum.drivers.heat.driver.HeatPoller')
    @patch('magnum.conductor.handlers.cluster_conductor.trust_manager')
    @patch('magnum.conductor.handlers.cluster_conductor.cert_manager')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    @patch('magnum.common.clients.OpenStackClients')
    def test_create(self, mock_openstack_client_class,
                    mock_driver, mock_cm, mock_trust_manager,
                    mock_heat_poller_class):
        timeout = 15
        mock_poller = mock.MagicMock()
        mock_poller.poll_and_check.return_value = loopingcall.LoopingCallDone()
        mock_heat_poller_class.return_value = mock_poller
        osc = mock.sentinel.osc

        def return_keystone():
            return self.keystone_client

        osc.keystone = return_keystone
        mock_openstack_client_class.return_value = osc
        mock_dr = mock.MagicMock()
        mock_driver.return_value = mock_dr

        def create_stack_side_effect(context, osc, cluster, timeout):
            return {'stack': {'id': 'stack-id'}}

        mock_dr.create_stack.side_effect = create_stack_side_effect

        # Just create a new cluster, since the one in setUp is already
        # created and the previous solution seems kind of hacky.
        cluster_dict = utils.get_test_cluster(node_count=1)
        cluster = objects.Cluster(self.context, **cluster_dict)
        node_count = 1
        master_count = 1
        del cluster_dict['id']
        del cluster_dict['uuid']
        cluster_obj = objects.Cluster(self.context, **cluster_dict)
        cluster = self.handler.cluster_create(self.context, cluster_obj,
                                              master_count, node_count,
                                              timeout)

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'magnum.cluster.create', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])

        mock_dr.create_cluster.assert_called_once_with(self.context,
                                                       cluster, timeout)
        mock_cm.generate_certificates_to_cluster.assert_called_once_with(
            cluster, context=self.context)
        self.assertEqual(cluster_status.CREATE_IN_PROGRESS, cluster.status)
        mock_trust_manager.create_trustee_and_trust.assert_called_once_with(
            osc, cluster)
        self.assertEqual(2, len(cluster.nodegroups))
        self.assertEqual(node_count, cluster.node_count)
        self.assertEqual(master_count, cluster.master_count)
        self.assertEqual(node_count, cluster.default_ng_worker.node_count)
        self.assertEqual(master_count, cluster.default_ng_master.node_count)

    def _test_create_failed(self,
                            mock_openstack_client_class,
                            mock_cert_manager,
                            mock_trust_manager,
                            mock_cluster_create,
                            expected_exception,
                            is_create_cert_called=True,
                            is_create_trust_called=True):
        osc = mock.MagicMock()
        mock_openstack_client_class.return_value = osc
        timeout = 15

        self.assertRaises(
            expected_exception,
            self.handler.cluster_create,
            self.context, self.cluster,
            self.master_count, self.node_count, timeout
        )

        gctb = mock_cert_manager.generate_certificates_to_cluster
        if is_create_cert_called:
            gctb.assert_called_once_with(self.cluster, context=self.context)
        else:
            gctb.assert_not_called()
        ctat = mock_trust_manager.create_trustee_and_trust
        if is_create_trust_called:
            ctat.assert_called_once_with(osc, self.cluster)
        else:
            ctat.assert_not_called()
        mock_cluster_create.assert_called_once_with()

    @patch('magnum.objects.Cluster.create')
    @patch('magnum.conductor.handlers.cluster_conductor.trust_manager')
    @patch('magnum.conductor.handlers.cluster_conductor.cert_manager')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    @patch('magnum.common.clients.OpenStackClients')
    def test_create_handles_bad_request(self, mock_openstack_client_class,
                                        mock_driver,
                                        mock_cert_manager,
                                        mock_trust_manager,
                                        mock_cluster_create):
        mock_dr = mock.MagicMock()
        mock_driver.return_value = mock_dr
        mock_dr.create_cluster.side_effect = exc.HTTPBadRequest

        self._test_create_failed(
            mock_openstack_client_class,
            mock_cert_manager,
            mock_trust_manager,
            mock_cluster_create,
            exception.InvalidParameterValue
        )

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(2, len(notifications))
        self.assertEqual(
            'magnum.cluster.create', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])
        self.assertEqual(
            'magnum.cluster.create', notifications[1].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[1].payload['outcome'])

    @patch('magnum.objects.Cluster.create')
    @patch('magnum.conductor.handlers.cluster_conductor.trust_manager')
    @patch('magnum.conductor.handlers.cluster_conductor.cert_manager')
    @patch('magnum.common.clients.OpenStackClients')
    def test_create_with_cert_failed(self, mock_openstack_client_class,
                                     mock_cert_manager,
                                     mock_trust_manager,
                                     mock_cluster_create):
        e = exception.CertificatesToClusterFailed(cluster_uuid='uuid')
        mock_cert_manager.generate_certificates_to_cluster.side_effect = e

        self._test_create_failed(
            mock_openstack_client_class,
            mock_cert_manager,
            mock_trust_manager,
            mock_cluster_create,
            exception.CertificatesToClusterFailed
        )

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'magnum.cluster.create', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[0].payload['outcome'])

    @patch('magnum.objects.Cluster.create')
    @patch('magnum.conductor.handlers.cluster_conductor.trust_manager')
    @patch('magnum.conductor.handlers.cluster_conductor.cert_manager')
    @patch('magnum.common.clients.OpenStackClients')
    def test_create_with_trust_failed(self, mock_openstack_client_class,
                                      mock_cert_manager,
                                      mock_trust_manager,
                                      mock_cluster_create):
        e = exception.TrusteeOrTrustToClusterFailed(cluster_uuid='uuid')
        mock_trust_manager.create_trustee_and_trust.side_effect = e

        self._test_create_failed(
            mock_openstack_client_class,
            mock_cert_manager,
            mock_trust_manager,
            mock_cluster_create,
            exception.TrusteeOrTrustToClusterFailed,
            False
        )

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'magnum.cluster.create', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[0].payload['outcome'])

    @patch('magnum.objects.Cluster.create')
    @patch('magnum.conductor.handlers.cluster_conductor.trust_manager')
    @patch('magnum.conductor.handlers.cluster_conductor.cert_manager')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    @patch('magnum.common.clients.OpenStackClients')
    def test_create_with_invalid_unicode_name(self,
                                              mock_openstack_client_class,
                                              mock_driver,
                                              mock_cert_manager,
                                              mock_trust_manager,
                                              mock_cluster_create):
        error_message = ("Invalid stack name 测试集群-zoyh253geukk must "
                         "contain only alphanumeric or \"_-.\" characters, "
                         "must start with alpha")
        mock_dr = mock.MagicMock()
        mock_driver.return_value = mock_dr
        mock_dr.create_cluster.side_effect = exc.HTTPBadRequest(error_message)

        self._test_create_failed(
            mock_openstack_client_class,
            mock_cert_manager,
            mock_trust_manager,
            mock_cluster_create,
            exception.InvalidParameterValue
        )

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(2, len(notifications))
        self.assertEqual(
            'magnum.cluster.create', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])
        self.assertEqual(
            'magnum.cluster.create', notifications[1].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[1].payload['outcome'])

    @patch('magnum.drivers.heat.driver.HeatPoller')
    @patch('heatclient.common.template_utils'
           '.process_multiple_environments_and_files')
    @patch('heatclient.common.template_utils.get_template_contents')
    @patch('magnum.conductor.handlers.cluster_conductor.trust_manager')
    @patch('magnum.conductor.handlers.cluster_conductor.cert_manager')
    @patch('magnum.drivers.k8s_fedora_coreos_v1.driver.Driver.'
           '_extract_template_definition')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    @patch('magnum.common.clients.OpenStackClients')
    @patch('magnum.common.short_id.generate_id')
    def test_create_with_environment(self,
                                     mock_short_id,
                                     mock_openstack_client_class,
                                     mock_driver,
                                     mock_extract_tmpl_def,
                                     mock_cert_manager,
                                     mock_trust_manager,
                                     mock_get_template_contents,
                                     mock_process_mult,
                                     mock_heat_poller_class):
        timeout = 15
        mock_poller = mock.MagicMock()
        mock_poller.poll_and_check.return_value = loopingcall.LoopingCallDone()
        mock_heat_poller_class.return_value = mock_poller
        mock_driver.return_value = k8s_fcos_dr.Driver()
        mock_short_id.return_value = 'short_id'

        mock_extract_tmpl_def.return_value = (
            'the/template/path.yaml',
            {'heat_param_1': 'foo', 'heat_param_2': 'bar'},
            ['env_file_1', 'env_file_2'])

        mock_get_template_contents.return_value = (
            {'tmpl_file_1': 'some content',
             'tmpl_file_2': 'some more content'},
            'some template yaml')

        def do_mock_process_mult(env_paths=None, env_list_tracker=None):
            self.assertEqual(env_list_tracker, [])
            for f in env_paths:
                env_list_tracker.append('file:///' + f)
            env_map = {path: 'content of ' + path for path in env_list_tracker}
            return (env_map, None)

        mock_process_mult.side_effect = do_mock_process_mult

        mock_hc = mock.Mock()
        mock_hc.stacks.create.return_value = {'stack': {'id': 'stack-id'}}

        osc = mock.Mock()
        osc.heat.return_value = mock_hc
        mock_openstack_client_class.return_value = osc

        # NOTE(ttsiouts): self.cluster is already created so it's
        # a bad idea to use it and try to create it again... Instead
        # get a new object and use it.
        cluster_dict = utils.get_test_cluster(
            node_count=1, uuid='f6a99187-6f42-4fbb-aa6f-18407c0ee50e')
        del cluster_dict['id']
        cluster = objects.Cluster(self.context, **cluster_dict)
        node_count = cluster.node_count
        master_count = cluster.master_count

        self.handler.cluster_create(self.context, cluster,
                                    master_count, node_count,
                                    timeout)

        mock_extract_tmpl_def.assert_called_once_with(self.context,
                                                      cluster,
                                                      nodegroups=None)
        mock_get_template_contents.assert_called_once_with(
            'the/template/path.yaml')
        mock_process_mult.assert_called_once_with(
            env_paths=['the/template/env_file_1', 'the/template/env_file_2'],
            env_list_tracker=mock.ANY)
        mock_hc.stacks.create.assert_called_once_with(
            environment_files=['file:///the/template/env_file_1',
                               'file:///the/template/env_file_2'],
            files={
                'tmpl_file_1': 'some content',
                'tmpl_file_2': 'some more content',
                'file:///the/template/env_file_1':
                    'content of file:///the/template/env_file_1',
                'file:///the/template/env_file_2':
                    'content of file:///the/template/env_file_2'
            },
            parameters={'is_cluster_stack': True, 'heat_param_1': 'foo',
                        'heat_param_2': 'bar'},
            stack_name=('%s-short_id' % cluster.name),
            template='some template yaml',
            timeout_mins=timeout)
        self.assertEqual(node_count, cluster.node_count)
        self.assertEqual(node_count, cluster.default_ng_worker.node_count)
        self.assertEqual(master_count, cluster.master_count)
        self.assertEqual(master_count, cluster.default_ng_master.node_count)

    @patch('magnum.conductor.handlers.cluster_conductor.cert_manager')
    @patch('magnum.common.clients.OpenStackClients')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    @patch('magnum.common.keystone.is_octavia_enabled')
    def test_cluster_delete(self, mock_octavia, mock_driver,
                            mock_openstack_client_class, cert_manager):
        mock_octavia.return_value = False
        mock_driver.return_value = k8s_fcos_dr.Driver()
        osc = mock.MagicMock()
        mock_openstack_client_class.return_value = osc
        osc.heat.side_effect = exc.HTTPNotFound
        self.master.create()
        self.worker.create()
        self.assertEqual(2, len(self.cluster.nodegroups))
        self.handler.cluster_delete(self.context, self.cluster.uuid)

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(2, len(notifications))
        self.assertEqual(
            'magnum.cluster.delete', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])
        self.assertEqual(
            'magnum.cluster.delete', notifications[1].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_SUCCESS, notifications[1].payload['outcome'])
        self.assertEqual(
            1, cert_manager.delete_certificates_from_cluster.call_count)
        # Assert that the cluster nodegroups were delete as well
        db_nodegroups = objects.NodeGroup.list(self.context, self.cluster.uuid)
        self.assertEqual([], db_nodegroups)
        # The cluster has been destroyed
        self.assertRaises(exception.ClusterNotFound,
                          objects.Cluster.get, self.context, self.cluster.uuid)

    @patch('magnum.conductor.handlers.cluster_conductor.cert_manager')
    @patch('magnum.common.clients.OpenStackClients')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    @patch('magnum.common.keystone.is_octavia_enabled')
    def test_cluster_delete_conflict(self, mock_octavia, mock_driver,
                                     mock_openstack_client_class,
                                     cert_manager):
        mock_octavia.return_value = False
        mock_driver.return_value = k8s_fcos_dr.Driver()
        osc = mock.MagicMock()
        mock_openstack_client_class.return_value = osc
        osc.heat.side_effect = exc.HTTPConflict
        self.worker.create()
        self.master.create()
        self.assertRaises(exception.OperationInProgress,
                          self.handler.cluster_delete,
                          self.context,
                          self.cluster.uuid)

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(2, len(notifications))
        self.assertEqual(
            'magnum.cluster.delete', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])
        self.assertEqual(
            'magnum.cluster.delete', notifications[1].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[1].payload['outcome'])
        self.assertEqual(
            0, cert_manager.delete_certificates_from_cluster.call_count)

    @patch('magnum.drivers.common.driver.Driver.get_driver')
    @patch('magnum.common.clients.OpenStackClients')
    @patch('magnum.common.keystone.is_octavia_enabled')
    @patch('magnum.common.octavia.delete_loadbalancers')
    def test_cluster_delete_with_lb(self, mock_delete_lb, mock_octavia,
                                    mock_clients, mock_driver):
        mock_octavia.return_value = True
        mock_driver.return_value = k8s_fcos_dr.Driver()

        self.master.create()
        self.worker.create()
        self.handler.cluster_delete(self.context, self.cluster.uuid)

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(1, len(notifications))
        self.assertEqual(1, mock_delete_lb.call_count)

    @patch('magnum.conductor.scale_manager.get_scale_manager')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    @patch('magnum.common.clients.OpenStackClients')
    def test_cluster_resize_success(
            self, mock_openstack_client_class,
            mock_driver,
            mock_scale_manager):

        mock_heat_stack = mock.MagicMock()
        mock_heat_stack.stack_status = cluster_status.CREATE_COMPLETE
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client = mock_openstack_client_class.return_value
        mock_openstack_client.heat.return_value = mock_heat_client
        mock_dr = mock.MagicMock()
        mock_driver.return_value = mock_dr

        # Create the default worker
        self.worker.create()
        self.cluster.status = cluster_status.CREATE_COMPLETE
        self.handler.cluster_resize(self.context, self.cluster, 3, ["ID1"],
                                    self.worker)

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'magnum.cluster.update', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])

        mock_dr.resize_cluster.assert_called_once_with(
            self.context, self.cluster, mock_scale_manager.return_value, 3,
            ["ID1"], self.worker)
        nodegroup = objects.NodeGroup.get_by_uuid(
            self.context, self.cluster.uuid, self.worker.uuid)
        self.assertEqual(3, nodegroup.node_count)

    @patch('magnum.common.clients.OpenStackClients')
    def test_cluster_resize_failure(
            self, mock_openstack_client_class):

        mock_heat_stack = mock.MagicMock()
        mock_heat_stack.stack_status = cluster_status.CREATE_FAILED
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client = mock_openstack_client_class.return_value
        mock_openstack_client.heat.return_value = mock_heat_client

        # Create the default worker
        self.worker.create()
        self.cluster.status = cluster_status.CREATE_FAILED
        self.assertRaises(exception.NotSupported, self.handler.cluster_resize,
                          self.context, self.cluster, 2, [], self.worker)

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'magnum.cluster.update', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[0].payload['outcome'])

        cluster = objects.Cluster.get(self.context, self.cluster.uuid)
        self.assertEqual(1, cluster.node_count)
        nodegroup = objects.NodeGroup.get_by_uuid(
            self.context, self.cluster.uuid, self.worker.uuid)
        self.assertEqual(1, nodegroup.node_count)
