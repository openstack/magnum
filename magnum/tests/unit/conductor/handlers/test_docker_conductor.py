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
from oslo_config import cfg

from magnum.common import exception
from magnum.conductor.handlers import docker_conductor
from magnum.tests import base
from mock import patch

CONF = cfg.CONF


class TestDockerConductor(base.BaseTestCase):
    def setUp(self):
        super(TestDockerConductor, self).setUp()
        self.conductor = docker_conductor.Handler()

    @mock.patch.object(docker_conductor, 'docker_client')
    def test_docker_for_bay(self, mock_docker_client):
        mock_docker = mock.MagicMock()
        mock_docker_client.DockerHTTPClient.return_value = mock_docker
        mock_bay = mock.MagicMock()
        mock_bay.api_address = '1.1.1.1'

        actual_docker = self.conductor._docker_for_bay(mock_bay)

        self.assertEqual(mock_docker, actual_docker)

        args = ('tcp://1.1.1.1:2376', CONF.docker.docker_remote_api_version)
        mock_docker_client.DockerHTTPClient.assert_called_once_with(*args)

    @mock.patch.object(docker_conductor, 'docker_client')
    @mock.patch.object(docker_conductor.objects.Bay, 'get_by_uuid')
    def test_get_docker_client(self, mock_bay_get_by_uuid,
                               mock_docker_client):
        mock_docker = mock.MagicMock()
        mock_docker_client.DockerHTTPClient.return_value = mock_docker

        mock_bay = mock.MagicMock()
        mock_bay.api_address = '1.1.1.1'
        mock_bay_get_by_uuid.return_value = mock_bay

        mock_container = mock.MagicMock()
        mock_container.bay_uuid = '9fb6c41e-a7e4-48b8-97c4-702b26034b8e'

        actual_docker = self.conductor.get_docker_client(
                                                mock.sentinel.context,
                                                mock_container)

        self.assertEqual(mock_docker, actual_docker)

        args = ('tcp://1.1.1.1:2376', CONF.docker.docker_remote_api_version)
        mock_bay_get_by_uuid.assert_called_once_with(mock.sentinel.context,
                                                     mock_container.bay_uuid)
        mock_docker_client.DockerHTTPClient.assert_called_once_with(*args)

    @mock.patch.object(docker_conductor, 'docker_client')
    @mock.patch.object(docker_conductor.objects.Bay, 'get_by_uuid')
    @mock.patch.object(docker_conductor.objects.Container, 'get_by_uuid')
    def test_get_docker_client_container_uuid(self,
                                              mock_container_get_by_uuid,
                                              mock_bay_get_by_uuid,
                                              mock_docker_client):
        mock_docker = mock.MagicMock()
        mock_docker_client.DockerHTTPClient.return_value = mock_docker

        mock_bay = mock.MagicMock()
        mock_bay.api_address = '1.1.1.1'
        mock_bay_get_by_uuid.return_value = mock_bay

        mock_container = mock.MagicMock()
        mock_container.uuid = '8e48ffb1-754d-4f21-bdd0-1a39bf796389'
        mock_container.bay_uuid = '9fb6c41e-a7e4-48b8-97c4-702b26034b8e'
        mock_container_get_by_uuid.return_value = mock_container

        actual_docker = self.conductor.get_docker_client(mock.sentinel.context,
                                                         mock_container.uuid)

        self.assertEqual(mock_docker, actual_docker)

        args = ('tcp://1.1.1.1:2376', CONF.docker.docker_remote_api_version)
        mock_container_get_by_uuid.assert_called_once_with(
                                                 mock.sentinel.context,
                                                 mock_container.uuid)
        mock_bay_get_by_uuid.assert_called_once_with(mock.sentinel.context,
                                                     mock_container.bay_uuid)
        mock_docker_client.DockerHTTPClient.assert_called_once_with(*args)

    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_create(self, mock_get_docker_client):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker

        mock_container = mock.MagicMock()
        mock_container.image_id = 'test_image:some_tag'
        mock_container.command = None

        self.conductor.container_create(None, 'some-name', 'some-uuid',
                                        mock_container)

        utf8_image_id = self.conductor._encode_utf8(mock_container.image_id)
        mock_docker.pull.assert_called_once_with('test_image',
                                                      tag='some_tag')
        mock_docker.inspect_image.assert_called_once_with(utf8_image_id)
        mock_docker.create_container.assert_called_once_with(
                                          mock_container.image_id,
                                          name='some-name',
                                          hostname='some-uuid',
                                          command=None)

    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_create_with_command(self, mock_get_docker_client):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker

        mock_container = mock.MagicMock()
        mock_container.image_id = 'test_image:some_tag'
        mock_container.command = 'env'

        self.conductor.container_create(None, 'some-name', 'some-uuid',
                                        mock_container)

        utf8_image_id = self.conductor._encode_utf8(mock_container.image_id)
        mock_docker.pull.assert_called_once_with('test_image',
                                                      tag='some_tag')
        mock_docker.inspect_image.assert_called_once_with(utf8_image_id)
        mock_docker.create_container.assert_called_once_with(
                                          mock_container.image_id,
                                          name='some-name',
                                          hostname='some-uuid',
                                          command='env')

    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_create_with_failure(self, mock_get_docker_client):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker
        mock_container = mock.MagicMock()
        mock_container.image_id = 'test_image:some_tag'
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            mock_docker.pull = mock.Mock(side_effect=
                                  errors.APIError('Error', '', ''))

            self.assertRaises(exception.ContainerException,
                              self.conductor.container_create,
                              None, 'some-name', 'some-uuid', mock_container)
            mock_docker.pull.assert_called_once_with(
                                          'test_image',
                                          tag='some_tag')
            self.assertFalse(mock_docker.create_container.called)
            mock_init.assert_called_once_with()

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_delete(self, mock_get_docker_client,
                              mock_find_container):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_delete(None, mock_container_uuid)
        mock_docker.remove_container.assert_called_once_with(
                                                   mock_docker_id)
        mock_find_container.assert_called_once_with(mock_docker,
                                                    mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_delete_with_container_not_exist(self,
                                        mock_get_docker_client,
                                        mock_find_container):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = {}
        mock_find_container.return_value = mock_docker_id
        res = self.conductor.container_delete(None, mock_container_uuid)
        self.assertIsNone(res)
        self.assertFalse(mock_docker.remove_container.called)
        mock_find_container.assert_called_once_with(mock_docker,
                                                    mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_delete_with_failure(self,
                                        mock_get_docker_client,
                                        mock_find_container):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            mock_docker.remove_container = mock.Mock(side_effect=
                                  errors.APIError('Error', '', ''))
            self.assertRaises(exception.ContainerException,
                              self.conductor.container_delete,
                              None, mock_container_uuid)
            mock_docker.remove_container.assert_called_once_with(
                                                       mock_docker_id)
            mock_find_container.assert_called_once_with(mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_once_with()

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_reboot(self, mock_get_docker_client,
                              mock_find_container):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_reboot(None, mock_container_uuid)
        mock_docker.restart.assert_called_once_with(mock_docker_id)
        mock_find_container.assert_called_once_with(mock_docker,
                                                    mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_reboot_with_failure(self,
                                           mock_get_docker_client,
                                           mock_find_container):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            mock_docker.restart = mock.Mock(side_effect=
                                  errors.APIError('Error', '', ''))

            self.assertRaises(exception.ContainerException,
                              self.conductor.container_reboot,
                              None, mock_container_uuid)
            mock_docker.restart.assert_called_once_with(mock_docker_id)
            mock_find_container.assert_called_once_with(mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_once_with()

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_start(self, mock_get_docker_client,
                             mock_find_container):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_start(None, mock_container_uuid)
        mock_docker.start.assert_called_once_with(mock_docker_id)
        mock_find_container.assert_called_once_with(mock_docker,
                                                    mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_start_with_failure(self,
                                          mock_get_docker_client,
                                          mock_find_container):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            mock_docker.start = mock.Mock(side_effect=
                                  errors.APIError('Error', '', ''))

            self.assertRaises(exception.ContainerException,
                              self.conductor.container_start,
                              None, mock_container_uuid)
            mock_docker.start.assert_called_once_with(mock_docker_id)
            mock_find_container.assert_called_once_with(mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_once_with()

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_stop(self, mock_get_docker_client,
                            mock_find_container):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_stop(None, mock_container_uuid)
        mock_docker.stop.assert_called_once_with(mock_docker_id)
        mock_find_container.assert_called_once_with(mock_docker,
                                                    mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_stop_with_failure(self, mock_get_docker_client,
                                         mock_find_container):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            mock_docker.stop = mock.Mock(side_effect=
                                  errors.APIError('Error', '', ''))

            self.assertRaises(exception.ContainerException,
                              self.conductor.container_stop,
                              None, mock_container_uuid)
            mock_docker.stop.assert_called_once_with(mock_docker_id)
            mock_find_container.assert_called_once_with(mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_once_with()

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_pause(self, mock_get_docker_client,
                             mock_find_container):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_pause(None, mock_container_uuid)
        mock_docker.pause.assert_called_once_with(mock_docker_id)
        mock_find_container.assert_called_once_with(mock_docker,
                                                    mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_pause_with_failure(self, mock_get_docker_client,
                                          mock_find_container):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            mock_docker.pause = mock.Mock(side_effect=
                                  errors.APIError('Error', '', ''))

            self.assertRaises(exception.ContainerException,
                              self.conductor.container_pause,
                              None, mock_container_uuid)
            mock_docker.pause.assert_called_once_with(mock_docker_id)
            mock_find_container.assert_called_once_with(mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_once_with()

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_unpause(self, mock_get_docker_client,
                               mock_find_container):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_unpause(None, mock_container_uuid)
        mock_docker.unpause.assert_called_once_with(mock_docker_id)
        mock_find_container.assert_called_once_with(mock_docker,
                                                    mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_unpause_with_failure(self,
                                            mock_get_docker_client,
                                            mock_find_container):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            mock_docker.unpause = mock.Mock(side_effect=
                                  errors.APIError('Error', '', ''))

            self.assertRaises(exception.ContainerException,
                              self.conductor.container_unpause,
                              None, mock_container_uuid)
            mock_docker.unpause.assert_called_once_with(mock_docker_id)
            mock_find_container.assert_called_once_with(mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_once_with()

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_show(self, mock_get_docker_client,
                            mock_find_container):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_show(None, mock_container_uuid)
        mock_docker.inspect_container.assert_called_once_with(
                                                    mock_docker_id)
        mock_find_container.assert_called_once_with(mock_docker,
                                                    mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_show_with_failure(self, mock_get_docker_client,
                                         mock_find_container):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            mock_docker.inspect_container = mock.Mock(side_effect=
                                  errors.APIError('Error', '', ''))
            self.assertRaises(exception.ContainerException,
                              self.conductor.container_show,
                              None, mock_container_uuid)
            mock_docker.inspect_container.assert_called_once_with(
                                                        mock_docker_id)
            mock_find_container.assert_called_once_with(mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_once_with()

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_execute(self, mock_get_docker_client,
                               mock_find_container):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_execute(None, mock_container_uuid, 'ls')
        mock_docker.execute.assert_called_once_with(mock_docker_id, 'ls')
        mock_find_container.assert_called_once_with(mock_docker,
                                                    mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_execute_with_failure(self,
                                            mock_get_docker_client,
                                            mock_find_container):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            mock_docker.execute = mock.Mock(side_effect=
                                  errors.APIError('Error', '', ''))
            self.assertRaises(exception.ContainerException,
                              self.conductor.container_execute,
                              None, mock_container_uuid, 'ls')
            mock_docker.execute.assert_called_once_with(mock_docker_id, 'ls')
            mock_find_container.assert_called_once_with(mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_once_with()

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_logs(self, mock_get_docker_client,
                            mock_find_container):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_logs(None, mock_container_uuid)
        mock_docker.get_container_logs.assert_called_once_with(
                                                    mock_docker_id)
        mock_find_container.assert_called_once_with(mock_docker,
                                                    mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    @mock.patch.object(docker_conductor.Handler, 'get_docker_client')
    def test_container_logs_with_failure(self, mock_get_docker_client,
                                         mock_find_container):
        mock_docker = mock.MagicMock()
        mock_get_docker_client.return_value = mock_docker
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            mock_docker.get_container_logs = mock.Mock(side_effect=
                                  errors.APIError('Error', '', ''))
            self.assertRaises(exception.ContainerException,
                              self.conductor.container_logs,
                              None, mock_container_uuid)
            mock_docker.get_container_logs.assert_called_once_with(
                                                        mock_docker_id)
            mock_find_container.assert_called_once_with(mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_once_with()
