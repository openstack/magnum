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


class ClusterID(wtypes.Base):
    """API representation of a cluster ID

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a cluster
    ID.
    """

    uuid = types.uuid
    """Unique UUID for this cluster"""

    def __init__(self, uuid):
        self.uuid = uuid


class Certificate(base.APIBase):
    """API representation of a certificate.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a
    certificate.
    """

    _cluster_uuid = None
    """uuid or logical name of cluster"""

    _cluster = None

    def _get_cluster_uuid(self):
        return self._cluster_uuid

    def _set_cluster_uuid(self, value):
        if value and self._cluster_uuid != value:
            try:
                self._cluster = api_utils.get_resource('Cluster', value)
                self._cluster_uuid = self._cluster.uuid
            except exception.ClusterNotFound as e:
                # Change error code because 404 (NotFound) is inappropriate
                # response for a POST request to create a Cluster
                e.code = 400  # BadRequest
                raise
        elif value == wtypes.Unset:
            self._cluster_uuid = wtypes.Unset

    cluster_uuid = wsme.wsproperty(wtypes.text, _get_cluster_uuid,
                                   _set_cluster_uuid)
    """The cluster UUID or id"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated certificate links"""

    csr = wtypes.StringType(min_length=1)
    """"The Certificate Signing Request"""

    pem = wtypes.StringType()
    """"The Signed Certificate"""

    ca_cert_type = wtypes.StringType()
    """"The CA Certificate type the CSR will be signed by"""

    def __init__(self, **kwargs):
        super(Certificate, self).__init__()

        self.fields = []
        for field in objects.Certificate.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    def get_cluster(self):
        if not self._cluster:
            self._cluster = api_utils.get_resource('Cluster',
                                                   self.cluster_uuid)
        return self._cluster

    @staticmethod
    def _convert_with_links(certificate, url, expand=True):
        if not expand:
            certificate.unset_fields_except(['cluster_uuid',
                                             'csr', 'pem', 'ca_cert_type'])

        certificate.links = [link.Link.make_link('self', url,
                                                 'certificates',
                                                 certificate.cluster_uuid),
                             link.Link.make_link('bookmark', url,
                                                 'certificates',
                                                 certificate.cluster_uuid,
                                                 bookmark=True)]
        return certificate

    @classmethod
    def convert_with_links(cls, rpc_cert, expand=True):
        cert = Certificate(**rpc_cert.as_dict())
        return cls._convert_with_links(cert,
                                       pecan.request.host_url, expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(cluster_uuid='7ae81bb3-dec3-4289-8d6c-da80bd8001ae',
                     created_at=timeutils.utcnow(),
                     csr='AAA....AAA',
                     ca_cert_type='kubernetes')
        return cls._convert_with_links(sample, 'http://localhost:9511', expand)


class CertificateController(base.Controller):
    """REST controller for Certificate."""

    def __init__(self):
        super(CertificateController, self).__init__()

    _custom_actions = {
        'detail': ['GET'],
    }

    @expose.expose(Certificate, types.uuid_or_name, wtypes.text)
    def get_one(self, cluster_ident, ca_cert_type=None):
        """Retrieve CA information about the given cluster.

        :param cluster_ident: UUID of a cluster or
        logical name of the cluster.
        """
        context = pecan.request.context
        cluster = api_utils.get_resource('Cluster', cluster_ident)
        policy.enforce(context, 'certificate:get', cluster.as_dict(),
                       action='certificate:get')
        certificate = pecan.request.rpcapi.get_ca_certificate(cluster,
                                                              ca_cert_type)
        return Certificate.convert_with_links(certificate)

    @expose.expose(Certificate, body=Certificate, status_code=201)
    def post(self, certificate):
        """Sign a new certificate by the CA.

        :param certificate: a certificate within the request body.
        """
        context = pecan.request.context
        cluster = certificate.get_cluster()
        policy.enforce(context, 'certificate:create', cluster.as_dict(),
                       action='certificate:create')
        certificate_dict = certificate.as_dict()
        certificate_dict['project_id'] = context.project_id
        certificate_dict['user_id'] = context.user_id
        cert_obj = objects.Certificate(context, **certificate_dict)

        new_cert = pecan.request.rpcapi.sign_certificate(cluster,
                                                         cert_obj)
        return Certificate.convert_with_links(new_cert)

    @expose.expose(ClusterID, types.uuid_or_name, status_code=202)
    def patch(self, cluster_ident):
        context = pecan.request.context
        cluster = api_utils.get_resource('Cluster', cluster_ident)
        policy.enforce(context, 'certificate:rotate_ca', cluster.as_dict(),
                       action='certificate:rotate_ca')
        if cluster.cluster_template.tls_disabled:
            raise exception.NotSupported("Rotating the CA certificate on a "
                                         "non-TLS cluster is not supported")

        pecan.request.rpcapi.rotate_ca_certificate(cluster)

        return ClusterID(cluster.uuid)
