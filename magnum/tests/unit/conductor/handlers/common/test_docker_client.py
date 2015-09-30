# Copyright 2015 Rackspace, inc.
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

from docker import client as docker_py_client
import mock

from magnum.conductor.handlers.common import docker_client
from magnum.tests import base


class DockerClientTestCase(base.BaseTestCase):
    def test_docker_client_init(self):
        client = docker_client.DockerHTTPClient()

        self.assertEqual(docker_client.DEFAULT_DOCKER_REMOTE_API_VERSION,
                         client.api_version)
        self.assertEqual(docker_client.DEFAULT_DOCKER_TIMEOUT,
                         client.timeout)

    def test_docker_client_init_timeout(self):
        expected_timeout = 300
        client = docker_client.DockerHTTPClient(timeout=expected_timeout)

        self.assertEqual(docker_client.DEFAULT_DOCKER_REMOTE_API_VERSION,
                         client.api_version)
        self.assertEqual(expected_timeout, client.timeout)

    def test_docker_client_init_url(self):
        expected_url = 'http://127.0.0.1:2375'
        client = docker_client.DockerHTTPClient(url=expected_url)

        self.assertEqual(expected_url,
                         client.base_url)
        self.assertEqual(docker_client.DEFAULT_DOCKER_REMOTE_API_VERSION,
                         client.api_version)
        self.assertEqual(docker_client.DEFAULT_DOCKER_TIMEOUT,
                         client.timeout)

    def test_docker_client_init_version(self):
        expected_version = '1.16'
        client = docker_client.DockerHTTPClient(ver=expected_version)

        self.assertEqual(expected_version,
                         client.api_version)
        self.assertEqual(docker_client.DEFAULT_DOCKER_TIMEOUT,
                         client.timeout)

    @mock.patch.object(docker_py_client.Client, 'inspect_container')
    @mock.patch.object(docker_py_client.Client, 'containers')
    def test_list_instances(self, mock_containers, mock_inspect):
        client = docker_client.DockerHTTPClient()

        containers = [dict(Id=x) for x in range(0, 3)]
        inspect_results = [dict(Config=dict(Hostname=x)) for x in range(0, 3)]

        mock_containers.return_value = containers
        mock_inspect.side_effect = inspect_results

        instances = client.list_instances()

        self.assertEqual([0, 1, 2], instances)
        mock_containers.assert_called_once_with(all=True)
        mock_inspect.assert_has_calls([mock.call(x) for x in range(0, 3)])

    @mock.patch.object(docker_py_client.Client, 'inspect_container')
    @mock.patch.object(docker_py_client.Client, 'containers')
    def test_list_instances_inspect(self, mock_containers, mock_inspect):
        client = docker_client.DockerHTTPClient()

        containers = [dict(Id=x) for x in range(0, 3)]
        inspect_results = [dict(Config=dict(Hostname=x)) for x in range(0, 3)]

        mock_containers.return_value = containers
        mock_inspect.side_effect = inspect_results

        instances = client.list_instances(inspect=True)

        self.assertEqual(inspect_results, instances)
        mock_containers.assert_called_once_with(all=True)
        mock_inspect.assert_has_calls([mock.call(x) for x in range(0, 3)])

    @mock.patch.object(docker_py_client.Client, '_raise_for_status')
    @mock.patch.object(docker_py_client.Client, '_post')
    @mock.patch.object(docker_py_client.Client, '_url')
    def test_pause(self, mock_url, mock_post, mock_raise_for_status):
        client = docker_client.DockerHTTPClient()

        client.pause('someid')

        mock_url.assert_called_once_with('/containers/someid/pause')
        mock_post.assert_called_once_with(mock_url.return_value)
        mock_raise_for_status.assert_called_once_with(
            mock_post.return_value)

    @mock.patch.object(docker_py_client.Client, '_raise_for_status')
    @mock.patch.object(docker_py_client.Client, '_post')
    @mock.patch.object(docker_py_client.Client, '_url')
    def test_pause_container_dict(self, mock_url, mock_post,
                                  mock_raise_for_status):
        client = docker_client.DockerHTTPClient()

        client.pause(dict(Id='someid'))

        mock_url.assert_called_once_with('/containers/someid/pause')
        mock_post.assert_called_once_with(mock_url.return_value)
        mock_raise_for_status.assert_called_once_with(
            mock_post.return_value)

    @mock.patch.object(docker_py_client.Client, '_raise_for_status')
    @mock.patch.object(docker_py_client.Client, '_post')
    @mock.patch.object(docker_py_client.Client, '_url')
    def test_unpause(self, mock_url, mock_post, mock_raise_for_status):
        client = docker_client.DockerHTTPClient()

        client.unpause('someid')

        mock_url.assert_called_once_with('/containers/someid/unpause')
        mock_post.assert_called_once_with(mock_url.return_value)
        mock_raise_for_status.assert_called_once_with(
            mock_post.return_value)

    @mock.patch.object(docker_py_client.Client, '_raise_for_status')
    @mock.patch.object(docker_py_client.Client, '_post')
    @mock.patch.object(docker_py_client.Client, '_url')
    def test_unpause_container_dict(self, mock_url, mock_post,
                                    mock_raise_for_status):
        client = docker_client.DockerHTTPClient()

        client.unpause(dict(Id='someid'))

        mock_url.assert_called_once_with('/containers/someid/unpause')
        mock_post.assert_called_once_with(mock_url.return_value)
        mock_raise_for_status.assert_called_once_with(
            mock_post.return_value)

    @mock.patch.object(docker_py_client.Client, 'logs')
    def test_get_container_logs(self, mock_logs):
        client = docker_client.DockerHTTPClient()

        client.get_container_logs('someid')

        mock_logs.assert_called_once_with('someid')
