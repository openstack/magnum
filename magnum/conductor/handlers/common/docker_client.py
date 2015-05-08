# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""Magnum Docker Client."""

from docker import client
from docker import tls
from oslo_config import cfg

from magnum.openstack.common import log as logging

DEFAULT_DOCKER_REMOTE_API_VERSION = '1.17'
DEFAULT_DOCKER_TIMEOUT = 10

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class DockerHTTPClient(client.Client):
    def __init__(self, url='unix://var/run/docker.sock',
                 ver=DEFAULT_DOCKER_REMOTE_API_VERSION,
                 timeout=DEFAULT_DOCKER_TIMEOUT):
        if (CONF.docker.cert_file or
                CONF.docker.key_file):
            client_cert = (CONF.docker.cert_file, CONF.docker.key_file)
        else:
            client_cert = None
        if (CONF.docker.ca_file or
                CONF.docker.api_insecure or
                client_cert):
            ssl_config = tls.TLSConfig(
                client_cert=client_cert,
                ca_cert=CONF.docker.ca_file,
                verify=CONF.docker.api_insecure)
        else:
            ssl_config = False
        super(DockerHTTPClient, self).__init__(
            base_url=url,
            version=ver,
            timeout=timeout,
            tls=ssl_config
        )

    def list_instances(self, inspect=False):
        res = []
        for container in self.containers(all=True):
            info = self.inspect_container(container['Id'])
            if not info:
                continue
            if inspect:
                res.append(info)
            else:
                res.append(info['Config'].get('Hostname'))
        return res

    def pause(self, container):
        if isinstance(container, dict):
            container = container.get('Id')
        url = self._url('/containers/{0}/pause'.format(container))
        res = self._post(url)
        self._raise_for_status(res)

    def unpause(self, container):
        if isinstance(container, dict):
            container = container.get('Id')
        url = self._url('/containers/{0}/unpause'.format(container))
        res = self._post(url)
        self._raise_for_status(res)

    def load_repository_file(self, name, path):
        with open(path) as fh:
            self.load_image(fh)

    def get_container_logs(self, docker_id):
        return self.attach(docker_id, 1, 1, 0, 1)
