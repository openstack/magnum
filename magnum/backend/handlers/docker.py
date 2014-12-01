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

"""Magnum Docker RPC handler."""

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
        return None

    def bay_list():
        return None

    def bay_delete(uuid):
        return None

    def bay_show(uuid):
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
        LOG.debug("container_create %s contents=%s" % (uuid, contents))

    def container_list():
        LOG.debug("container_list")
        # return container list dict

    def container_delete(uuid):
        LOG.debug("cotainer_delete %s" % uuid)

    def container_show(uuid):
        LOG.debug("container_show %s" % uuid)
        # return container information dict

    def container_reboot(uuid):
        LOG.debug("container_reboot %s" % uuid)

    def container_stop(uuid):
        LOG.debug("container_stop %s" % uuid)

    def container_start(uuid):
        LOG.debug("container_start %s" % uuid)

    def container_pause(uuid):
        LOG.debug("container_pause %s" % uuid)

    def container_unpause(uuid):
        LOG.debug("container_unpause %s" % uuid)

    def container_logs(uuid):
        LOG.debug("container_logs %s" % uuid)

    def container_execute(uuid):
        LOG.debug("container_execute %s" % uuid)
