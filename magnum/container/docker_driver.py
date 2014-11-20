#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import docker

from magnum import base


class DockerContainerFactory(base.ContainerFactory):
    def __init__(self, pod_id, client=None):
        self.docker = client or docker.Client()

    def create(self, *args, **kwargs):
        self.docker.create_container(**kwargs)
        self.docker.start(self.container_id)

    def list(self):
        return self.docker.containers()


class DockerContainer(base.Container):
    def __init__(self, client, container_id):
        self.docker = client
        self.container_id = container_id

    def info(self):
        self.docker.inspect(self.container_id)

    def reboot(self):
        self.docker.reboot(self.container_id)

    def kill(self):
        self.docker.kill(self.container_id)

    def destroy(self):
        self.docker.destroy(self.container_id)

    def logs(self):
        return self.docker.logs(self.container_id)

    def pause(self):
        self.docker.pause(self.container_id)

    def unpause(self):
        self.docker.unpause(self.container_id)

    def execute(self, cmd):
        return self.docker.execute(self.container_id, cmd)
