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

from magnum.conductor.handlers.common import cert_manager
from magnum import objects
LOG = logging.getLogger(__name__)


class Handler(object):
    """Magnum CA RPC handler.

    These are the backend operations. They are executed by the backend service.
    API calls via AMQP (within the ReST API) trigger the handlers to be called.

    """

    def __init__(self):
        super(Handler, self).__init__()

    def sign_certificate(self, context, bay, certificate):
        LOG.debug("Creating self signed x509 certificate")
        signed_cert = cert_manager.sign_node_certificate(bay,
                                                         certificate.csr)
        certificate.pem = signed_cert
        return certificate

    def get_ca_certificate(self, context, bay):
        ca_cert = cert_manager.get_bay_ca_certificate(bay)
        certificate = objects.Certificate.from_object_bay(bay)
        certificate.pem = ca_cert.get_certificate()
        return certificate
