# Copyright 2015 NEC Corporation.  All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_utils import timeutils
import pecan
from pecan import rest
import wsme
from wsme import types as wtypes

from magnum.api.controllers import base
from magnum.api.controllers import link
from magnum.api.controllers.v1 import types
from magnum.api import expose
from magnum.api import utils as api_utils
from magnum.common import exception
from magnum.common import policy
from magnum import objects


class Certificate(base.APIBase):
    """API representation of a certificate.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a
    certificate.
    """

    _bay_uuid = None
    """uuid or logical name of bay"""

    _bay = None

    def _get_bay_uuid(self):
        return self._bay_uuid

    def _set_bay_uuid(self, value):
        if value and self._bay_uuid != value:
            try:
                self._bay = api_utils.get_resource('Bay', value)
                self._bay_uuid = self._bay.uuid
            except exception.BayNotFound as e:
                # Change error code because 404 (NotFound) is inappropriate
                # response for a POST request to create a Bay
                e.code = 400  # BadRequest
                raise e
        elif value == wtypes.Unset:
            self._bay_uuid = wtypes.Unset

    bay_uuid = wsme.wsproperty(wtypes.text, _get_bay_uuid,
                               _set_bay_uuid, mandatory=True)
    """The bay UUID or id"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated certificate links"""

    csr = wtypes.StringType(min_length=1)
    """"The Certificate Signing Request"""

    pem = wtypes.StringType()
    """"The Signed Certificate"""

    def __init__(self, **kwargs):
        super(Certificate, self).__init__()

        self.fields = []
        for field in objects.Certificate.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    def get_bay(self):
        if not self._bay:
            self._bay = api_utils.get_resource('Bay', self.bay_uuid)
        return self._bay

    @staticmethod
    def _convert_with_links(certificate, url, expand=True):
        if not expand:
            certificate.unset_fields_except(['bay_uuid', 'csr', 'pem'])

        certificate.links = [link.Link.make_link('self', url,
                                                 'certificates',
                                                 certificate.bay_uuid),
                             link.Link.make_link('bookmark', url,
                                                 'certificates',
                                                 certificate.bay_uuid,
                                                 bookmark=True)]
        return certificate

    @classmethod
    def convert_with_links(cls, rpc_cert, expand=True):
        cert = Certificate(**rpc_cert.as_dict())
        return cls._convert_with_links(cert,
                                       pecan.request.host_url, expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(bay_uuid='7ae81bb3-dec3-4289-8d6c-da80bd8001ae',
                     created_at=timeutils.utcnow(),
                     csr='AAA....AAA')
        return cls._convert_with_links(sample, 'http://localhost:9511', expand)


class CertificateController(rest.RestController):
    """REST controller for Certificate."""

    def __init__(self):
        super(CertificateController, self).__init__()

    _custom_actions = {
        'detail': ['GET'],
    }

    @expose.expose(Certificate, types.uuid_or_name)
    def get_one(self, bay_ident):
        """Retrieve CA information about the given bay.

        :param bay_ident: UUID of a bay or
        logical name of the bay.
        """
        context = pecan.request.context
        bay = api_utils.get_resource('Bay', bay_ident)
        policy.enforce(context, 'certificate:get', bay,
                       action='certificate:get')
        certificate = pecan.request.rpcapi.get_ca_certificate(bay)
        return Certificate.convert_with_links(certificate)

    @expose.expose(Certificate, body=Certificate, status_code=201)
    def post(self, certificate):
        """Sign a new certificate by the CA.

        :param certificate: a certificate within the request body.
        """
        context = pecan.request.context
        bay = certificate.get_bay()
        policy.enforce(context, 'certificate:create', bay,
                       action='certificate:create')
        certificate_dict = certificate.as_dict()
        certificate_dict['project_id'] = context.project_id
        certificate_dict['user_id'] = context.user_id
        cert_obj = objects.Certificate(context, **certificate_dict)

        new_cert = pecan.request.rpcapi.sign_certificate(bay,
                                                         cert_obj)
        return Certificate.convert_with_links(new_cert)
