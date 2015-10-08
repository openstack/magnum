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
import docker
from docker import errors
import mock
from oslo_config import cfg
import six

from magnum.common import docker_utils
from magnum.common import exception
from magnum.conductor.handlers import docker_conductor
from magnum import objects
from magnum.objects import fields
from magnum.tests import base
from mock import patch

CONF = cfg.CONF


class TestDockerHandler(base.BaseTestCase):
    def setUp(self):
        super(TestDockerHandler, self).setUp()
        self.conductor = docker_conductor.Handler()
        dfc_patcher = mock.patch.object(docker_utils,
                                        'docker_for_container')
        docker_for_container = dfc_patcher.start()
        self.dfc_context_manager = docker_for_container.return_value
        self.mock_docker = mock.MagicMock()
        self.dfc_context_manager.__enter__.return_value = self.mock_docker
        self.addCleanup(dfc_patcher.stop)

    def test_container_create(self):
        mock_container = mock.MagicMock()
        mock_container.name = 'some-name'
        mock_container.uuid = 'some-uuid'
        mock_container.image = 'test_image:some_tag'
        mock_container.command = None
        mock_container.memory = None

        container = self.conductor.container_create(
            None, mock_container)

        utf8_image = self.conductor._encode_utf8(mock_container.image)
        self.mock_docker.pull.assert_called_once_with('test_image',
                                                      tag='some_tag')
        self.mock_docker.inspect_image.assert_called_once_with(utf8_image)
        self.mock_docker.create_container.assert_called_once_with(
            mock_container.image,
            name='some-name',
            hostname='some-uuid',
            command=None,
            mem_limit=None)
        self.assertEqual(fields.ContainerStatus.STOPPED, container.status)

    def test_container_create_with_command(self):
        mock_container = mock.MagicMock()
        mock_container.name = 'some-name'
        mock_container.uuid = 'some-uuid'
        mock_container.image = 'test_image:some_tag'
        mock_container.command = 'env'
        mock_container.memory = None

        container = self.conductor.container_create(
            None, mock_container)

        utf8_image = self.conductor._encode_utf8(mock_container.image)
        self.mock_docker.pull.assert_called_once_with('test_image',
                                                      tag='some_tag')
        self.mock_docker.inspect_image.assert_called_once_with(utf8_image)
        self.mock_docker.create_container.assert_called_once_with(
            mock_container.image,
            name='some-name',
            hostname='some-uuid',
            command='env',
            mem_limit=None)
        self.assertEqual(fields.ContainerStatus.STOPPED, container.status)

    def test_container_create_with_memory(self):
        mock_container = mock.MagicMock()
        mock_container.name = 'some-name'
        mock_container.uuid = 'some-uuid'
        mock_container.image = 'test_image:some_tag'
        mock_container.command = None
        mock_container.memory = '512m'

        container = self.conductor.container_create(
            None, mock_container)

        utf8_image = self.conductor._encode_utf8(mock_container.image)
        self.mock_docker.pull.assert_called_once_with('test_image',
                                                      tag='some_tag')
        self.mock_docker.inspect_image.assert_called_once_with(utf8_image)
        self.mock_docker.create_container.assert_called_once_with(
            mock_container.image,
            name='some-name',
            hostname='some-uuid',
            command=None,
            mem_limit='512m')
        self.assertEqual(fields.ContainerStatus.STOPPED, container.status)

    def test_encode_utf8_unicode(self):
        image = 'some_image:some_tag'
        unicode_image = six.u(image)
        utf8_image = self.conductor._encode_utf8(unicode_image)
        self.assertEqual(image, utf8_image)

    def test_container_create_with_failure(self):
        mock_container = mock.MagicMock()
        mock_container.image = 'test_image:some_tag'
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_docker.pull = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))

            self.assertRaises(exception.ContainerException,
                              self.conductor.container_create,
                              None, mock_container)
            self.mock_docker.pull.assert_called_once_with(
                'test_image',
                tag='some_tag')
            self.assertFalse(self.mock_docker.create_container.called)
            mock_init.assert_called_once_with()
            self.assertEqual(fields.ContainerStatus.ERROR,
                             mock_container.status)

    def test_find_container_by_name_not_found(self):
        mock_docker = mock.MagicMock()
        fake_response = mock.MagicMock()
        fake_response.content = 'not_found'
        fake_response.status_code = 404
        mock_docker.list_instances.side_effect = errors.APIError(
            'not_found', fake_response)
        ret = self.conductor._find_container_by_name(mock_docker, '1')
        self.assertEqual({}, ret)

    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_delete(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_delete(None, mock_container_uuid)
        self.mock_docker.remove_container.assert_called_once_with(
            mock_docker_id)
        mock_find_container.assert_called_once_with(self.mock_docker,
                                                    mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_delete_with_container_not_exist(self,
                                                       mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = {}
        mock_find_container.return_value = mock_docker_id
        res = self.conductor.container_delete(None, mock_container_uuid)
        self.assertIsNone(res)
        self.assertFalse(self.mock_docker.remove_container.called)
        mock_find_container.assert_called_once_with(self.mock_docker,
                                                    mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_delete_with_failure(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_docker.remove_container = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))
            self.assertRaises(exception.ContainerException,
                              self.conductor.container_delete,
                              None, mock_container_uuid)
            self.mock_docker.remove_container.assert_called_once_with(
                mock_docker_id)
            mock_find_container.assert_called_once_with(self.mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_once_with()

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_action(self, mock_find_container, mock_get_by_uuid):
        mock_container = mock.MagicMock()
        mock_get_by_uuid.return_value = mock_container
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor._container_action(None, mock_container_uuid,
                                         'fake-status', 'fake-func')
        self.assertEqual('fake-status', mock_container.status)

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_reboot(self, mock_find_container, mock_get_by_uuid):
        mock_container = mock.MagicMock()
        mock_get_by_uuid.return_value = mock_container
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_reboot(None, mock_container_uuid)
        self.mock_docker.restart.assert_called_once_with(mock_docker_id)
        mock_find_container.assert_called_once_with(self.mock_docker,
                                                    mock_container_uuid)
        self.assertEqual(fields.ContainerStatus.RUNNING, mock_container.status)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_reboot_with_failure(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_docker.restart = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))

            self.assertRaises(exception.ContainerException,
                              self.conductor.container_reboot,
                              None, mock_container_uuid)
            self.mock_docker.restart.assert_called_once_with(mock_docker_id)
            mock_find_container.assert_called_once_with(self.mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_once_with()

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_start(self, mock_find_container, mock_get_by_uuid):
        mock_container = mock.MagicMock()
        mock_get_by_uuid.return_value = mock_container
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_start(None, mock_container_uuid)
        self.mock_docker.start.assert_called_once_with(mock_docker_id)
        mock_find_container.assert_called_once_with(self.mock_docker,
                                                    mock_container_uuid)
        self.assertEqual(fields.ContainerStatus.RUNNING, mock_container.status)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_start_with_failure(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_docker.start = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))

            self.assertRaises(exception.ContainerException,
                              self.conductor.container_start,
                              None, mock_container_uuid)
            self.mock_docker.start.assert_called_once_with(mock_docker_id)
            mock_find_container.assert_called_once_with(self.mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_once_with()

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_stop(self, mock_find_container, mock_get_by_uuid):
        mock_container = mock.MagicMock()
        mock_get_by_uuid.return_value = mock_container
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_stop(None, mock_container_uuid)
        self.mock_docker.stop.assert_called_once_with(mock_docker_id)
        mock_find_container.assert_called_once_with(self.mock_docker,
                                                    mock_container_uuid)
        self.assertEqual(fields.ContainerStatus.STOPPED, mock_container.status)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_stop_with_failure(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_docker.stop = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))

            self.assertRaises(exception.ContainerException,
                              self.conductor.container_stop,
                              None, mock_container_uuid)
            self.mock_docker.stop.assert_called_once_with(mock_docker_id)
            mock_find_container.assert_called_once_with(self.mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_once_with()

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_pause(self, mock_find_container, mock_get_by_uuid):
        mock_container = mock.MagicMock()
        mock_get_by_uuid.return_value = mock_container
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_pause(None, mock_container_uuid)
        self.mock_docker.pause.assert_called_once_with(mock_docker_id)
        mock_find_container.assert_called_once_with(self.mock_docker,
                                                    mock_container_uuid)
        self.assertEqual(fields.ContainerStatus.PAUSED, mock_container.status)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_pause_with_failure(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_docker.pause = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))

            self.assertRaises(exception.ContainerException,
                              self.conductor.container_pause,
                              None, mock_container_uuid)
            self.mock_docker.pause.assert_called_once_with(mock_docker_id)
            mock_find_container.assert_called_once_with(self.mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_once_with()

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_unpause(self, mock_find_container, mock_get_by_uuid):
        mock_container = mock.MagicMock()
        mock_get_by_uuid.return_value = mock_container
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_unpause(None, mock_container_uuid)
        self.mock_docker.unpause.assert_called_once_with(mock_docker_id)
        mock_find_container.assert_called_once_with(self.mock_docker,
                                                    mock_container_uuid)
        self.assertEqual(fields.ContainerStatus.RUNNING, mock_container.status)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_unpause_with_failure(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_docker.unpause = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))

            self.assertRaises(exception.ContainerException,
                              self.conductor.container_unpause,
                              None, mock_container_uuid)
            self.mock_docker.unpause.assert_called_once_with(mock_docker_id)
            mock_find_container.assert_called_once_with(self.mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_once_with()

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_show(self, mock_find_container, mock_get_by_uuid):
        mock_container = mock.MagicMock()
        mock_get_by_uuid.return_value = mock_container
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_show(None, mock_container_uuid)
        self.mock_docker.inspect_container.assert_called_once_with(
            mock_docker_id)
        mock_find_container.assert_called_once_with(self.mock_docker,
                                                    mock_container_uuid)

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_show_with_running_state(self, mock_find_container,
                                               mock_get_by_uuid):
        mock_container = mock.MagicMock()
        mock_get_by_uuid.return_value = mock_container
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        mock_container_detail = {'State': {'Error': '',
                                           'Running': True,
                                           'Paused': False}}
        self.mock_docker.inspect_container.return_value = mock_container_detail
        self.conductor.container_show(None, mock_container_uuid)
        self.assertEqual(fields.ContainerStatus.RUNNING, mock_container.status)

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_show_with_stop_state(self, mock_find_container,
                                            mock_get_by_uuid):
        mock_container = mock.MagicMock()
        mock_get_by_uuid.return_value = mock_container
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        mock_container_detail = {'State': {'Error': '',
                                           'Running': False,
                                           'Paused': False}}
        self.mock_docker.inspect_container.return_value = mock_container_detail
        self.conductor.container_show(None, mock_container_uuid)
        self.assertEqual(fields.ContainerStatus.STOPPED, mock_container.status)

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_show_with_pause_state(self, mock_find_container,
                                             mock_get_by_uuid):
        mock_container = mock.MagicMock()
        mock_get_by_uuid.return_value = mock_container
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        mock_container_detail = {'State': {'Error': '',
                                           'Running': True,
                                           'Paused': True}}
        self.mock_docker.inspect_container.return_value = mock_container_detail
        self.conductor.container_show(None, mock_container_uuid)
        self.assertEqual(fields.ContainerStatus.PAUSED, mock_container.status)

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_show_with_error_status(self, mock_find_container,
                                              mock_get_by_uuid):
        mock_container = mock.MagicMock()
        mock_get_by_uuid.return_value = mock_container
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        mock_container_detail = {'State': {'Error': True,
                                           'Running': False,
                                           'Paused': False}}
        self.mock_docker.inspect_container.return_value = mock_container_detail
        self.conductor.container_show(None, mock_container_uuid)
        self.assertEqual(fields.ContainerStatus.ERROR, mock_container.status)

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_show_with_failure(self, mock_find_container,
                                         mock_get_by_uuid):
        mock_get_by_uuid.return_value = mock.MagicMock()
        mock_container_uuid = 'd545a92d-609a-428f-8edb-1d6b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_docker.inspect_container = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))
            self.assertRaises(exception.ContainerException,
                              self.conductor.container_show,
                              None, mock_container_uuid)
            self.mock_docker.inspect_container.assert_called_once_with(
                mock_docker_id)
            mock_find_container.assert_called_once_with(self.mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_with()

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_show_with_not_found(self, mock_find_container,
                                           mock_get_by_uuid):
        mock_container = mock.MagicMock()
        mock_get_by_uuid.return_value = mock_container
        mock_container_uuid = 'd545a92d-609a-428f-8edb-1d6b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='404 error') as mock_init:
            self.mock_docker.inspect_container = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))
            self.conductor.container_show(None, mock_container_uuid)
            self.mock_docker.inspect_container.assert_called_once_with(
                mock_docker_id)
            mock_find_container.assert_called_once_with(self.mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_once_with()
            self.assertEqual(fields.ContainerStatus.ERROR,
                             mock_container.status)

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_show_with_not_found_from_docker(self,
                                                       mock_find_container,
                                                       mock_get_by_uuid):
        mock_container = mock.MagicMock()
        mock_get_by_uuid.return_value = mock_container
        mock_container_uuid = 'd545a92d-609a-428f-8edb-1d6b02ad20ca1'
        mock_docker_id = {}
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_show(None, mock_container_uuid)
        mock_find_container.assert_called_once_with(self.mock_docker,
                                                    mock_container_uuid)
        self.assertEqual(fields.ContainerStatus.ERROR, mock_container.status)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_exec(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        docker.version = '1.2.2'
        mock_find_container.return_value = mock_docker_id
        mock_create_res = mock.MagicMock()
        self.mock_docker.exec_create.return_value = mock_create_res
        self.conductor.container_exec(None, mock_container_uuid, 'ls')
        self.mock_docker.exec_create.assert_called_once_with(mock_docker_id,
                                                             'ls',
                                                             True, True, False)

        self. mock_docker.exec_start.assert_called_once_with(mock_create_res,
                                                             False, False,
                                                             False)
        mock_find_container.assert_called_once_with(self.mock_docker,
                                                    mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_exec_deprecated(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        docker.version = '0.7.0'
        mock_find_container.return_value = mock_docker_id
        mock_create_res = mock.MagicMock()
        self.mock_docker.exec_create.return_value = mock_create_res
        self.conductor.container_exec(None, mock_container_uuid, 'ls')
        self.mock_docker.execute.assert_called_once_with(mock_docker_id, 'ls')
        mock_find_container.assert_called_once_with(self.mock_docker,
                                                    mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_exec_with_failure(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        docker.version = '1.2.2'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_docker.exec_create = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))
            self.assertRaises(exception.ContainerException,
                              self.conductor.container_exec,
                              None, mock_container_uuid, 'ls')
            self.mock_docker.exec_create.assert_called_once_with(
                mock_docker_id, 'ls', True, True, False)
            mock_find_container.assert_called_once_with(self.mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_once_with()

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_exec_deprecated_with_failure(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        docker.version = '0.7.0'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_docker.execute = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))
            self.assertRaises(exception.ContainerException,
                              self.conductor.container_exec,
                              None, mock_container_uuid, 'ls')
            self.mock_docker.execute.assert_called_once_with(mock_docker_id,
                                                             'ls')
            mock_find_container.assert_called_once_with(self.mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_once_with()

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_logs(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_logs(None, mock_container_uuid)
        self.mock_docker.get_container_logs.assert_called_once_with(
            mock_docker_id)
        mock_find_container.assert_called_once_with(self.mock_docker,
                                                    mock_container_uuid)

    @patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_logs_with_failure(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with patch.object(errors.APIError, '__str__',
                          return_value='hit error') as mock_init:
            self.mock_docker.get_container_logs = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))
            self.assertRaises(exception.ContainerException,
                              self.conductor.container_logs,
                              None, mock_container_uuid)
            self.mock_docker.get_container_logs.assert_called_once_with(
                mock_docker_id)
            mock_find_container.assert_called_once_with(self.mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_once_with()

    def test_container_common_exception(self):
        self.dfc_context_manager.__enter__.side_effect = Exception("So bad")
        for action in ('container_exec', 'container_logs', 'container_show',
                       'container_delete', 'container_create',
                       '_container_action'):
            func = getattr(self.conductor, action)
            self.assertRaises(exception.ContainerException,
                              func, None, None)
