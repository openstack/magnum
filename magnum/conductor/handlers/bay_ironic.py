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

"""Magnum Bay Ironic RPC handler."""

from magnum import objects
from magnum.openstack.common import log as logging

LOG = logging.getLogger(__name__)


# These are the backend operations.  They are executed by the backend
# service.  API calls via AMQP (within the ReST API) trigger the handlers to
# be called.

class Handler(object):
    def __init__(self):
        super(Handler, self).__init__()

    # Bay Operations

    def bay_create(self, context, bay):
        LOG.debug('ironic bay_create')
        bay.create()
        return bay

    def bay_delete(self, context, uuid):
        LOG.debug('ironic bay_delete')
        bay = objects.Bay.get_by_uuid(context, uuid)
        bay.destroy()
        return None

    def bay_show(self, context, uuid):
        LOG.debug('ironic bay_show')
        bay = objects.Bay.get_by_uuid(context, uuid)
        return bay
