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
import functools
from oslo_config import cfg
from oslo_log import log as logging
import six

from magnum.common import docker_utils
from magnum.common import exception
from magnum.common import utils
from magnum.conductor.handlers.common import docker_client
from magnum.conductor import utils as conductor_utils
from magnum.i18n import _LE
from magnum import objects
from magnum.objects import fields

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

docker_opts = [
    cfg.StrOpt('docker_remote_api_version',
               default=docker_client.DEFAULT_DOCKER_REMOTE_API_VERSION,
               help='Docker remote api version. Override it according to '
                    'specific docker api version in your environment.'),
    cfg.IntOpt('default_timeout',
               default=docker_client.DEFAULT_DOCKER_TIMEOUT,
               help='Default timeout in seconds for docker client '
                    'operations.'),
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


def wrap_container_exception(f):
    def wrapped(self, context, *args, **kwargs):
        try:
            return f(self, context, *args, **kwargs)
        except Exception as e:
            container_uuid = kwargs.get('container_uuid')
            if container_uuid is not None:
                LOG.exception(_LE("Error while connect to docker "
                                  "container %(name)s: %(error)s"),
                              {'name': container_uuid,
                               'error': str(e)})
            raise exception.ContainerException(
                "Docker internal Error: %s" % str(e))
    return functools.wraps(f)(wrapped)


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
        if six.PY2 and not isinstance(value, unicode):
            value = unicode(value)
        return value.encode('utf-8')

    @staticmethod
    def _docker_for_bay(bay):
        tcp_url = 'tcp://%s:2376' % bay.api_address
        return docker_client.DockerHTTPClient(
            tcp_url,
            CONF.docker.docker_remote_api_version,
            CONF.docker.default_timeout
        )

    @classmethod
    def _docker_for_container(cls, context, container):
        bay = conductor_utils.retrieve_bay(context, container)
        return cls._docker_for_bay(bay)

    @classmethod
    def get_docker_client(cls, context, container):
        if utils.is_uuid_like(container):
            container = objects.Container.get_by_uuid(context, container)
        return cls._docker_for_container(context, container)

    # Container operations

    @wrap_container_exception
    def container_create(self, context, container):
        docker = self.get_docker_client(context, container)
        name = container.name
        container_uuid = container.uuid
        image = container.image
        LOG.debug('Creating container with image %s name %s'
                  % (image, name))
        try:
            image_repo, image_tag = docker_utils.parse_docker_image(image)
            docker.pull(image_repo, tag=image_tag)
            docker.inspect_image(self._encode_utf8(container.image))
            docker.create_container(image, name=name,
                                    hostname=container_uuid,
                                    command=container.command)
            container.status = fields.ContainerStatus.STOPPED
            return container
        except errors.APIError as api_error:
            container.status = fields.ContainerStatus.ERROR
            raise exception.ContainerException(
                "Docker API Error : %s" % str(api_error))
        finally:
            container.save()

    @wrap_container_exception
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

    @wrap_container_exception
    def container_show(self, context, container_uuid):
        LOG.debug("container_show %s" % container_uuid)
        docker = self.get_docker_client(context, container_uuid)
        container = objects.Container.get_by_uuid(context, container_uuid)
        try:
            docker_id = self._find_container_by_name(docker, container_uuid)
            if not docker_id:
                LOG.exception(_LE("Can not find docker instance with %s,"
                                  "set it to Error status"), container_uuid)
                container.status = fields.ContainerStatus.ERROR
                container.save()
                return container
            result = docker.inspect_container(docker_id)
            status = result.get('State')
            if status:
                if status.get('Error') is True:
                    container.status = fields.ContainerStatus.ERROR
                elif status.get('Paused'):
                    container.status = fields.ContainerStatus.PAUSED
                elif status.get('Running'):
                    container.status = fields.ContainerStatus.RUNNING
                else:
                    container.status = fields.ContainerStatus.STOPPED
                container.save()
            return container
        except errors.APIError as api_error:
            error_message = str(api_error)
            if '404' in error_message:
                container.status = fields.ContainerStatus.ERROR
                container.save()
                return container
            raise exception.ContainerException(
                "Docker API Error : %s" % (error_message))

    @wrap_container_exception
    def _container_action(self, context, container_uuid, status, docker_func):
        LOG.debug("container_%s %s" % (status, container_uuid))
        docker = self.get_docker_client(context, container_uuid)
        try:
            docker_id = self._find_container_by_name(docker, container_uuid)
            result = getattr(docker, docker_func)(docker_id)
            container = objects.Container.get_by_uuid(context, container_uuid)
            container.status = status
            container.save()
            return result
        except errors.APIError as api_error:
            raise exception.ContainerException(
                "Docker API Error : %s" % str(api_error))

    def container_reboot(self, context, container_uuid):
        return self._container_action(context, container_uuid,
                                      fields.ContainerStatus.RUNNING,
                                      'restart')

    def container_stop(self, context, container_uuid):
        return self._container_action(context, container_uuid,
                                      fields.ContainerStatus.STOPPED, 'stop')

    def container_start(self, context, container_uuid):
        return self._container_action(context, container_uuid,
                                      fields.ContainerStatus.RUNNING, 'start')

    def container_pause(self, context, container_uuid):
        return self._container_action(context, container_uuid,
                                      fields.ContainerStatus.PAUSED, 'pause')

    def container_unpause(self, context, container_uuid):
        return self._container_action(context, container_uuid,
                                      fields.ContainerStatus.RUNNING,
                                      'unpause')

    @wrap_container_exception
    def container_logs(self, context, container_uuid):
        LOG.debug("container_logs %s" % container_uuid)
        docker = self.get_docker_client(context, container_uuid)
        try:
            docker_id = self._find_container_by_name(docker, container_uuid)
            return {'output': docker.get_container_logs(docker_id)}
        except errors.APIError as api_error:
            raise exception.ContainerException(
                "Docker API Error : %s" % str(api_error))

    @wrap_container_exception
    def container_exec(self, context, container_uuid, command):
        LOG.debug("container_exec %s command %s" %
                  (container_uuid, command))
        docker = self.get_docker_client(context, container_uuid)
        try:
            docker_id = self._find_container_by_name(docker, container_uuid)
            if docker_utils.is_docker_library_version_atleast('1.2.0'):
                create_res = docker.exec_create(docker_id, command, True,
                                                True, False)
                exec_output = docker.exec_start(create_res, False, False,
                                                False)
            else:
                exec_output = docker.execute(docker_id, command)
            return {'output': exec_output}
        except errors.APIError as api_error:
            raise exception.ContainerException(
                "Docker API Error : %s" % str(api_error))
