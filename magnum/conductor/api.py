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

"""API for interfacing with Magnum Conductor."""

from oslo.config import cfg

from magnum.common.rpc import service


# The Conductor API class serves as a AMQP client for communicating
# on a topic exchange specific to the conductor.  This allows all database
# access to execute.

class API(service.API):
    def __init__(self, transport=None, context=None):
        cfg.CONF.import_opt('topic', 'magnum.conductor.config',
                            group='conductor')
        super(API, self).__init__(transport, context,
                                  topic=cfg.CONF.conductor.topic)

    # Get objects from database

    def bay_get(self, uuid):
        return self._call('bay_get', uuid=uuid)

    def service_get(self, uuid):
        return self._call('service_get', uuid=uuid)

    def pod_get(self, uuid):
        return self._call('pod_get', uuid=uuid)

    def container_get(self, uuid):
        return self._call('container_get', uuid=uuid)

    # Put objects into database

    def bay_put(self, uuid=None, contents=None):
        self._cast('bay_get', uuid=uuid, contents=contents)

    def service_put(self, uuid=None, contents=None):
        self._cast('service_get', uuid=uuid, contents=contents)

    def pod_put(self, uuid=None, contents=None):
        self._cast('pod_get', uuid=uuid, contents=contents)

    def container_put(self, uuid=None, contents=None):
        self._cast('container_get', uuid=uuid, contents=contents)

    # Delete objects from database

    def bay_delete(self, uuid):
        self._cast('bay_delete', uuid=uuid)

    def service_delete(self, uuid):
        self._cast('service_delete', uuid=uuid)

    def pod_delete(self, uuid):
        self._cast('pod_delete', uuid=uuid)

    def container_delete(self, uuid):
        self._cast('container_delete', uuid=uuid)

    # List objects from database
    #
    # TODO(sdake) - this could probably use some filters and
    # pagination for scalability

    def bay_list(self):
        return self._call('bay_list')

    def service_list(self):
        return self._call('service_list')

    def pod_list(self):
        return self._call('pod_list')

    def container_list(self):
        return self._call('container_list')
