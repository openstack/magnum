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

import mock
import oslo_messaging as messaging

from magnum.common import exception
from magnum.common import short_id
from magnum.conductor import bay_lock
from magnum.tests import base
from magnum.tests.unit.objects import utils as obj_utils
from mock import patch


class BayLockTest(base.TestCase):

    def setUp(self):
        super(BayLockTest, self).setUp()
        self.conductor_id = short_id.generate_id()
        self.bay = obj_utils.get_test_bay(self.context)

    class TestThreadLockException(Exception):
        pass

    @patch('magnum.objects.BayLock.create', return_value=None)
    def test_successful_acquire_new_lock(self, mock_object_create):
        baylock = bay_lock.BayLock(self.context, self.bay, self.conductor_id)
        baylock.acquire()

        mock_object_create.assert_called_once_with(self.bay.uuid,
                                                   self.conductor_id)

    @patch('magnum.objects.BayLock.create')
    def test_failed_acquire_current_conductor_lock(self, mock_object_create):
        mock_object_create.return_value = self.conductor_id

        baylock = bay_lock.BayLock(self.context, self.bay, self.conductor_id)

        self.assertRaises(exception.OperationInProgress, baylock.acquire)
        mock_object_create.assert_called_once_with(self.bay.uuid,
                                                   self.conductor_id)

    @patch('magnum.objects.BayLock.steal', return_value=None)
    @patch('magnum.objects.BayLock.create', return_value='fake-conductor-id')
    def test_successful_acquire_dead_conductor_lock(self, mock_object_create,
                                                    mock_object_steal):
        baylock = bay_lock.BayLock(self.context, self.bay, self.conductor_id)
        with mock.patch.object(baylock, 'conductor_alive',
                               return_value=False):
            baylock.acquire()

            mock_object_create.assert_called_once_with(self.bay.uuid,
                                                       self.conductor_id)
            mock_object_steal.assert_called_once_with(
                self.bay.uuid,
                'fake-conductor-id', self.conductor_id)

    @patch('magnum.objects.BayLock.create', return_value='fake-conductor-id')
    def test_failed_acquire_alive_conductor_lock(self, mock_object_create):
        baylock = bay_lock.BayLock(self.context, self.bay, self.conductor_id)
        with mock.patch.object(baylock, 'conductor_alive',
                               return_value=True):
            self.assertRaises(exception.OperationInProgress, baylock.acquire)

            mock_object_create.assert_called_once_with(self.bay.uuid,
                                                       self.conductor_id)

    @patch('magnum.objects.BayLock.steal', return_value='fake-conductor-id2')
    @patch('magnum.objects.BayLock.create', return_value='fake-conductor-id')
    def test_failed_acquire_dead_conductor_lock(self, mock_object_create,
                                                mock_object_steal):
        baylock = bay_lock.BayLock(self.context, self.bay, self.conductor_id)
        with mock.patch.object(baylock, 'conductor_alive',
                               return_value=False):
            self.assertRaises(exception.OperationInProgress, baylock.acquire)

            mock_object_create.assert_called_once_with(self.bay.uuid,
                                                       self.conductor_id)
            mock_object_steal.assert_called_once_with(
                self.bay.uuid,
                'fake-conductor-id', self.conductor_id)

    @patch('magnum.objects.BayLock.steal', side_effect=[True, None])
    @patch('magnum.objects.BayLock.create', return_value='fake-conductor-id')
    def test_successful_acquire_with_retry(self, mock_object_create,
                                           mock_object_steal):
        baylock = bay_lock.BayLock(self.context, self.bay, self.conductor_id)
        with mock.patch.object(baylock, 'conductor_alive',
                               return_value=False):
            baylock.acquire()

            mock_object_create.assert_has_calls(
                [mock.call(self.bay.uuid, self.conductor_id)] * 2)
            mock_object_steal.assert_has_calls(
                [mock.call(self.bay.uuid, 'fake-conductor-id',
                           self.conductor_id)] * 2)

    @patch('magnum.objects.BayLock.steal', return_value=True)
    @patch('magnum.objects.BayLock.create', return_value='fake-conductor-id')
    def test_failed_acquire_one_retry_only(self, mock_object_create,
                                           mock_object_steal):
        baylock = bay_lock.BayLock(self.context, self.bay, self.conductor_id)
        with mock.patch.object(baylock, 'conductor_alive',
                               return_value=False):
            self.assertRaises(exception.OperationInProgress, baylock.acquire)

            mock_object_create.assert_has_calls(
                [mock.call(self.bay.uuid, self.conductor_id)] * 2)
            mock_object_steal.assert_has_calls(
                [mock.call(self.bay.uuid, 'fake-conductor-id',
                           self.conductor_id)] * 2)

    @patch('magnum.objects.BayLock.release', return_value=None)
    @patch('magnum.objects.BayLock.create', return_value=None)
    def test_thread_lock_acquire_success_with_exception(self,
                                                        mock_object_create,
                                                        mock_object_release):
        baylock = bay_lock.BayLock(self.context, self.bay, self.conductor_id)

        def check_thread_lock():
            with baylock.thread_lock(self.bay.uuid):
                self.assertEqual(1, mock_object_create.call_count)
                raise self.TestThreadLockException

        self.assertRaises(self.TestThreadLockException, check_thread_lock)
        self.assertEqual(1, mock_object_release.call_count)

    @patch('magnum.objects.BayLock.release', return_value=None)
    @patch('magnum.objects.BayLock.create')
    def test_thread_lock_acquire_fail_with_exception(self, mock_object_create,
                                                     mock_object_release):
        mock_object_create.return_value = self.conductor_id
        baylock = bay_lock.BayLock(self.context, self.bay, self.conductor_id)

        def check_thread_lock():
            with baylock.thread_lock(self.bay.uuid):
                self.assertEqual(1, mock_object_create.call_count)
                raise exception.OperationInProgress

        self.assertRaises(exception.OperationInProgress, check_thread_lock)
        assert not mock_object_release.called

    @patch('magnum.objects.BayLock.release', return_value=None)
    @patch('magnum.objects.BayLock.create', return_value=None)
    def test_thread_lock_acquire_success_no_exception(self, mock_object_create,
                                                      mock_object_release):
        baylock = bay_lock.BayLock(self.context, self.bay, self.conductor_id)
        with baylock.thread_lock(self.bay.uuid):
            self.assertEqual(1, mock_object_create.call_count)
        assert not mock_object_release.called

    @patch('magnum.conductor.api.ListenerAPI.__new__')
    def test_conductor_alive_ok(self, mock_listener_api_new):
        mock_listener_api = mock.MagicMock()
        mock_listener_api.ping_conductor.return_value = True
        mock_listener_api_new.return_value = mock_listener_api
        baylock = bay_lock.BayLock(self.context, self.bay, self.conductor_id)

        ret = baylock.conductor_alive(self.context, self.conductor_id)

        self.assertIs(True, ret)
        self.assertEqual(1, mock_listener_api_new.call_count)

    @patch('magnum.conductor.api.ListenerAPI.__new__')
    def test_conductor_alive_timeout(self, mock_listener_api_new):
        mock_listener_api = mock.MagicMock()
        mock_listener_api.ping_conductor.side_effect = (
            messaging.MessagingTimeout('too slow'))
        mock_listener_api_new.return_value = mock_listener_api
        baylock = bay_lock.BayLock(self.context, self.bay, self.conductor_id)

        ret = baylock.conductor_alive(self.context, self.conductor_id)

        self.assertIs(False, ret)
        self.assertEqual(1, mock_listener_api_new.call_count)
