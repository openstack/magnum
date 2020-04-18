# Copyright 2015 - Yahoo! Inc.
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

from magnum.common.rpc_service import CONF
from magnum import objects
from magnum.servicegroup import magnum_service_periodic as periodic
from magnum.tests import base


class MagnumServicePeriodicTestCase(base.TestCase):

    def setUp(self):
        super(MagnumServicePeriodicTestCase, self).setUp()
        mock_magnum_service_refresh = mock.Mock()

        class FakeMS(object):
            report_state_up = mock_magnum_service_refresh

        self.fake_ms = FakeMS()
        self.fake_ms_refresh = mock_magnum_service_refresh

    @mock.patch.object(objects.MagnumService, 'get_by_host_and_binary')
    @mock.patch.object(objects.MagnumService, 'create')
    @mock.patch.object(objects.MagnumService, 'report_state_up')
    def test_update_magnum_service_firsttime(self,
                                             mock_ms_refresh,
                                             mock_ms_create,
                                             mock_ms_get
                                             ):
        p_task = periodic.MagnumServicePeriodicTasks(CONF,
                                                     'fake-conductor')
        mock_ms_get.return_value = None

        p_task.update_magnum_service(None)

        mock_ms_get.assert_called_once_with(mock.ANY, p_task.host,
                                            p_task.binary)
        mock_ms_create.assert_called_once_with()
        mock_ms_refresh.assert_called_once_with()

    @mock.patch.object(objects.MagnumService, 'get_by_host_and_binary')
    @mock.patch.object(objects.MagnumService, 'create')
    def test_update_magnum_service_on_restart(self,
                                              mock_ms_create,
                                              mock_ms_get):
        p_task = periodic.MagnumServicePeriodicTasks(CONF,
                                                     'fake-conductor')
        mock_ms_get.return_value = self.fake_ms

        p_task.update_magnum_service(None)

        mock_ms_get.assert_called_once_with(mock.ANY, p_task.host,
                                            p_task.binary)
        self.fake_ms_refresh.assert_called_once_with()

    def test_update_magnum_service_regular(self):
        p_task = periodic.MagnumServicePeriodicTasks(CONF,
                                                     'fake-conductor')
        p_task.magnum_service_ref = self.fake_ms

        p_task.update_magnum_service(None)

        self.fake_ms_refresh.assert_called_once_with()
