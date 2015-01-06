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

import mock

from magnum.conductor.handlers import docker_conductor
from magnum.tests import base


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

        self.conductor.container_create(None, 'some-name', 'some-uuid',
                                        mock_container)

        utf8_image_id = self.conductor._encode_utf8(mock_container.image_id)
        self.mock_client.pull.assert_called_once_with('test_image',
                                                      tag='some_tag')
        self.mock_client.inspect_image.assert_called_once_with(utf8_image_id)
        self.mock_client.create_container(mock_container.image_id,
                                          name='some-name',
                                          hostname='some-uduid')
