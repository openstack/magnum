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

"""Magnum Conductor default handler."""

from magnum.openstack.common import log as logging

LOG = logging.getLogger(__name__)


# These are the database operations - They are executed by the conductor
# service.  API calls via AMQP trigger the handlers to be called.

class Handler(object):
    def __init__(self):
        super(Handler, self).__init__()
        # Open DB here I suspect

    def bay_get(uuid):
        LOG.debug("bay_get %s" % uuid)
        # return bay information dict

    def service_get(uuid):
        LOG.debug("service_get %s" % uuid)
        # return service information dict

    def pod_get(uuid):
        LOG.debug("pod_get %s" % uuid)
        # return pod information dict

    def container_get(uuid):
        LOG.debug("container_get %s" % uuid)
        # return container information dict

    def bay_put(uuid, contents):
        LOG.debug("bay_put %s contents=%s" % (uuid, contents))

    def service_put(uuid, contents):
        LOG.debug("service_put %s contents=%s" % (uuid, contents))

    def pod_put(uuid, contents):
        LOG.debug("pod_put %s contents=%s" % (uuid, contents))

    def container_put(uuid, contents):
        LOG.debug("container_put %s contents=%s" % (uuid, contents))

    def bay_delete(uuid):
        LOG.debug("bay_delete %s" % uuid)

    def service_delete(uuid):
        LOG.debug("bay_delete %s" % uuid)

    def pod_delete(uuid):
        LOG.debug("pod_delete %s" % uuid)

    def container_delete(uuid):
        LOG.debug("cotainer_delete %s" % uuid)

    def bay_list():
        LOG.debug("bay_list")
        # return bay list dict

    def service_list():
        LOG.debug("service_list")
        # return service list dict

    def pod_list():
        LOG.debug("pod_list")
        # return pod list dict

    def container_list():
        LOG.debug("container_list")
        # return container list dict
