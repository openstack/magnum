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

from docker import errors
from oslo_config import cfg

from magnum.common import docker_utils
from magnum.common import exception
from magnum.common import utils
from magnum.conductor.handlers.common import docker_client
from magnum import objects
from magnum.openstack.common import log as logging

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

docker_opts = [
    cfg.StrOpt('docker_remote_api_version',
               default=docker_client.DEFAULT_DOCKER_REMOTE_API_VERSION,
               help='Docker remote api version. Override it according to '
                    'specific docker api version in your environment.'),
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


class Handler(object):

    def __init__(self):
        super(Handler, self).__init__()

    @staticmethod
    def _find_container_by_name(docker, name):
        try:
            for info in docker.list_instances(inspect=True):
                if info['Config'].get('Hostname') == name:
                    return info
        except errors.APIError as e:
            if e.response.status_code != 404:
                raise
        return {}

    def _encode_utf8(self, value):
        return unicode(value).encode('utf-8')

    @staticmethod
    def _docker_for_bay(bay):
        tcp_url = 'tcp://%s:2376' % bay.api_address
        return docker_client.DockerHTTPClient(tcp_url,
                                        CONF.docker.docker_remote_api_version)

    @classmethod
    def _docker_for_container(cls, context, container):
        bay = objects.Bay.get_by_uuid(context, container.bay_uuid)
        return cls._docker_for_bay(bay)

    @classmethod
    def get_docker_client(cls, context, container):
        if utils.is_uuid_like(container):
            container = objects.Container.get_by_uuid(context, container)
        return cls._docker_for_container(context, container)

    # Container operations

    def container_create(self, context, name, container_uuid, container):
        docker = self.get_docker_client(context, container)
        image_id = container.image_id
        LOG.debug('Creating container with image %s name %s'
                  % (image_id, name))
        try:
            image_repo, image_tag = docker_utils.parse_docker_image(image_id)
            docker.pull(image_repo, tag=image_tag)
            docker.inspect_image(self._encode_utf8(container.image_id))
            docker.create_container(image_id, name=name,
                                    hostname=container_uuid,
                                    command=container.command)
            return container
        except errors.APIError as api_error:
            raise exception.ContainerException(
                      "Docker API Error : %s" % str(api_error))

    def container_delete(self, context, container_uuid):
        LOG.debug("container_delete %s" % container_uuid)
        docker = self.get_docker_client(context, container_uuid)
        try:
            docker_id = self._find_container_by_name(docker, container_uuid)
            if not docker_id:
                return None
            return docker.remove_container(docker_id)
        except errors.APIError as api_error:
            raise exception.ContainerException(
                      "Docker API Error : %s" % str(api_error))

    def container_show(self, context, container_uuid):
        LOG.debug("container_show %s" % container_uuid)
        docker = self.get_docker_client(context, container_uuid)
        try:
            docker_id = self._find_container_by_name(docker, container_uuid)
            return docker.inspect_container(docker_id)
        except errors.APIError as api_error:
            raise exception.ContainerException(
                      "Docker API Error : %s" % str(api_error))

    def container_reboot(self, context, container_uuid):
        LOG.debug("container_reboot %s" % container_uuid)
        docker = self.get_docker_client(context, container_uuid)
        try:
            docker_id = self._find_container_by_name(docker, container_uuid)
            return docker.restart(docker_id)
        except errors.APIError as api_error:
            raise exception.ContainerException(
                      "Docker API Error : %s" % str(api_error))

    def container_stop(self, context, container_uuid):
        LOG.debug("container_stop %s" % container_uuid)
        docker = self.get_docker_client(context, container_uuid)
        try:
            docker_id = self._find_container_by_name(docker, container_uuid)
            return docker.stop(docker_id)
        except errors.APIError as api_error:
            raise exception.ContainerException(
                      "Docker API Error : %s" % str(api_error))

    def container_start(self, context, container_uuid):
        LOG.debug("Starting container %s" % container_uuid)
        docker = self.get_docker_client(context, container_uuid)
        try:
            docker_id = self._find_container_by_name(docker, container_uuid)
            LOG.debug("Found Docker container %s" % docker_id)
            return docker.start(docker_id)
        except errors.APIError as api_error:
            raise exception.ContainerException(
                      "Docker API Error : %s" % str(api_error))

    def container_pause(self, context, container_uuid):
        LOG.debug("container_pause %s" % container_uuid)
        docker = self.get_docker_client(context, container_uuid)
        try:
            docker_id = self._find_container_by_name(docker, container_uuid)
            return docker.pause(docker_id)
        except errors.APIError as api_error:
            raise exception.ContainerException(
                      "Docker API Error : %s" % str(api_error))

    def container_unpause(self, context, container_uuid):
        LOG.debug("container_unpause %s" % container_uuid)
        docker = self.get_docker_client(context, container_uuid)
        try:
            docker_id = self._find_container_by_name(docker, container_uuid)
            return docker.unpause(docker_id)
        except errors.APIError as api_error:
            raise exception.ContainerException(
                      "Docker API Error : %s" % str(api_error))

    def container_logs(self, context, container_uuid):
        LOG.debug("container_logs %s" % container_uuid)
        docker = self.get_docker_client(context, container_uuid)
        try:
            docker_id = self._find_container_by_name(docker, container_uuid)
            return {'output': docker.get_container_logs(docker_id)}
        except errors.APIError as api_error:
            raise exception.ContainerException(
                      "Docker API Error : %s" % str(api_error))

    def container_execute(self, context, container_uuid, command):
        LOG.debug("container_execute %s command %s" %
                  (container_uuid, command))
        docker = self.get_docker_client(context, container_uuid)
        try:
            docker_id = self._find_container_by_name(docker, container_uuid)
            return {'output': docker.execute(docker_id, command)}
        except errors.APIError as api_error:
            raise exception.ContainerException(
                      "Docker API Error : %s" % str(api_error))
