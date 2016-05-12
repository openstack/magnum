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

import six
import uuid

from heatclient import exc
import mock
from mock import patch
from oslo_config import cfg
from oslo_service import loopingcall
from pycadf import cadftaxonomy as taxonomy

from magnum.common import exception
from magnum.conductor.handlers import bay_conductor
from magnum import objects
from magnum.objects.fields import BayStatus as bay_status
from magnum.tests import base
from magnum.tests import fake_notifier
from magnum.tests.unit.db import base as db_base
from magnum.tests.unit.db import utils


class TestHandler(db_base.DbTestCase):

    def setUp(self):
        super(TestHandler, self).setUp()
        self.handler = bay_conductor.Handler()
        baymodel_dict = utils.get_test_baymodel()
        self.baymodel = objects.BayModel(self.context, **baymodel_dict)
        self.baymodel.create()
        bay_dict = utils.get_test_bay(node_count=1)
        self.bay = objects.Bay(self.context, **bay_dict)
        self.bay.create()

    @patch('magnum.conductor.scale_manager.ScaleManager')
    @patch('magnum.conductor.handlers.bay_conductor.Handler._poll_and_check')
    @patch('magnum.conductor.handlers.bay_conductor._update_stack')
    @patch('magnum.common.clients.OpenStackClients')
    def test_update_node_count_success(
            self, mock_openstack_client_class,
            mock_update_stack, mock_poll_and_check,
            mock_scale_manager):
        def side_effect(*args, **kwargs):
            self.bay.node_count = 2
            self.bay.save()
        mock_poll_and_check.side_effect = side_effect
        mock_heat_stack = mock.MagicMock()
        mock_heat_stack.stack_status = bay_status.CREATE_COMPLETE
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client = mock_openstack_client_class.return_value
        mock_openstack_client.heat.return_value = mock_heat_client

        self.bay.node_count = 2
        self.handler.bay_update(self.context, self.bay)

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'magnum.bay.update', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])

        mock_update_stack.assert_called_once_with(
            self.context, mock_openstack_client, self.bay,
            mock_scale_manager.return_value)
        bay = objects.Bay.get(self.context, self.bay.uuid)
        self.assertEqual(2, bay.node_count)

    @patch('magnum.conductor.handlers.bay_conductor.Handler._poll_and_check')
    @patch('magnum.conductor.handlers.bay_conductor._update_stack')
    @patch('magnum.common.clients.OpenStackClients')
    def test_update_node_count_failure(
            self, mock_openstack_client_class,
            mock_update_stack, mock_poll_and_check):
        def side_effect(*args, **kwargs):
            self.bay.node_count = 2
            self.bay.save()
        mock_poll_and_check.side_effect = side_effect
        mock_heat_stack = mock.MagicMock()
        mock_heat_stack.stack_status = bay_status.CREATE_FAILED
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client = mock_openstack_client_class.return_value
        mock_openstack_client.heat.return_value = mock_heat_client

        self.bay.node_count = 2
        self.assertRaises(exception.NotSupported, self.handler.bay_update,
                          self.context, self.bay)

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'magnum.bay.update', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[0].payload['outcome'])

        bay = objects.Bay.get(self.context, self.bay.uuid)
        self.assertEqual(1, bay.node_count)

    @patch('magnum.conductor.scale_manager.ScaleManager')
    @patch('magnum.conductor.handlers.bay_conductor.Handler._poll_and_check')
    @patch('magnum.conductor.handlers.bay_conductor._update_stack')
    @patch('magnum.common.clients.OpenStackClients')
    def _test_update_bay_status_complete(
            self, expect_status, mock_openstack_client_class,
            mock_update_stack, mock_poll_and_check,
            mock_scale_manager):
        def side_effect(*args, **kwargs):
            self.bay.node_count = 2
            self.bay.save()
        mock_poll_and_check.side_effect = side_effect
        mock_heat_stack = mock.MagicMock()
        mock_heat_stack.stack_status = expect_status
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client = mock_openstack_client_class.return_value
        mock_openstack_client.heat.return_value = mock_heat_client

        self.bay.node_count = 2
        self.handler.bay_update(self.context, self.bay)

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'magnum.bay.update', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])

        mock_update_stack.assert_called_once_with(
            self.context, mock_openstack_client, self.bay,
            mock_scale_manager.return_value)
        bay = objects.Bay.get(self.context, self.bay.uuid)
        self.assertEqual(2, bay.node_count)

    def test_update_bay_status_update_compelete(self):
        self._test_update_bay_status_complete(bay_status.UPDATE_COMPLETE)

    def test_update_bay_status_resume_compelete(self):
        self._test_update_bay_status_complete(bay_status.RESUME_COMPLETE)

    def test_update_bay_status_restore_compelete(self):
        self._test_update_bay_status_complete(bay_status.RESTORE_COMPLETE)

    def test_update_bay_status_rollback_compelete(self):
        self._test_update_bay_status_complete(bay_status.ROLLBACK_COMPLETE)

    def test_update_bay_status_snapshot_compelete(self):
        self._test_update_bay_status_complete(bay_status.SNAPSHOT_COMPLETE)

    def test_update_bay_status_check_compelete(self):
        self._test_update_bay_status_complete(bay_status.CHECK_COMPLETE)

    def test_update_bay_status_adopt_compelete(self):
        self._test_update_bay_status_complete(bay_status.ADOPT_COMPLETE)

    @patch('magnum.conductor.handlers.bay_conductor.HeatPoller')
    @patch('magnum.conductor.handlers.bay_conductor.trust_manager')
    @patch('magnum.conductor.handlers.bay_conductor.cert_manager')
    @patch('magnum.conductor.handlers.bay_conductor._create_stack')
    @patch('magnum.conductor.handlers.bay_conductor.uuid')
    @patch('magnum.common.clients.OpenStackClients')
    def test_create(self, mock_openstack_client_class, mock_uuid,
                    mock_create_stack, mock_cert_manager, mock_trust_manager,
                    mock_heat_poller_class):
        timeout = 15
        test_uuid = uuid.uuid4()
        mock_uuid.uuid4.return_value = test_uuid
        mock_poller = mock.MagicMock()
        mock_poller.poll_and_check.return_value = loopingcall.LoopingCallDone()
        mock_heat_poller_class.return_value = mock_poller
        osc = mock.sentinel.osc
        mock_openstack_client_class.return_value = osc

        def create_stack_side_effect(context, osc, bay, timeout):
            self.assertEqual(str(test_uuid), bay.uuid)
            return {'stack': {'id': 'stack-id'}}

        mock_create_stack.side_effect = create_stack_side_effect

        # FixMe(eliqiao): bay_create will call bay.create() again, this so bad
        # because we have already called it in setUp since other test case will
        # share the codes in setUp()
        # But in self.handler.bay_create, we update bay.uuid and bay.stack_id
        # so bay.create will create a new recored with baymodel_id None,
        # this is bad because we load BayModel object in Bay object by
        # baymodel_id. Here update self.bay.baymodel_id so bay.obj_get_changes
        # will get notice that baymodel_id is updated and will update it
        # in db.
        self.bay.baymodel_id = self.baymodel.uuid
        bay = self.handler.bay_create(self.context,
                                      self.bay, timeout)

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'magnum.bay.create', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])

        mock_create_stack.assert_called_once_with(self.context,
                                                  mock.sentinel.osc,
                                                  self.bay, timeout)
        mock_cert_manager.generate_certificates_to_bay.assert_called_once_with(
            self.bay)
        self.assertEqual(bay_status.CREATE_IN_PROGRESS, bay.status)
        mock_trust_manager.create_trustee_and_trust.assert_called_once_with(
            osc, self.bay)

    def _test_create_failed(self,
                            mock_openstack_client_class,
                            mock_cert_manager,
                            mock_trust_manager,
                            expected_exception,
                            is_create_cert_called=True,
                            is_create_trust_called=True):
        osc = mock.MagicMock()
        mock_openstack_client_class.return_value = osc
        timeout = 15

        self.assertRaises(
            expected_exception,
            self.handler.bay_create,
            self.context,
            self.bay, timeout
        )

        gctb = mock_cert_manager.generate_certificates_to_bay
        if is_create_cert_called:
            gctb.assert_called_once_with(self.bay)
        else:
            gctb.assert_not_called()
        ctat = mock_trust_manager.create_trustee_and_trust
        if is_create_trust_called:
            ctat.assert_called_once_with(osc, self.bay)
        else:
            ctat.assert_not_called()

        mock_cert_manager.delete_certificates_from_bay(self.bay)
        mock_trust_manager.delete_trustee_and_trust.assert_called_once_with(
            osc, self.context, self.bay)

    @patch('magnum.conductor.handlers.bay_conductor.trust_manager')
    @patch('magnum.conductor.handlers.bay_conductor.cert_manager')
    @patch('magnum.conductor.handlers.bay_conductor._create_stack')
    @patch('magnum.common.clients.OpenStackClients')
    def test_create_handles_bad_request(self, mock_openstack_client_class,
                                        mock_create_stack,
                                        mock_cert_manager,
                                        mock_trust_manager):
        mock_create_stack.side_effect = exc.HTTPBadRequest

        self._test_create_failed(
            mock_openstack_client_class,
            mock_cert_manager,
            mock_trust_manager,
            exception.InvalidParameterValue
        )

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(2, len(notifications))
        self.assertEqual(
            'magnum.bay.create', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])
        self.assertEqual(
            'magnum.bay.create', notifications[1].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[1].payload['outcome'])

    @patch('magnum.conductor.handlers.bay_conductor.trust_manager')
    @patch('magnum.conductor.handlers.bay_conductor.cert_manager')
    @patch('magnum.common.clients.OpenStackClients')
    def test_create_with_cert_failed(self, mock_openstack_client_class,
                                     mock_cert_manager,
                                     mock_trust_manager):
        e = exception.CertificatesToBayFailed(bay_uuid='uuid')
        mock_cert_manager.generate_certificates_to_bay.side_effect = e

        self._test_create_failed(
            mock_openstack_client_class,
            mock_cert_manager,
            mock_trust_manager,
            exception.CertificatesToBayFailed
        )

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'magnum.bay.create', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[0].payload['outcome'])

    @patch('magnum.conductor.handlers.bay_conductor.trust_manager')
    @patch('magnum.conductor.handlers.bay_conductor.cert_manager')
    @patch('magnum.conductor.handlers.bay_conductor._create_stack')
    @patch('magnum.common.clients.OpenStackClients')
    def test_create_with_trust_failed(self, mock_openstack_client_class,
                                      mock_create_stack,
                                      mock_cert_manager,
                                      mock_trust_manager):
        e = exception.TrusteeOrTrustToBayFailed(bay_uuid='uuid')
        mock_trust_manager.create_trustee_and_trust.side_effect = e

        self._test_create_failed(
            mock_openstack_client_class,
            mock_cert_manager,
            mock_trust_manager,
            exception.TrusteeOrTrustToBayFailed,
            False
        )

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'magnum.bay.create', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[0].payload['outcome'])

    @patch('magnum.conductor.handlers.bay_conductor.trust_manager')
    @patch('magnum.conductor.handlers.bay_conductor.cert_manager')
    @patch('magnum.conductor.handlers.bay_conductor._create_stack')
    @patch('magnum.conductor.handlers.bay_conductor.uuid')
    @patch('magnum.common.clients.OpenStackClients')
    def test_create_with_invalid_unicode_name(self,
                                              mock_openstack_client_class,
                                              mock_uuid,
                                              mock_create_stack,
                                              mock_cert_manager,
                                              mock_trust_manager):
        test_uuid = uuid.uuid4()
        mock_uuid.uuid4.return_value = test_uuid
        error_message = six.u("""Invalid stack name 测试集群-zoyh253geukk
                              must contain only alphanumeric or "_-."
                              characters, must start with alpha""")
        mock_create_stack.side_effect = exc.HTTPBadRequest(error_message)

        self._test_create_failed(
            mock_openstack_client_class,
            mock_cert_manager,
            mock_trust_manager,
            exception.InvalidParameterValue
        )

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(2, len(notifications))
        self.assertEqual(
            'magnum.bay.create', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])
        self.assertEqual(
            'magnum.bay.create', notifications[1].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[1].payload['outcome'])

    @patch('magnum.common.clients.OpenStackClients')
    def test_bay_delete(self, mock_openstack_client_class):
        osc = mock.MagicMock()
        mock_openstack_client_class.return_value = osc
        osc.heat.side_effect = exc.HTTPNotFound
        self.handler.bay_delete(self.context, self.bay.uuid)

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(2, len(notifications))
        self.assertEqual(
            'magnum.bay.delete', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])
        self.assertEqual(
            'magnum.bay.delete', notifications[1].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_SUCCESS, notifications[1].payload['outcome'])
        # The bay has been destroyed
        self.assertRaises(exception.BayNotFound,
                          objects.Bay.get, self.context, self.bay.uuid)

    @patch('magnum.common.clients.OpenStackClients')
    def test_bay_delete_conflict(self, mock_openstack_client_class):
        osc = mock.MagicMock()
        mock_openstack_client_class.return_value = osc
        osc.heat.side_effect = exc.HTTPConflict
        self.assertRaises(exception.OperationInProgress,
                          self.handler.bay_delete,
                          self.context,
                          self.bay.uuid)

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(2, len(notifications))
        self.assertEqual(
            'magnum.bay.delete', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])
        self.assertEqual(
            'magnum.bay.delete', notifications[1].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[1].payload['outcome'])


