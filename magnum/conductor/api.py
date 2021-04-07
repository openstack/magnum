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

from magnum.common import profiler
from magnum.common import rpc_service
import magnum.conf

CONF = magnum.conf.CONF

# The Backend API class serves as a AMQP client for communicating
# on a topic exchange specific to the conductors.  This allows the ReST
# API to trigger operations on the conductors


@profiler.trace_cls("rpc")
class API(rpc_service.API):
    def __init__(self, context=None, topic=CONF.conductor.topic):
        super(API, self).__init__(context=context, topic=topic)

    # Cluster Operations

    def cluster_create(self, cluster, master_count, node_count,
                       create_timeout):
        return self._call('cluster_create', cluster=cluster,
                          master_count=master_count, node_count=node_count,
                          create_timeout=create_timeout)

    def cluster_create_async(self, cluster, master_count, node_count,
                             create_timeout):
        self._cast('cluster_create', cluster=cluster,
                   master_count=master_count, node_count=node_count,
                   create_timeout=create_timeout)

    def cluster_delete(self, uuid):
        return self._call('cluster_delete', uuid=uuid)

    def cluster_delete_async(self, uuid):
        self._cast('cluster_delete', uuid=uuid)

    def cluster_update(self, cluster, node_count,
                       health_status, health_status_reason):
        return self._call(
            'cluster_update', cluster=cluster, node_count=node_count,
            health_status=health_status,
            health_status_reason=health_status_reason)

    def cluster_update_async(self, cluster, node_count,
                             health_status, health_status_reason,
                             rollback=False):
        self._cast('cluster_update', cluster=cluster,
                   node_count=node_count,
                   health_status=health_status,
                   health_status_reason=health_status_reason,
                   rollback=rollback)

    def cluster_resize(self, cluster, node_count, nodes_to_remove,
                       nodegroup, rollback=False):

        return self._call('cluster_resize',
                          cluster=cluster,
                          node_count=node_count,
                          nodes_to_remove=nodes_to_remove,
                          nodegroup=nodegroup)

    def cluster_resize_async(self, cluster, node_count, nodes_to_remove,
                             nodegroup, rollback=False):
        return self._cast('cluster_resize',
                          cluster=cluster,
                          node_count=node_count,
                          nodes_to_remove=nodes_to_remove,
                          nodegroup=nodegroup)

    def cluster_upgrade(self, cluster, cluster_template, max_batch_size,
                        nodegroup):
        return self._call('cluster_upgrade',
                          cluster=cluster,
                          cluster_template=cluster_template,
                          max_batch_size=max_batch_size,
                          nodegroup=nodegroup)

    def cluster_upgrade_async(self, cluster, cluster_template, max_batch_size,
                              nodegroup):
        return self._call('cluster_upgrade',
                          cluster=cluster,
                          cluster_template=cluster_template,
                          max_batch_size=max_batch_size,
                          nodegroup=nodegroup)

    # Federation Operations

    def federation_create(self, federation, create_timeout):
        return self._call('federation_create', federation=federation,
                          create_timeout=create_timeout)

    def federation_create_async(self, federation, create_timeout):
        self._cast('federation_create', federation=federation,
                   create_timeout=create_timeout)

    def federation_delete(self, uuid):
        return self._call('federation_delete', uuid=uuid)

    def federation_delete_async(self, uuid):
        self._cast('federation_delete', uuid=uuid)

    def federation_update(self, federation):
        return self._call('federation_update', federation=federation)

    def federation_update_async(self, federation, rollback=False):
        self._cast('federation_update', federation=federation,
                   rollback=rollback)

    # CA operations

    def sign_certificate(self, cluster, certificate):
        return self._call('sign_certificate', cluster=cluster,
                          certificate=certificate)

    def get_ca_certificate(self, cluster, ca_cert_type=None):
        return self._call('get_ca_certificate', cluster=cluster,
                          ca_cert_type=ca_cert_type)

    def rotate_ca_certificate(self, cluster):
        return self._call('rotate_ca_certificate', cluster=cluster)

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

    # NodeGroup Operations

    def nodegroup_create(self, cluster, nodegroup):
        return self._call('nodegroup_create', cluster=cluster,
                          nodegroup=nodegroup)

    def nodegroup_create_async(self, cluster, nodegroup):
        self._cast('nodegroup_create', cluster=cluster, nodegroup=nodegroup)

    def nodegroup_delete(self, cluster, nodegroup):
        return self._call('nodegroup_delete', cluster=cluster,
                          nodegroup=nodegroup)

    def nodegroup_delete_async(self, cluster, nodegroup):
        self._cast('nodegroup_delete', cluster=cluster, nodegroup=nodegroup)

    def nodegroup_update(self, cluster, nodegroup):
        return self._call('nodegroup_update', cluster=cluster,
                          nodegroup=nodegroup)

    def nodegroup_update_async(self, cluster, nodegroup):
        self._cast('nodegroup_update', cluster=cluster, nodegroup=nodegroup)


@profiler.trace_cls("rpc")
class ListenerAPI(rpc_service.API):
    def __init__(self, context=None, topic=None, server=None, timeout=None):
        super(ListenerAPI, self).__init__(context=context, topic=topic,
                                          server=server, timeout=timeout)

    def ping_conductor(self):
        return self._call('ping_conductor')
