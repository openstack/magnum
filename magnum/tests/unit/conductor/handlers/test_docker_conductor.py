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
import six

from magnum.common import docker_utils
from magnum.common import exception
from magnum.conductor.handlers import docker_conductor
from magnum import objects
from magnum.objects import fields
from magnum.tests import base


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

    @mock.patch.object(docker_utils, 'is_docker_api_version_atleast')
    def _test_container_create(self, container_dict, expected_kwargs,
                               mock_version, expected_image='test_image',
                               expected_tag='some_tag',
                               api_version='1.18'):

        mock_version.return_value = (float(api_version) > 1.18)

        name = container_dict.pop('name')
        mock_container = mock.MagicMock(**container_dict)
        type(mock_container).name = mock.PropertyMock(return_value=name)

        container = self.conductor.container_create(
            None, mock_container)

        utf8_image = self.conductor._encode_utf8(mock_container.image)
        self.mock_docker.inspect_image.assert_called_once_with(utf8_image)
        self.mock_docker.pull.assert_called_once_with(expected_image,
                                                      tag=expected_tag)
        self.mock_docker.create_container.assert_called_once_with(
            mock_container.image, **expected_kwargs)
        self.assertEqual(fields.ContainerStatus.STOPPED, container.status)

    def test_container_create(self):
        container_dict = {
            'name': 'some-name',
            'uuid': 'some-uuid',
            'image': 'test_image:some_tag',
            'command': None,
            'memory': None,
            'environment': None,
        }
        expected_kwargs = {
            'name': 'some-name',
            'hostname': 'some-uuid',
            'command': None,
            'mem_limit': None,
            'environment': None,
        }
        self._test_container_create(container_dict, expected_kwargs)

    def test_container_create_api_1_19(self):
        container_dict = {
            'name': 'some-name',
            'uuid': 'some-uuid',
            'image': 'test_image:some_tag',
            'command': None,
            'memory': '100m',
            'environment': None,
        }
        expected_kwargs = {
            'name': 'some-name',
            'hostname': 'some-uuid',
            'command': None,
            'host_config': {'Memory': 100 * 1024 * 1024},
            'environment': None,
        }
        self._test_container_create(container_dict, expected_kwargs,
                                    api_version='1.19')

    def test_container_create_with_command(self):
        container_dict = {
            'name': 'some-name',
            'uuid': 'some-uuid',
            'image': 'test_image:some_tag',
            'command': 'env',
            'memory': None,
            'environment': None,
        }
        expected_kwargs = {
            'name': 'some-name',
            'hostname': 'some-uuid',
            'command': 'env',
            'mem_limit': None,
            'environment': None,
        }
        self._test_container_create(container_dict, expected_kwargs)

    def test_container_create_with_memory(self):
        container_dict = {
            'name': 'some-name',
            'uuid': 'some-uuid',
            'image': 'test_image:some_tag',
            'command': None,
            'memory': '512m',
            'environment': None,
        }
        expected_kwargs = {
            'name': 'some-name',
            'hostname': 'some-uuid',
            'command': None,
            'mem_limit': '512m',
            'environment': None,
        }
        self._test_container_create(container_dict, expected_kwargs)

    def test_container_create_with_environment(self):
        container_dict = {
            'name': 'some-name',
            'uuid': 'some-uuid',
            'image': 'test_image:some_tag',
            'command': None,
            'memory': '512m',
            'environment': {'key1': 'val1', 'key2': 'val2'},
        }
        expected_kwargs = {
            'name': 'some-name',
            'hostname': 'some-uuid',
            'command': None,
            'mem_limit': '512m',
            'environment': {'key1': 'val1', 'key2': 'val2'},
        }
        self._test_container_create(container_dict, expected_kwargs)

    def test_encode_utf8_unicode(self):
        image = 'some_image:some_tag'
        unicode_image = six.u(image)
        utf8_image = self.conductor._encode_utf8(unicode_image)
        self.assertEqual(unicode_image.encode('utf-8'), utf8_image)

    @mock.patch.object(errors.APIError, '__str__')
    def test_container_create_with_failure(self, mock_init):
        mock_container = mock.MagicMock()
        mock_container.image = 'test_image:some_tag'
        mock_init.return_value = 'hit error'
        self.mock_docker.pull = mock.Mock(
            side_effect=errors.APIError('Error', '', ''))

        self.assertRaises(exception.ContainerException,
                          self.conductor.container_create,
                          None, mock_container)
        self.mock_docker.pull.assert_called_once_with(
            'test_image',
            tag='some_tag')
        self.assertFalse(self.mock_docker.create_container.called)
        mock_init.assert_called_with()
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

    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
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

    @mock.patch.object(errors.APIError, '__str__')
    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_delete_with_failure(self, mock_find_container,
                                           mock_init):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        mock_init.return_value = 'hit error'
        self.mock_docker.remove_container = mock.Mock(
            side_effect=errors.APIError('Error', '', ''))
        self.assertRaises(exception.ContainerException,
                          self.conductor.container_delete,
                          None, mock_container_uuid)
        self.mock_docker.remove_container.assert_called_once_with(
            mock_docker_id)
        mock_find_container.assert_called_once_with(self.mock_docker,
                                                    mock_container_uuid)
        mock_init.assert_called_with()

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_action(self, mock_find_container, mock_get_by_uuid):
        mock_container = mock.MagicMock()
        mock_get_by_uuid.return_value = mock_container
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor._container_action(None, mock_container_uuid,
                                         'fake-status', 'fake-func')
        self.assertEqual('fake-status', mock_container.status)

    def _test_container(self, action, docker_func_name, expected_status,
                        mock_find_container, mock_get_by_uuid):
        mock_container = mock.MagicMock()
        mock_get_by_uuid.return_value = mock_container
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        action_func = getattr(self.conductor, action)
        action_func(None, mock_container_uuid)
        docker_func = getattr(self.mock_docker, docker_func_name)
        docker_func.assert_called_once_with(mock_docker_id)
        mock_find_container.assert_called_once_with(self.mock_docker,
                                                    mock_container_uuid)
        self.assertEqual(expected_status, mock_container.status)

    @mock.patch.object(errors.APIError, '__str__')
    def _test_container_with_failure(
            self, action, docker_func_name, mock_find_container, mock_init):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        mock_init.return_value = 'hit error'
        setattr(self.mock_docker, docker_func_name, mock.Mock(
            side_effect=errors.APIError('Error', '', '')))
        self.assertRaises(exception.ContainerException,
                          getattr(self.conductor, action),
                          None, mock_container_uuid)
        docker_func = getattr(self.mock_docker, docker_func_name)
        docker_func.assert_called_once_with(mock_docker_id)
        mock_find_container.assert_called_once_with(self.mock_docker,
                                                    mock_container_uuid)
        mock_init.assert_called_with()

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_reboot(self, mock_find_container, mock_get_by_uuid):
        self._test_container(
            'container_reboot', 'restart', fields.ContainerStatus.RUNNING,
            mock_find_container, mock_get_by_uuid)

    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_reboot_with_failure(self, mock_find_container):
        self._test_container_with_failure(
            'container_reboot', 'restart', mock_find_container)

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_start(self, mock_find_container, mock_get_by_uuid):
        self._test_container(
            'container_start', 'start', fields.ContainerStatus.RUNNING,
            mock_find_container, mock_get_by_uuid)

    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_start_with_failure(self, mock_find_container):
        self._test_container_with_failure(
            'container_start', 'start', mock_find_container)

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_stop(self, mock_find_container, mock_get_by_uuid):
        self._test_container(
            'container_stop', 'stop', fields.ContainerStatus.STOPPED,
            mock_find_container, mock_get_by_uuid)

    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_stop_with_failure(self, mock_find_container):
        self._test_container_with_failure(
            'container_stop', 'stop', mock_find_container)

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_pause(self, mock_find_container, mock_get_by_uuid):
        self._test_container(
            'container_pause', 'pause', fields.ContainerStatus.PAUSED,
            mock_find_container, mock_get_by_uuid)

    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_pause_with_failure(self, mock_find_container):
        self._test_container_with_failure(
            'container_pause', 'pause', mock_find_container)

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_unpause(self, mock_find_container, mock_get_by_uuid):
        self._test_container(
            'container_unpause', 'unpause', fields.ContainerStatus.RUNNING,
            mock_find_container, mock_get_by_uuid)

    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_unpause_with_failure(self, mock_find_container):
        self._test_container_with_failure(
            'container_unpause', 'unpause', mock_find_container)

    def _test_container_show(
            self, mock_find_container, mock_get_by_uuid, container_detail=None,
            expected_status=None, mock_docker_id='2703ef2b705d'):
        mock_container = mock.MagicMock()
        mock_get_by_uuid.return_value = mock_container
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_find_container.return_value = mock_docker_id
        if container_detail is not None:
            self.mock_docker.inspect_container.return_value = container_detail

        self.conductor.container_show(None, mock_container_uuid)

        if mock_docker_id:
            self.mock_docker.inspect_container.assert_called_once_with(
                mock_docker_id)
        mock_find_container.assert_called_once_with(self.mock_docker,
                                                    mock_container_uuid)
        if expected_status is not None:
            self.assertEqual(expected_status, mock_container.status)

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_show(self, mock_find_container, mock_get_by_uuid):
        self._test_container_show(mock_find_container, mock_get_by_uuid)

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_show_with_running_state(self, mock_find_container,
                                               mock_get_by_uuid):
        mock_container_detail = {'State': {'Error': '',
                                           'Running': True,
                                           'Paused': False}}
        self._test_container_show(
            mock_find_container, mock_get_by_uuid, mock_container_detail,
            fields.ContainerStatus.RUNNING)

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_show_with_stop_state(self, mock_find_container,
                                            mock_get_by_uuid):
        mock_container_detail = {'State': {'Error': '',
                                           'Running': False,
                                           'Paused': False}}
        self._test_container_show(
            mock_find_container, mock_get_by_uuid, mock_container_detail,
            fields.ContainerStatus.STOPPED)

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_show_with_pause_state(self, mock_find_container,
                                             mock_get_by_uuid):
        mock_container_detail = {'State': {'Error': '',
                                           'Running': True,
                                           'Paused': True}}
        self._test_container_show(
            mock_find_container, mock_get_by_uuid, mock_container_detail,
            fields.ContainerStatus.PAUSED)

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_show_with_error_status(self, mock_find_container,
                                              mock_get_by_uuid):
        mock_container_detail = {'State': {'Error': True,
                                           'Running': False,
                                           'Paused': False}}
        self._test_container_show(
            mock_find_container, mock_get_by_uuid, mock_container_detail,
            fields.ContainerStatus.ERROR)

    def _test_container_show_with_failure(
            self, mock_find_container, mock_get_by_uuid, error,
            assert_raise=True, expected_status=None):
        mock_container = mock.MagicMock()
        mock_get_by_uuid.return_value = mock_container
        mock_container_uuid = 'd545a92d-609a-428f-8edb-1d6b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        with mock.patch.object(errors.APIError, '__str__',
                               return_value=error) as mock_init:
            self.mock_docker.inspect_container = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))

            if assert_raise:
                self.assertRaises(exception.ContainerException,
                                  self.conductor.container_show,
                                  None, mock_container_uuid)
            else:
                self.conductor.container_show(None, mock_container_uuid)

            self.mock_docker.inspect_container.assert_called_once_with(
                mock_docker_id)
            mock_find_container.assert_called_once_with(self.mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_with()
            if expected_status is not None:
                self.assertEqual(expected_status, mock_container.status)

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_show_with_failure(self, mock_find_container,
                                         mock_get_by_uuid):
        self._test_container_show_with_failure(
            mock_find_container, mock_get_by_uuid, error='hit error')

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_show_with_not_found(self, mock_find_container,
                                           mock_get_by_uuid):
        self._test_container_show_with_failure(
            mock_find_container, mock_get_by_uuid, error='404 error',
            assert_raise=False, expected_status=fields.ContainerStatus.ERROR)

    @mock.patch.object(objects.Container, 'get_by_uuid')
    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_show_with_not_found_from_docker(self,
                                                       mock_find_container,
                                                       mock_get_by_uuid):
        self._test_container_show(
            mock_find_container, mock_get_by_uuid, mock_docker_id={},
            expected_status=fields.ContainerStatus.ERROR)

    def _test_container_exec(self, mock_find_container, docker_version='1.2.2',
                             deprecated=False):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        docker.version = docker_version
        mock_find_container.return_value = mock_docker_id
        mock_create_res = mock.MagicMock()
        self.mock_docker.exec_create.return_value = mock_create_res
        self.conductor.container_exec(None, mock_container_uuid, 'ls')
        if deprecated:
            self.mock_docker.execute.assert_called_once_with(
                mock_docker_id, 'ls')
        else:
            self.mock_docker.exec_create.assert_called_once_with(
                mock_docker_id, 'ls', True, True, False)
            self. mock_docker.exec_start.assert_called_once_with(
                mock_create_res, False, False, False)
        mock_find_container.assert_called_once_with(self.mock_docker,
                                                    mock_container_uuid)

    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_exec(self, mock_find_container):
        self._test_container_exec(mock_find_container)

    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_exec_deprecated(self, mock_find_container):
        self._test_container_exec(
            mock_find_container, docker_version='0.7.0', deprecated=True)

    def _test_container_exec_with_failure(
            self, mock_find_container, docker_version='1.2.2',
            deprecated=False):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        docker.version = docker_version
        mock_find_container.return_value = mock_docker_id
        with mock.patch.object(errors.APIError, '__str__',
                               return_value='hit error') as mock_init:
            if deprecated:
                self.mock_docker.execute = mock.Mock(
                    side_effect=errors.APIError('Error', '', ''))
            else:
                self.mock_docker.exec_create = mock.Mock(
                    side_effect=errors.APIError('Error', '', ''))
            self.assertRaises(exception.ContainerException,
                              self.conductor.container_exec,
                              None, mock_container_uuid, 'ls')
            if deprecated:
                self.mock_docker.execute.assert_called_once_with(
                    mock_docker_id, 'ls')
            else:
                self.mock_docker.exec_create.assert_called_once_with(
                    mock_docker_id, 'ls', True, True, False)
            mock_find_container.assert_called_once_with(self.mock_docker,
                                                        mock_container_uuid)
            mock_init.assert_called_with()

    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_exec_with_failure(self, mock_find_container):
        self._test_container_exec_with_failure(mock_find_container)

    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_exec_deprecated_with_failure(self, mock_find_container):
        self._test_container_exec_with_failure(
            mock_find_container, docker_version='0.7.0', deprecated=True)

    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_logs(self, mock_find_container):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        self.conductor.container_logs(None, mock_container_uuid)
        self.mock_docker.logs.assert_called_once_with(
            mock_docker_id)
        mock_find_container.assert_called_once_with(self.mock_docker,
                                                    mock_container_uuid)

    @mock.patch.object(errors.APIError, '__str__')
    @mock.patch.object(docker_conductor.Handler, '_find_container_by_name')
    def test_container_logs_with_failure(self, mock_find_container, mock_init):
        mock_container_uuid = 'd545a92d-609a-428f-8edb-16b02ad20ca1'
        mock_docker_id = '2703ef2b705d'
        mock_find_container.return_value = mock_docker_id
        mock_init.return_value = 'hit error'
        self.mock_docker.logs = mock.Mock(
            side_effect=errors.APIError('Error', '', ''))
        self.assertRaises(exception.ContainerException,
                          self.conductor.container_logs,
                          None, mock_container_uuid)
        self.mock_docker.logs.assert_called_once_with(
            mock_docker_id)
        mock_find_container.assert_called_once_with(self.mock_docker,
                                                    mock_container_uuid)
        mock_init.assert_called_with()

    def test_container_common_exception(self):
        self.dfc_context_manager.__enter__.side_effect = Exception("So bad")
        for action in ('container_exec', 'container_logs', 'container_show',
                       'container_delete', 'container_create',
                       '_container_action'):
            func = getattr(self.conductor, action)
            self.assertRaises(exception.ContainerException,
                              func, None, None)
