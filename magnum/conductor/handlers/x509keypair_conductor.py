# Copyright 2015 NEC Corporation.  All rights reserved.
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


from oslo_log import log as logging

from magnum import objects

LOG = logging.getLogger(__name__)


class Handler(object):
    """Magnum X509KeyPair RPC handler.

    These are the backend operations. They are executed by the backend service.
    API calls via AMQP (within the ReST API) trigger the handlers to be called.

    """

    def __init__(self):
        super(Handler, self).__init__()

    def x509keypair_create(self, context, x509keypair):
        LOG.debug("Creating x509keypair")
        x509keypair.create(context)
        return x509keypair

    def x509keypair_delete(self, context, uuid):
        LOG.debug("Deleting x509keypair %s", uuid)
        x509keypair = objects.X509KeyPair.get_by_uuid(context, uuid)
        x509keypair.destroy(context)
