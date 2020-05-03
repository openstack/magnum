# Copyright 2016 - Fujitsu, Ltd.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

from unittest import mock

from oslo_concurrency import processutils

from magnum.cmd import conductor
from magnum.tests import base


class TestMagnumConductor(base.TestCase):

    @mock.patch('oslo_service.service.launch')
    @mock.patch.object(conductor, 'rpc_service')
    @mock.patch('magnum.common.service.prepare_service')
    def test_conductor(self, mock_prep, mock_rpc, mock_launch):
        conductor.main()

        server = mock_rpc.Service.create.return_value
        launcher = mock_launch.return_value
        mock_prep.assert_called_once_with(mock.ANY)
        mock_rpc.Service.create.assert_called_once_with(
            base.CONF.conductor.topic,
            mock.ANY, mock.ANY, binary='magnum-conductor')
        workers = processutils.get_worker_count()
        mock_launch.assert_called_once_with(base.CONF, server,
                                            workers=workers)
        launcher.wait.assert_called_once_with()

    @mock.patch('oslo_service.service.launch')
    @mock.patch.object(conductor, 'rpc_service')
    @mock.patch('magnum.common.service.prepare_service')
    def test_conductor_config_workers(self, mock_prep, mock_rpc, mock_launch):
        fake_workers = 8
        self.config(workers=fake_workers, group='conductor')
        conductor.main()

        server = mock_rpc.Service.create.return_value
        launcher = mock_launch.return_value
        mock_prep.assert_called_once_with(mock.ANY)
        mock_rpc.Service.create.assert_called_once_with(
            base.CONF.conductor.topic,
            mock.ANY, mock.ANY, binary='magnum-conductor')
        mock_launch.assert_called_once_with(base.CONF, server,
                                            workers=fake_workers)
        launcher.wait.assert_called_once_with()
