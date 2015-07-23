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

import mock

from oslo_config import cfg

from magnum.common import context
from magnum.common.rpc_service import CONF
from magnum.db.sqlalchemy import api as dbapi
from magnum import objects
from magnum.objects.bay import Status as bay_status
from magnum.service import periodic
from magnum.tests import base
from magnum.tests.unit.db import utils

periodic_opts = [
    cfg.BoolOpt('periodic_enable',
                default=True,
                help='Enable periodic tasks.'),
    cfg.IntOpt('periodic_interval_max',
               default=60,
               help='Max interval size between periodic tasks execution in '
                    'seconds.'),
]


class fake_stack(object):
    def __init__(self, **kw):
        for key, val in kw.items():
            setattr(self, key, val)


class PeriodicTestCase(base.TestCase):

    def setUp(self):
        super(PeriodicTestCase, self).setUp()

        ctx = context.make_admin_context()

        bay1 = utils.get_test_bay(id=1, stack_id='11',
                                  status=bay_status.CREATE_IN_PROGRESS)
        bay2 = utils.get_test_bay(id=2, stack_id='22',
                                  status=bay_status.DELETE_IN_PROGRESS)
        bay3 = utils.get_test_bay(id=3, stack_id='33',
                                  status=bay_status.UPDATE_IN_PROGRESS)

        self.bay1 = objects.Bay(ctx, **bay1)
        self.bay2 = objects.Bay(ctx, **bay2)
        self.bay3 = objects.Bay(ctx, **bay3)

    @mock.patch.object(objects.Bay, 'list_all')
    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch.object(dbapi.Connection, 'destroy_bay')
    @mock.patch.object(dbapi.Connection, 'update_bay')
    def test_sync_bay_status_changes(self, mock_db_update, mock_db_destroy,
                                     mock_oscc, mock_bay_list):
        mock_heat_client = mock.MagicMock()
        stack1 = fake_stack(id='11', stack_status=bay_status.CREATE_COMPLETE)
        stack3 = fake_stack(id='33', stack_status=bay_status.UPDATE_COMPLETE)
        mock_heat_client.stacks.list.return_value = [stack1, stack3]
        mock_osc = mock_oscc.return_value
        mock_osc.heat.return_value = mock_heat_client
        mock_bay_list.return_value = [self.bay1, self.bay2, self.bay3]

        mock_keystone_client = mock.MagicMock()
        mock_keystone_client.client.project_id = "fake_project"
        mock_osc.keystone.return_value = mock_keystone_client

        periodic.MagnumPeriodicTasks(CONF).sync_bay_status(None)

        self.assertEqual(self.bay1.status, bay_status.CREATE_COMPLETE)
        mock_db_destroy.assert_called_once_with(self.bay2.uuid)
        self.assertEqual(self.bay3.status, bay_status.UPDATE_COMPLETE)

    @mock.patch.object(objects.Bay, 'list_all')
    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_sync_bay_status_not_changes(self, mock_oscc, mock_bay_list):
        mock_heat_client = mock.MagicMock()
        stack1 = fake_stack(id='11',
                            stack_status=bay_status.CREATE_IN_PROGRESS)
        stack2 = fake_stack(id='22',
                            stack_status=bay_status.DELETE_IN_PROGRESS)
        stack3 = fake_stack(id='33',
                            stack_status=bay_status.UPDATE_IN_PROGRESS)
        mock_heat_client.stacks.list.return_value = [stack1, stack2, stack3]
        mock_osc = mock_oscc.return_value
        mock_osc.heat.return_value = mock_heat_client
        mock_bay_list.return_value = [self.bay1, self.bay2, self.bay3]
        periodic.MagnumPeriodicTasks(CONF).sync_bay_status(None)

        self.assertEqual(self.bay1.status, bay_status.CREATE_IN_PROGRESS)
        self.assertEqual(self.bay2.status, bay_status.DELETE_IN_PROGRESS)
        self.assertEqual(self.bay3.status, bay_status.UPDATE_IN_PROGRESS)

    @mock.patch.object(objects.Bay, 'list_all')
    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch.object(dbapi.Connection, 'destroy_bay')
    @mock.patch.object(dbapi.Connection, 'update_bay')
    def test_sync_bay_status_heat_not_found(self, mock_db_update,
                                            mock_db_destroy, mock_oscc,
                                            mock_bay_list):
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.list.return_value = []
        mock_osc = mock_oscc.return_value
        mock_osc.heat.return_value = mock_heat_client
        mock_bay_list.return_value = [self.bay1, self.bay2, self.bay3]

        mock_keystone_client = mock.MagicMock()
        mock_keystone_client.client.project_id = "fake_project"
        mock_osc.keystone.return_value = mock_keystone_client

        periodic.MagnumPeriodicTasks(CONF).sync_bay_status(None)

        self.assertEqual(self.bay1.status, bay_status.CREATE_FAILED)
        mock_db_destroy.assert_called_once_with(self.bay2.uuid)
        self.assertEqual(self.bay3.status, bay_status.UPDATE_FAILED)
