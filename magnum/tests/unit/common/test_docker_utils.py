# Copyright 2015 Huawei Technologies Co.,LTD.
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
from unittest import mock

from magnum.common import docker_utils
import magnum.conf
from magnum.tests import base


CONF = magnum.conf.CONF


class TestDockerUtils(base.BaseTestCase):

    def test_is_docker_api_version_atleast(self):

        def fake_version():
            return {'ApiVersion': '1.18'}

        docker_client = mock.MagicMock()
        docker_client.version.side_effect = fake_version
        res = docker_utils.is_docker_api_version_atleast(docker_client, '1.21')
        self.assertFalse(res)


class DockerClientTestCase(base.BaseTestCase):
    def test_docker_client_init(self):
        client = docker_utils.DockerHTTPClient()

        self.assertEqual(CONF.docker.docker_remote_api_version,
                         client.api_version)
        self.assertEqual(CONF.docker.default_timeout,
                         client.timeout)

    def test_docker_client_init_timeout(self):
        expected_timeout = 300
        client = docker_utils.DockerHTTPClient(timeout=expected_timeout)

        self.assertEqual(CONF.docker.docker_remote_api_version,
                         client.api_version)
        self.assertEqual(expected_timeout, client.timeout)

    def test_docker_client_init_url(self):
        expected_url = 'http://127.0.0.1:2375'
        client = docker_utils.DockerHTTPClient(url=expected_url)

        self.assertEqual(expected_url,
                         client.base_url)
        self.assertEqual(CONF.docker.docker_remote_api_version,
                         client.api_version)
        self.assertEqual(CONF.docker.default_timeout,
                         client.timeout)

    def test_docker_client_init_version(self):
        expected_version = '1.21'
        client = docker_utils.DockerHTTPClient(ver=expected_version)

        self.assertEqual(expected_version,
                         client.api_version)
        self.assertEqual(CONF.docker.default_timeout,
                         client.timeout)

    @mock.patch.object(docker.APIClient, 'inspect_container')
    @mock.patch.object(docker.APIClient, 'containers')
    def test_list_instances(self, mock_containers, mock_inspect):
        client = docker_utils.DockerHTTPClient()

        containers = [dict(Id=x) for x in range(0, 3)]
        inspect_results = [dict(Config=dict(Hostname=x)) for x in range(0, 3)]

        mock_containers.return_value = containers
        mock_inspect.side_effect = inspect_results

        instances = client.list_instances()

        self.assertEqual([0, 1, 2], instances)
        mock_containers.assert_called_once_with(all=True)
        mock_inspect.assert_has_calls([mock.call(x) for x in range(0, 3)])

    @mock.patch.object(docker.APIClient, 'inspect_container')
    @mock.patch.object(docker.APIClient, 'containers')
    def test_list_instances_inspect(self, mock_containers, mock_inspect):
        client = docker_utils.DockerHTTPClient()

        containers = [dict(Id=x) for x in range(0, 3)]
        inspect_results = [dict(Config=dict(Hostname=x)) for x in range(0, 3)]

        mock_containers.return_value = containers
        mock_inspect.side_effect = inspect_results

        instances = client.list_instances(inspect=True)

        self.assertEqual(inspect_results, instances)
        mock_containers.assert_called_once_with(all=True)
        mock_inspect.assert_has_calls([mock.call(x) for x in range(0, 3)])