class TestHeatPoller(base.TestCase):

    @patch('magnum.conductor.utils.retrieve_baymodel')
    @patch('oslo_config.cfg')
    @patch('magnum.common.clients.OpenStackClients')
    def setup_poll_test(self, mock_openstack_client, cfg,
                        mock_retrieve_baymodel):
        cfg.CONF.bay_heat.max_attempts = 10
        bay = mock.MagicMock()
        baymodel_dict = utils.get_test_baymodel(coe='kubernetes')
        mock_heat_stack = mock.MagicMock()
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client.heat.return_value = mock_heat_client
        baymodel = objects.BayModel(self.context, **baymodel_dict)
        mock_retrieve_baymodel.return_value = baymodel
        poller = bay_conductor.HeatPoller(mock_openstack_client, bay)
        return (mock_heat_stack, bay, poller)

    def test_poll_and_check_send_notification(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()
        mock_heat_stack.stack_status = bay_status.CREATE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        mock_heat_stack.stack_status = bay_status.CREATE_FAILED
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        mock_heat_stack.stack_status = bay_status.DELETE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        mock_heat_stack.stack_status = bay_status.DELETE_FAILED
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        mock_heat_stack.stack_status = bay_status.UPDATE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        mock_heat_stack.stack_status = bay_status.UPDATE_FAILED
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(6, poller.attempts)
        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(6, len(notifications))
        self.assertEqual(
            'magnum.bay.create', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_SUCCESS, notifications[0].payload['outcome'])
        self.assertEqual(
            'magnum.bay.create', notifications[1].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[1].payload['outcome'])
        self.assertEqual(
            'magnum.bay.delete', notifications[2].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_SUCCESS, notifications[2].payload['outcome'])
        self.assertEqual(
            'magnum.bay.delete', notifications[3].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[3].payload['outcome'])
        self.assertEqual(
            'magnum.bay.update', notifications[4].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_SUCCESS, notifications[4].payload['outcome'])
        self.assertEqual(
            'magnum.bay.update', notifications[5].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[5].payload['outcome'])

    def test_poll_no_save(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        bay.status = bay_status.CREATE_IN_PROGRESS
        mock_heat_stack.stack_status = bay_status.CREATE_IN_PROGRESS
        poller.poll_and_check()

        self.assertEqual(0, bay.save.call_count)
        self.assertEqual(1, poller.attempts)

    def test_poll_save(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        bay.status = bay_status.CREATE_IN_PROGRESS
        mock_heat_stack.stack_status = bay_status.CREATE_FAILED
        mock_heat_stack.stack_status_reason = 'Create failed'
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(2, bay.save.call_count)
        self.assertEqual(bay_status.CREATE_FAILED, bay.status)
        self.assertEqual('Create failed', bay.status_reason)
        self.assertEqual(1, poller.attempts)

    def test_poll_done(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.DELETE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        mock_heat_stack.stack_status = bay_status.CREATE_FAILED
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        self.assertEqual(2, poller.attempts)

    def test_poll_done_by_update(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.UPDATE_COMPLETE
        mock_heat_stack.parameters = {'number_of_minions': 2}
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(1, bay.save.call_count)
        self.assertEqual(bay_status.UPDATE_COMPLETE, bay.status)
        self.assertEqual(2, bay.node_count)
        self.assertEqual(1, poller.attempts)

    def test_poll_done_by_update_failed(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.UPDATE_FAILED
        mock_heat_stack.parameters = {'number_of_minions': 2}
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(2, bay.save.call_count)
        self.assertEqual(bay_status.UPDATE_FAILED, bay.status)
        self.assertEqual(2, bay.node_count)
        self.assertEqual(1, poller.attempts)

    def test_poll_destroy(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.DELETE_FAILED
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        # Destroy method is not called when stack delete failed
        self.assertEqual(0, bay.destroy.call_count)

        mock_heat_stack.stack_status = bay_status.DELETE_IN_PROGRESS
        poller.poll_and_check()
        self.assertEqual(0, bay.destroy.call_count)
        self.assertEqual(bay_status.DELETE_IN_PROGRESS, bay.status)

        mock_heat_stack.stack_status = bay_status.DELETE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        # The bay status should still be DELETE_IN_PROGRESS, because
        # the destroy() method may be failed. If success, this bay record
        # will delete directly, change status is meaningless.
        self.assertEqual(bay_status.DELETE_IN_PROGRESS, bay.status)
        self.assertEqual(1, bay.destroy.call_count)

    def test_poll_delete_in_progress_timeout_set(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.DELETE_IN_PROGRESS
        mock_heat_stack.timeout_mins = 60
        # timeout only affects stack creation so expecting this
        # to process normally
        poller.poll_and_check()

    def test_poll_delete_in_progress_max_attempts_reached(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.DELETE_IN_PROGRESS
        poller.attempts = cfg.CONF.bay_heat.max_attempts
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

    def test_poll_create_in_prog_max_att_reached_no_timeout(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.CREATE_IN_PROGRESS
        poller.attempts = cfg.CONF.bay_heat.max_attempts
        mock_heat_stack.timeout_mins = None
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

    def test_poll_create_in_prog_max_att_reached_timeout_set(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.CREATE_IN_PROGRESS
        poller.attempts = cfg.CONF.bay_heat.max_attempts
        mock_heat_stack.timeout_mins = 60
        # since the timeout is set the max attempts gets ignored since
        # the timeout will eventually stop the poller either when
        # the stack gets created or the timeout gets reached
        poller.poll_and_check()

    def test_poll_create_in_prog_max_att_reached_timed_out(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.CREATE_FAILED
        poller.attempts = cfg.CONF.bay_heat.max_attempts
        mock_heat_stack.timeout_mins = 60
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

    def test_poll_create_in_prog_max_att_not_reached_no_timeout(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.CREATE_IN_PROGRESS
        mock_heat_stack.timeout.mins = None
        poller.poll_and_check()

    def test_poll_create_in_prog_max_att_not_reached_timeout_set(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.CREATE_IN_PROGRESS
        mock_heat_stack.timeout_mins = 60
        poller.poll_and_check()

    def test_poll_create_in_prog_max_att_not_reached_timed_out(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.CREATE_FAILED
        mock_heat_stack.timeout_mins = 60
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

    def test_poll_node_count(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.parameters = {'number_of_minions': 1}
        mock_heat_stack.stack_status = bay_status.CREATE_IN_PROGRESS
        poller.poll_and_check()

        self.assertEqual(1, bay.node_count)

    def test_poll_node_count_by_update(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.parameters = {'number_of_minions': 2}
        mock_heat_stack.stack_status = bay_status.UPDATE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(2, bay.node_count)

    @patch('magnum.conductor.handlers.bay_conductor.trust_manager')
    @patch('magnum.conductor.handlers.bay_conductor.cert_manager')
    def test_delete_complete(self, cert_manager, trust_manager):
        mock_heat_stack, bay, poller = self.setup_poll_test()
        poller._delete_complete()
        self.assertEqual(1, bay.destroy.call_count)
        self.assertEqual(1,
                         cert_manager.delete_certificates_from_bay.call_count)
        self.assertEqual(1,
                         trust_manager.delete_trustee_and_trust.call_count)

    def test_create_or_complete(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()
        mock_heat_stack.stack_status = bay_status.CREATE_COMPLETE
        mock_heat_stack.stack_status_reason = 'stack complete'
        poller._sync_bay_and_template_status(mock_heat_stack)
        self.assertEqual('stack complete', bay.status_reason)
        self.assertEqual(bay_status.CREATE_COMPLETE, bay.status)
        self.assertEqual(1, bay.save.call_count)

    def test_sync_bay_status(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()
        mock_heat_stack.stack_status = bay_status.CREATE_IN_PROGRESS
        mock_heat_stack.stack_status_reason = 'stack incomplete'
        poller._sync_bay_status(mock_heat_stack)
        self.assertEqual('stack incomplete', bay.status_reason)
        self.assertEqual(bay_status.CREATE_IN_PROGRESS, bay.status)

    @patch('magnum.conductor.handlers.bay_conductor.LOG')
    def test_bay_failed(self, logger):
        mock_heat_stack, bay, poller = self.setup_poll_test()
        poller._sync_bay_and_template_status(mock_heat_stack)
        poller._bay_failed(mock_heat_stack)
        self.assertEqual(1, logger.error.call_count)
