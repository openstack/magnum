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

    # Cluster Operations

    def cluster_create(self, cluster, create_timeout):
        return self._call('cluster_create', cluster=cluster,
                          create_timeout=create_timeout)

    def cluster_create_async(self, cluster, create_timeout):
        self._cast('cluster_create', cluster=cluster,
                   create_timeout=create_timeout)

    def cluster_delete(self, uuid):
        return self._call('cluster_delete', uuid=uuid)

    def cluster_delete_async(self, uuid):
        self._cast('cluster_delete', uuid=uuid)

    def cluster_update(self, cluster):
        return self._call('cluster_update', cluster=cluster)

    def cluster_update_async(self, cluster, rollback=False):
        self._cast('cluster_update', cluster=cluster, rollback=rollback)

    # CA operations

    def sign_certificate(self, cluster, certificate):
        return self._call('sign_certificate', cluster=cluster,
                          certificate=certificate)

    def get_ca_certificate(self, cluster):
        return self._call('get_ca_certificate', cluster=cluster)

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
