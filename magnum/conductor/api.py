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
from oslo_config import cfg

from magnum.common import rpc_service


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

    # Bay Operations

    def bay_create(self, bay, bay_create_timeout):
        return self._call('bay_create', bay=bay,
                          bay_create_timeout=bay_create_timeout)

    def bay_delete(self, uuid):
        return self._call('bay_delete', uuid=uuid)

    def bay_update(self, bay):
        return self._call('bay_update', bay=bay)

    # ReplicationController Operations

    def rc_create(self, rc):
        return self._call('rc_create', rc=rc)

    def rc_update(self, rc_ident, bay_ident, manifest):
        return self._call('rc_update', rc_ident=rc_ident,
                          bay_ident=bay_ident, manifest=manifest)

    def rc_list(self, context, bay_ident):
        return self._call('rc_list', bay_ident=bay_ident)

    def rc_delete(self, rc_ident, bay_ident):
        return self._call('rc_delete', rc_ident=rc_ident, bay_ident=bay_ident)

    def rc_show(self, context, rc_ident, bay_ident):
        return self._call('rc_show', rc_ident=rc_ident,
                          bay_ident=bay_ident)

    # Container operations

    def container_create(self, container):
        return self._call('container_create', container=container)

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
        return self._call('container_logs', container_uuid=container_uuid)

    def container_exec(self, container_uuid, command):
        return self._call('container_exec', container_uuid=container_uuid,
                          command=command)

    # CA operations

    def sign_certificate(self, bay, certificate):
        return self._call('sign_certificate', bay=bay, certificate=certificate)

    def get_ca_certificate(self, bay):
        return self._call('get_ca_certificate', bay=bay)

    # Versioned Objects indirection API

    def object_class_action(self, context, objname, objmethod, objver,
                            args, kwargs):
        "Indirection API callback"
        return self._client.call(context, 'object_class_action',
                                 objname=objname, objmethod=objmethod,
                                 objver=objver, args=args, kwargs=kwargs)

    def object_action(self, context, objinst, objmethod, args, kwargs):
        "Indirection API callback"
        return self._client.call(context, 'object_action', objinst=objinst,
                                 objmethod=objmethod, args=args, kwargs=kwargs)

    def object_backport(self, context, objinst, target_version):
        "Indirection API callback"
        return self._client.call(context, 'object_backport', objinst=objinst,
                                 target_version=target_version)


class ListenerAPI(rpc_service.API):
    def __init__(self, context=None, topic=None, server=None, timeout=None):
        super(ListenerAPI, self).__init__(context=context, topic=topic,
                                          server=server, timeout=timeout)

    def ping_conductor(self):
        return self._call('ping_conductor')
