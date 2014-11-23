#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""API for interfacing with Magnum Backend."""

from oslo.config import cfg

from magnum.common.rpc import service


# The Backend API class serves as a AMQP client for communicating
# on a topic exchange specific to the backends.  This allows the ReST
# API to trigger operations on the backends

class API(service.API):
    def __init__(self, transport=None, context=None):
        cfg.CONF.import_opt('topic', 'magnum.backends.config',
                            group='backends')
        super(API, self).__init__(transport, context,
                                  topic=cfg.CONF.backends.topic)

    # Bay Operations

    def bay_create(self, uuid, contents):
        return self._call('bay_get', contents=contents)

    def bay_list(self):
        return self._call('bay_list')

    def bay_delete(self, uuid):
        return self._call('bay_delete', uuid=uuid)

    def bay_show(self, uuid):
        return self._call('bay_show', uuid=uuid)

    # Service Operations

    def service_create(self, uuid, contents):
        return self._call('service_create', uuid=uuid, contents=contents)

    def service_list(self):
        return self._call('service_list')

    def service_delete(self, uuid):
        return self._call('service_delete', uuid=uuid)

    def service_show(self, uuid):
        return self._call('service_show', uuid=uuid)

    # Pod Operations

    def pod_create(self, uuid, contents):
        return self._call('pod_create4', uuid=uuid, contents=contents)

    def pod_list(self):
        return self._call('pod_list')

    def pod_delete(self, uuid):
        return self._call('pod_delete', uuid=uuid)

    def pod_show(self, uuid):
        return self._call('pod_show', uuid=uuid)

    # Container operations

    def container_create(self, uuid, contents):
        return self._call('container_create', uuid=uuid)

    def container_list(self):
        return self._call('container_list')

    def container_delete(self, uuid):
        return self._call('container_delete', uuid=uuid)

    def container_show(self, uuid):
        return self._call('container_show', uuid=uuid)

    def container_reboot(self, uuid):
        return self._call('container_reboot', uuid=uuid)

    def container_stop(self, uuid):
        return self._call('container_stop', uuid=uuid)

    def container_start(self, uuid):
        return self._call('container_start', uuid=uuid)

    def container_pause(self, uuid):
        return self._call('container_pause', uuid=uuid)

    def container_unpause(self, uuid):
        return self._call('container_unpause', uuid=uuid)

    def container_logs(self, uuid):
        return self._call('container_logs', uuid=uuid)

    def container_execute(self, uuid):
        return self._call('container_execute', uuid=uuid)
