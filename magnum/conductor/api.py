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
    def __init__(self, transport=None, context=None, topic=None):
        if topic is None:
            cfg.CONF.import_opt('topic', 'magnum.conductor.config',
                                group='conductor')
        super(API, self).__init__(transport, context,
                                  topic=cfg.CONF.conductor.topic)

    # Bay Model Operations

    def baymodel_create(self, ctxt, baymodel):
        return baymodel.create(ctxt)

    def baymodel_list(self, ctxt, limit, marker, sort_key, sort_dir):
        return objects.BayModel.list(ctxt, limit, marker, sort_key, sort_dir)

    def baymodel_delete(self, ctxt, uuid):
        baymodel = objects.BayModel.get_by_uuid(uuid)
        return baymodel.destroy()

    def baymodel_show(self, ctxt, uuid):
        return objects.BayModel.get_by_uuid(uuid)

    # Bay Operations

    def bay_create(self, bay):
        return self._call('bay_create', bay=bay)

    def bay_list(self, context, limit, marker, sort_key, sort_dir):
        return objects.Bay.list(context, limit, marker, sort_key, sort_dir)

    def bay_delete(self, uuid):
        return self._call('bay_delete', uuid=uuid)

    def bay_show(self, ctxt, uuid):
        return objects.Bay.get_by_uuid(ctxt, uuid)

    # Service Operations

    def service_create(self, service):
        return self._call('service_create', service=service)

    def service_list(self, context, limit, marker, sort_key, sort_dir):
        # TODO(pkilambi): return kubectl results once we parse appropriately
        # or figure out a clean way to interact with k8s.
        return objects.Service.list(context, limit, marker, sort_key, sort_dir)

    def service_delete(self, uuid):
        return self._call('service_delete', uuid=uuid)

    def service_show(self, ctxt, uuid):
        return objects.Service.get_by_uuid(ctxt, uuid)

    # Pod Operations

    def pod_create(self, pod):
        return self._call('pod_create', pod=pod)

    def pod_list(self, context, limit, marker, sort_key, sort_dir):
        return objects.Pod.list(context, limit, marker, sort_key, sort_dir)

    def pod_delete(self, uuid):
        return self._call('pod_delete', uuid=uuid)

    def pod_show(self, ctxt, uuid):
        return objects.Pod.get_by_uuid(ctxt, uuid)

    # ReplicationController Operations

    def rc_create(self, rc):
        return self._call('rc_create', rc=rc)

    def rc_list(self, context, limit, marker, sort_key, sort_dir):
        return objects.ReplicationController.list(context, limit, marker,
                                                  sort_key, sort_dir)

    def rc_delete(self, uuid):
        return self._call('rc_delete', uuid=uuid)

    def rc_show(self, ctxt, uuid):
        return objects.ReplicationController.get_by_uuid(ctxt, uuid)

    # Container operations

    def container_create(self, name, container_uuid, container):
        return self._call('container_create', name=name,
                          container_uuid=container_uuid,
                          container=container)

    def container_list(self, context, limit, marker, sort_key, sort_dir):
        return objects.Container.list(context, limit, marker, sort_key,
                                      sort_dir)

    def container_delete(self, container_uuid):
        return self._call('container_delete', container_uuid=container_uuid)

    def container_show(self, container_uuid):
        return self._call('container_show', container_uuid=container_uuid)

    def container_reboot(self, container_uuid):
        return self._call('container_reboot', container_uuid=container_uuid)

    def container_stop(self, container_uuid):
        return self._call('container_stop', container_uuid=container_uuid)

    def container_start(self, container_uuid):
        return self._call('container_start', container_uuid=container_uuid)

    def container_pause(self, container_uuid):
        return self._call('container_pause', container_uuid=container_uuid)

    def container_unpause(self, container_uuid):
        return self._call('container_unpause', container_uuid=container_uuid)

    def container_logs(self, container_uuid):
        return self._call('container_logs', ontainer_uuid=container_uuid)

    def container_execute(self, container_uuid, command):
        return self._call('container_execute', container_uuid=container_uuid,
                          command=command)
