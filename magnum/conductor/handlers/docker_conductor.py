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

import functools

from docker import errors
from oslo_log import log as logging
import six

from magnum.common import docker_utils
from magnum.common import exception
from magnum.common import utils as magnum_utils
from magnum.i18n import _LE
from magnum import objects
from magnum.objects import fields

LOG = logging.getLogger(__name__)


def wrap_container_exception(f):
    def wrapped(self, context, *args, **kwargs):
        try:
            return f(self, context, *args, **kwargs)
        except Exception as e:
            container_uuid = None
            if 'container_uuid' in kwargs:
                container_uuid = kwargs.get('container_uuid')
            elif 'container' in kwargs:
                container_uuid = kwargs.get('container').uuid

            LOG.exception(_LE("Error while connect to docker "
                              "container %s"), container_uuid)
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

    # Container operations

    @wrap_container_exception
    def container_create(self, context, container):
        with docker_utils.docker_for_container(context, container) as docker:
            name = container.name
            container_uuid = container.uuid
            image = container.image
            LOG.debug('Creating container with image %s name %s', image, name)
            try:
                image_repo, image_tag = docker_utils.parse_docker_image(image)
                docker.pull(image_repo, tag=image_tag)
                docker.inspect_image(self._encode_utf8(container.image))
                kwargs = {'name': name,
                          'hostname': container_uuid,
                          'command': container.command,
                          'environment': container.environment}
                if docker_utils.is_docker_api_version_atleast(docker, '1.19'):
                    if container.memory is not None:
                        kwargs['host_config'] = {
                            'Memory':
                            magnum_utils.get_docker_quantity(container.memory)}
                else:
                    kwargs['mem_limit'] = container.memory

                docker.create_container(image, **kwargs)
                container.status = fields.ContainerStatus.STOPPED
                return container
            except errors.APIError:
                container.status = fields.ContainerStatus.ERROR
                raise
            finally:
                container.save()

    @wrap_container_exception
    def container_delete(self, context, container_uuid):
        LOG.debug("container_delete %s", container_uuid)
        with docker_utils.docker_for_container(context,
                                               container_uuid) as docker:
            docker_id = self._find_container_by_name(docker,
                                                     container_uuid)
            if not docker_id:
                return None
            return docker.remove_container(docker_id)

    @wrap_container_exception
    def container_show(self, context, container_uuid):
        LOG.debug("container_show %s", container_uuid)
        with docker_utils.docker_for_container(context,
                                               container_uuid) as docker:
            container = objects.Container.get_by_uuid(context, container_uuid)
            try:
                docker_id = self._find_container_by_name(docker,
                                                         container_uuid)
                if not docker_id:
                    LOG.exception(_LE("Can not find docker instance with %s,"
                                      "set it to Error status"),
                                  container_uuid)
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
                raise

    @wrap_container_exception
    def _container_action(self, context, container_uuid, status, docker_func):
        LOG.debug("%s container %s ...", docker_func, container_uuid)
        with docker_utils.docker_for_container(context,
                                               container_uuid) as docker:
            docker_id = self._find_container_by_name(docker,
                                                     container_uuid)
            result = getattr(docker, docker_func)(docker_id)
            container = objects.Container.get_by_uuid(context,
                                                      container_uuid)
            container.status = status
            container.save()
            return result

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
        LOG.debug("container_logs %s", container_uuid)
        with docker_utils.docker_for_container(context,
                                               container_uuid) as docker:
            docker_id = self._find_container_by_name(docker,
                                                     container_uuid)
            return {'output': docker.logs(docker_id)}

    @wrap_container_exception
    def container_exec(self, context, container_uuid, command):
        LOG.debug("container_exec %s command %s",
                  container_uuid, command)
        with docker_utils.docker_for_container(context,
                                               container_uuid) as docker:
            docker_id = self._find_container_by_name(docker,
                                                     container_uuid)
            if docker_utils.is_docker_library_version_atleast('1.2.0'):
                create_res = docker.exec_create(docker_id, command, True,
                                                True, False)
                exec_output = docker.exec_start(create_res, False, False,
                                                False)
            else:
                exec_output = docker.execute(docker_id, command)
            return {'output': exec_output}
