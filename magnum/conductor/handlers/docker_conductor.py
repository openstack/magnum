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

"""Magnum Docker RPC handler."""

from docker import client
from docker import errors
from docker import tls
from oslo.config import cfg

from magnum.openstack.common import log as logging

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

docker_opts = [
    cfg.StrOpt('root_directory',
               default='/var/lib/docker',
               help='Path to use as the root of the Docker runtime.'),
    cfg.StrOpt('host_url',
               default='unix:///var/run/docker.sock',
               help='tcp://host:port to bind/connect to or '
                    'unix://path/to/socket to use'),
    cfg.BoolOpt('api_insecure',
                default=False,
                help='If set, ignore any SSL validation issues'),
    cfg.StrOpt('ca_file',
               help='Location of CA certificates file for '
                    'securing docker api requests (tlscacert).'),
    cfg.StrOpt('cert_file',
               help='Location of TLS certificate file for '
                    'securing docker api requests (tlscert).'),
    cfg.StrOpt('key_file',
               help='Location of TLS private key file for '
                    'securing docker api requests (tlskey).'),
]

CONF.register_opts(docker_opts, 'docker')


class DockerHTTPClient(client.Client):
    def __init__(self, url='unix://var/run/docker.sock'):
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
            version='1.13',
            timeout=10,
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

    def pause(self, docker_id):
        url = self._url("/containers/{0}/pause".format(docker_id))
        res = self._post(url)
        return res.status_code == 204

    def unpause(self, docker_id):
        url = self._url("/containers/{0}/unpause".format(docker_id))
        res = self._post(url)
        return res.status_code == 204

    def load_repository_file(self, name, path):
        with open(path) as fh:
            self.load_image(fh)

    def get_container_logs(self, docker_id):
        return self.attach(docker_id, 1, 1, 0, 1)


# These are the backend operations.  They are executed by the backend
# service.  API calls via AMQP (within the ReST API) trigger the handlers to
# be called.


class Handler(object):

    def __init__(self):
        super(Handler, self).__init__()
        self._docker = None

    @property
    def docker(self):
        if self._docker is None:
            self._docker = DockerHTTPClient(CONF.docker.host_url)
        return self._docker

    def _find_container_by_name(self, name):
        try:
            for info in self.docker.list_instances(inspect=True):
                if info['Config'].get('Hostname') == name:
                    return info
        except errors.APIError as e:
            if e.response.status_code != 404:
                raise
        return {}

    def _encode_utf8(self, value):
        return unicode(value).encode('utf-8')

    # Container operations

    def container_create(self, ctxt, name, container_uuid, container):
        LOG.debug('Creating container with image %s name %s'
                  % (container.image_id, name))
        self.docker.inspect_image(self._encode_utf8(container.image_id))
        self.docker.create_container(container.image_id, name=name,
                                     hostname=container_uuid)
        return container

    def container_list(self, ctxt):
        LOG.debug("container_list")
        container_list = self.docker.containers()
        return container_list

    def container_delete(self, ctxt, container_uuid):
        LOG.debug("container_delete %s" % container_uuid)
        docker_id = self._find_container_by_name(container_uuid)
        return self.docker.remove_container(docker_id)

    def container_show(self, ctxt, container_uuid):
        LOG.debug("container_show %s" % container_uuid)
        docker_id = self._find_container_by_name(container_uuid)
        return self.docker.inspect_container(docker_id)

    def container_reboot(self, ctxt, container_uuid):
        LOG.debug("container_reboot %s" % container_uuid)
        docker_id = self._find_container_by_name(container_uuid)
        return self.docker.restart(docker_id)

    def container_stop(self, ctxt, container_uuid):
        LOG.debug("container_stop %s" % container_uuid)
        docker_id = self._find_container_by_name(container_uuid)
        return self.docker.stop(docker_id)

    def container_start(self, ctxt, container_uuid):
        LOG.debug("Starting container %s" % container_uuid)
        docker_id = self._find_container_by_name(container_uuid)
        LOG.debug("Found Docker container %s" % docker_id)
        return self.docker.start(docker_id)

    def container_pause(self, ctxt, container_uuid):
        LOG.debug("container_pause %s" % container_uuid)
        docker_id = self._find_container_by_name(container_uuid)
        return self.docker.pause(docker_id)

    def container_unpause(self, ctxt, container_uuid):
        LOG.debug("container_unpause %s" % container_uuid)
        docker_id = self._find_container_by_name(container_uuid)
        return self.docker.unpause(docker_id)

    def container_logs(self, ctxt, container_uuid):
        LOG.debug("container_logs %s" % container_uuid)
        docker_id = self._find_container_by_name(container_uuid)
        return self.docker.get_container_logs(docker_id)

    def container_execute(self, ctxt, container_uuid, command):
        LOG.debug("container_execute %s command %s" %
                  (container_uuid, command))
        docker_id = self._find_container_by_name(container_uuid)
        return self.docker.execute(docker_id, command)
