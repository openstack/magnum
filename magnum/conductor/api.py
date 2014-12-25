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

from magnum.common import rpc_service
from magnum import objects


# The Backend API class serves as a AMQP client for communicating
# on a topic exchange specific to the conductors.  This allows the ReST
# API to trigger operations on the conductors

class API(rpc_service.API):
    def __init__(self, transport=None, context=None):
        cfg.CONF.import_opt('topic', 'magnum.conductor.config',
                            group='conductor')
        super(API, self).__init__(transport, context,
                                  topic=cfg.CONF.conductor.topic)

    # Bay Model Operations

    def baymodel_create(self, bay):
        return self._call('baymodel_create', bay=bay)

    def baymodel_list(self, context, limit, marker, sort_key, sort_dir):
        return objects.BayModel.list(context, limit, marker, sort_key,
            sort_dir)

    def baymodel_delete(self, uuid):
        return self._call('baymodel_delete', uuid=uuid)

    def baymodel_show(self, uuid):
        return self._call('baymodel_show', uuid=uuid)

    # Bay Operations

    def bay_create(self, bay):
        return self._call('bay_create', bay=bay)

    def bay_list(self, context, limit, marker, sort_key, sort_dir):
        return objects.Bay.list(context, limit, marker, sort_key, sort_dir)

    def bay_delete(self, uuid):
        return self._call('bay_delete', uuid=uuid)

    def bay_show(self, uuid):
        return self._call('bay_show', uuid=uuid)

    # Service Operations

    def service_create(self, service):
        return self._call('service_create', service=service)

    def service_list(self, context, limit, marker, sort_key, sort_dir):
        # TODO(pkilambi): return kubectl results once we parse appropriately
        # or figure out a clean way to interact with k8s.
        return objects.Service.list(context, limit, marker, sort_key, sort_dir)

    def service_delete(self, service):
        return self._call('service_delete', service)

    def service_show(self, uuid):
        return self._call('service_show', uuid=uuid)

    # Pod Operations

    def pod_create(self, pod):
        return self._call('pod_create', pod=pod)

    def pod_list(self, context, limit, marker, sort_key, sort_dir):
        return objects.Pod.list(context, limit, marker, sort_key, sort_dir)

    def pod_delete(self, pod):
        return self._call('pod_delete', pod)

    def pod_show(self, uuid):
        return self._call('pod_show', uuid=uuid)

    # Container operations

    def container_create(self, name, container):
        return self._call('container_create', name=name, container=container)

    def container_list(self, context, limit, marker, sort_key, sort_dir):
        return objects.Container.list(context, limit, marker, sort_key,
                                      sort_dir)

    def container_delete(self, name):
        return self._call('container_delete', name=name)

    def container_show(self, name):
        return self._call('container_show', name)

    def container_reboot(self, name):
        return self._call('container_reboot', name=name)

    def container_stop(self, name):
        return self._call('container_stop', name=name)

    def container_start(self, name):
        return self._call('container_start', name=name)

    def container_pause(self, name):
        return self._call('container_pause', name=name)

    def container_unpause(self, name):
        return self._call('container_unpause', name=name)

    def container_logs(self, name):
        return self._call('container_logs', name=name)

    def container_execute(self, name):
        return self._call('container_execute', name=name)
