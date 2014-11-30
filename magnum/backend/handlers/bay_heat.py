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

"""Magnum Bay Heat RPC handler."""

from magnum.openstack.common import log as logging

LOG = logging.getLogger(__name__)


# These are the backend operations.  They are executed by the backend
# service.  API calls via AMQP (within the ReST API) trigger the handlers to
# be called.

class Handler(object):
    def __init__(self):
        super(Handler, self).__init__()

    # Bay Operations

    def bay_create(id, name, type):
        LOG.debug('heat bay_create\n')
        return None

    def bay_list():
        LOG.debug('heat bay_list\n')
        return None

    def bay_delete(uuid):
        LOG.debug('heat bay_delete\n')
        return None

    def bay_show(uuid):
        LOG.debug('heat bay_show\n')
        return None

    # Service Operations

    def service_create(uuid, contents):
        return None

    def service_list():
        return None

    def service_delete():
        return None

    def service_show(uuid):
        return None

    # Pod Operations

    def pod_create(uuid, contents):
        return None

    def pod_list():
        return None

    def pod_delete(uuid):
        return None

    def pod_show(uuid):
        return None

    # Container operations

    def container_create(uuid, contents):
        return None

    def container_list():
        return None

    def container_delete(uuid):
        return None

    def container_show(uuid):
        return None

    def container_reboot(uuid):
        return None

    def container_stop(uuid):
        return None

    def container_start(uuid):
        return None

    def container_pause(uuid):
        return None

    def container_unpause(uuid):
        return None

    def container_logs(uuid):
        return None

    def container_execute(uuid):
        return None
