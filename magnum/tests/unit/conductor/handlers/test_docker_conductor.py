# Copyright 2015 Rackspace  All rights reserved.
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
from docker import errors
import mock

from magnum.common import exception
from magnum.conductor.handlers import docker_conductor
from magnum.tests import base
from mock import patch


class TestDockerConductor(base.BaseTestCase):
    def setUp(self):
        super(TestDockerConductor, self).setUp()
        with mock.patch.object(docker_conductor,
                               'docker_client') as mock_client:
            mock_client.DockerHTTPClient.return_value = mock.MagicMock()
            self.conductor = docker_conductor.Handler()
            self.mock_client = self.conductor.docker

    def test_container_create(self):
        mock_container = mock.MagicMock()
        mock_container.image_id = 'test_image:some_tag'
        mock_container.command = None

        self.conductor.container_create(None, 'some-name', 'some-uuid',
                                        mock_container)

        utf8_image_id = self.conductor._encode_utf8(mock_container.image_id)
        self.mock_client.pull.assert_called_once_with('test_image',
                                                      tag='some_tag')
        self.mock_client.inspect_image.assert_called_once_with(utf8_image_id)
        self.mock_client.create_container.assert_called_once_with(
                                          mock_container.image_id,
                                          name='some-name',
                                          hostname='some-uuid',
                                          command=None)

    def test_container_create_with_command(self):
        mock_container = mock.MagicMock()
        mock_container.image_id = 'test_image:some_tag'
        mock_container.command = 'env'

        self.conductor.container_create(None, 'some-name', 'some-uuid',
                                        mock_container)

        utf8_image_id = self.conductor._encode_utf8(mock_container.image_id)
        self.mock_client.pull.assert_called_once_with('test_image',
                                                      tag='some_tag')
        self.mock_client.inspect_image.assert_called_once_with(utf8_image_id)
        self.mock_client.create_container.assert_called_once_with(
                                          mock_container.image_id,
                                          name='some-name',
                                          hostname='some-uuid',
                                          command='env')

    def test_container_create_with_failure(self):
        mock_container = mock.MagicMock()
        mock_container.image_id = 'test_image:some_tag'
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_client.pull = mock.Mock(side_effect=
                                  errors.APIError('Error', '', ''))

            self.assertRaises(exception.ContainerException,
                              self.conductor.container_create,
                              None, 'some-name', 'some-uuid', mock_container)
            self.mock_client.pull.assert_called_once_with(
                                          'test_image',
                                          tag='some_tag')
            self.assertFalse(self.mock_client.create_container.called)
            mock_init.assert_called_once_with()

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_delete(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_delete(None, mock_container_uuid)
        self.mock_client.remove_container.assert_called_once_with(
                                                   mock_docker_id)
        mock_find_container.assert_called_once_with(mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_delete_with_container_not_exist(self,
                                                       mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = {}
        mock_find_container.return_value = mock_docker_id
        res = self.conductor.container_delete(None, mock_container_uuid)
        self.assertIsNone(res)
        self.assertFalse(self.mock_client.remove_container.called)
        mock_find_container.assert_called_once_with(mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_delete_with_failure(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_client.remove_container = mock.Mock(side_effect=
                                  errors.APIError('Error', '', ''))
            self.assertRaises(exception.ContainerException,
                              self.conductor.container_delete,
                              None, mock_container_uuid)
            self.mock_client.remove_container.assert_called_once_with(
                                                       mock_docker_id)
            mock_find_container.assert_called_once_with(mock_container_uuid)
            mock_init.assert_called_once_with()

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_reboot(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_reboot(None, mock_container_uuid)
        self.mock_client.restart.assert_called_once_with(mock_docker_id)
        mock_find_container.assert_called_once_with(mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_reboot_with_failure(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_client.restart = mock.Mock(side_effect=
                                  errors.APIError('Error', '', ''))

            self.assertRaises(exception.ContainerException,
                              self.conductor.container_reboot,
                              None, mock_container_uuid)
            self.mock_client.restart.assert_called_once_with(mock_docker_id)
            mock_find_container.assert_called_once_with(mock_container_uuid)
            mock_init.assert_called_once_with()

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_start(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_start(None, mock_container_uuid)
        self.mock_client.start.assert_called_once_with(mock_docker_id)
        mock_find_container.assert_called_once_with(mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_start_with_failure(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_client.start = mock.Mock(side_effect=
                                  errors.APIError('Error', '', ''))

            self.assertRaises(exception.ContainerException,
                              self.conductor.container_start,
                              None, mock_container_uuid)
            self.mock_client.start.assert_called_once_with(mock_docker_id)
            mock_find_container.assert_called_once_with(mock_container_uuid)
            mock_init.assert_called_once_with()

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_stop(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_stop(None, mock_container_uuid)
        self.mock_client.stop.assert_called_once_with(mock_docker_id)
        mock_find_container.assert_called_once_with(mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_stop_with_failure(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_client.stop = mock.Mock(side_effect=
                                  errors.APIError('Error', '', ''))

            self.assertRaises(exception.ContainerException,
                              self.conductor.container_stop,
                              None, mock_container_uuid)
            self.mock_client.stop.assert_called_once_with(mock_docker_id)
            mock_find_container.assert_called_once_with(mock_container_uuid)
            mock_init.assert_called_once_with()

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_pause(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_pause(None, mock_container_uuid)
        self.mock_client.pause.assert_called_once_with(mock_docker_id)
        mock_find_container.assert_called_once_with(mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_pause_with_failure(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_client.pause = mock.Mock(side_effect=
                                  errors.APIError('Error', '', ''))

            self.assertRaises(exception.ContainerException,
                              self.conductor.container_pause,
                              None, mock_container_uuid)
            self.mock_client.pause.assert_called_once_with(mock_docker_id)
            mock_find_container.assert_called_once_with(mock_container_uuid)
            mock_init.assert_called_once_with()

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_unpause(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_unpause(None, mock_container_uuid)
        self.mock_client.unpause.assert_called_once_with(mock_docker_id)
        mock_find_container.assert_called_once_with(mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_unpause_with_failure(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_client.unpause = mock.Mock(side_effect=
                                  errors.APIError('Error', '', ''))

            self.assertRaises(exception.ContainerException,
                              self.conductor.container_unpause,
                              None, mock_container_uuid)
            self.mock_client.unpause.assert_called_once_with(mock_docker_id)
            mock_find_container.assert_called_once_with(mock_container_uuid)
            mock_init.assert_called_once_with()

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_show(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_show(None, mock_container_uuid)
        self.mock_client.inspect_container.assert_called_once_with(
                                                    mock_docker_id)
        mock_find_container.assert_called_once_with(mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_show_with_failure(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_client.inspect_container = mock.Mock(side_effect=
                                  errors.APIError('Error', '', ''))
            self.assertRaises(exception.ContainerException,
                              self.conductor.container_show,
                              None, mock_container_uuid)
            self.mock_client.inspect_container.assert_called_once_with(
                                                        mock_docker_id)
            mock_find_container.assert_called_once_with(mock_container_uuid)
            mock_init.assert_called_once_with()

    def test_container_list(self):
        self.conductor.container_list(None)
        self.mock_client.containers.assert_called_once_with()

    def test_container_list_with_failure(self):
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_client.containers = mock.Mock(side_effect=
                                  errors.APIError('Error', '', ''))
            self.assertRaises(exception.ContainerException,
                              self.conductor.container_list,
                              None)
            self.mock_client.containers.assert_called_once_with()
            mock_init.assert_called_once_with()

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_execute(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_execute(None, mock_container_uuid, 'ls')
        self.mock_client.execute.assert_called_once_with(
                                                    mock_docker_id, 'ls')
        mock_find_container.assert_called_once_with(mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_execute_with_failure(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_client.execute = mock.Mock(side_effect=
                                  errors.APIError('Error', '', ''))
            self.assertRaises(exception.ContainerException,
                              self.conductor.container_execute,
                              None, mock_container_uuid, 'ls')
            self.mock_client.execute.assert_called_once_with(
                                                        mock_docker_id, 'ls')
            mock_find_container.assert_called_once_with(mock_container_uuid)
            mock_init.assert_called_once_with()

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_logs(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_logs(None, mock_container_uuid)
        self.mock_client.get_container_logs.assert_called_once_with(
                                                    mock_docker_id)
        mock_find_container.assert_called_once_with(mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_logs_with_failure(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_client.get_container_logs = mock.Mock(side_effect=
                                  errors.APIError('Error', '', ''))
            self.assertRaises(exception.ContainerException,
                              self.conductor.container_logs,
                              None, mock_container_uuid)
            self.mock_client.get_container_logs.assert_called_once_with(
                                                        mock_docker_id)
            mock_find_container.assert_called_once_with(mock_container_uuid)
            mock_init.assert_called_once_with()
