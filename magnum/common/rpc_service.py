# Copyright 2014 - Rackspace Hosting
#
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

"""Common RPC service and API tools for Magnum."""

import oslo_messaging as messaging
from oslo_messaging.rpc import dispatcher
from oslo_service import service
from oslo_utils import importutils

from magnum.common import profiler
from magnum.common import rpc
import magnum.conf
from magnum.objects import base as objects_base
from magnum.service import periodic
from magnum.servicegroup import magnum_service_periodic as servicegroup


osprofiler = importutils.try_import("osprofiler.profiler")

CONF = magnum.conf.CONF


def _init_serializer():
    serializer = rpc.RequestContextSerializer(
        objects_base.MagnumObjectSerializer())
    if osprofiler:
        serializer = rpc.ProfilerRequestContextSerializer(serializer)
    else:
        serializer = rpc.RequestContextSerializer(serializer)
    return serializer


class Service(service.Service):

    def __init__(self, topic, server, handlers, binary):
        super(Service, self).__init__()
        serializer = _init_serializer()
        transport = messaging.get_rpc_transport(CONF)
        # TODO(asalkeld) add support for version='x.y'
        access_policy = dispatcher.DefaultRPCAccessPolicy
        target = messaging.Target(topic=topic, server=server)
        self._server = messaging.get_rpc_server(transport, target, handlers,
                                                executor='eventlet',
                                                serializer=serializer,
                                                access_policy=access_policy)
        self.binary = binary
        profiler.setup(binary, CONF.host)

    def start(self):
        self._server.start()

    def create_periodic_tasks(self):
        if CONF.periodic_enable:
            periodic.setup(CONF, self.tg)
        servicegroup.setup(CONF, self.binary, self.tg)

    def stop(self):
        if self._server:
            self._server.stop()
            self._server.wait()
        super(Service, self).stop()

    @classmethod
    def create(cls, topic, server, handlers, binary):
        service_obj = cls(topic, server, handlers, binary)
        return service_obj


class API(object):
    def __init__(self, transport=None, context=None, topic=None, server=None,
                 timeout=None):
        serializer = _init_serializer()
        if transport is None:
            exmods = rpc.get_allowed_exmods()
            transport = messaging.get_rpc_transport(
                CONF, allowed_remote_exmods=exmods)
        self._context = context
        if topic is None:
            topic = ''
        target = messaging.Target(topic=topic, server=server)
        self._client = messaging.RPCClient(transport, target,
                                           serializer=serializer,
                                           timeout=timeout)

    def _call(self, method, *args, **kwargs):
        return self._client.call(self._context, method, *args, **kwargs)

    def _cast(self, method, *args, **kwargs):
        self._client.cast(self._context, method, *args, **kwargs)

    def echo(self, message):
        self._cast('echo', message=message)
