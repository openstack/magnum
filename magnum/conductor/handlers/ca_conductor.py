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

from heatclient import exc
from oslo_log import log as logging
from pycadf import cadftaxonomy as taxonomy

from magnum.common import exception
from magnum.common import profiler
from magnum.conductor.handlers.common import cert_manager
from magnum.conductor import utils as conductor_utils
from magnum.drivers.common import driver
from magnum.i18n import _
from magnum import objects
from magnum.objects import fields

LOG = logging.getLogger(__name__)


@profiler.trace_cls("rpc")
class Handler(object):
    """Magnum CA RPC handler.

    These are the backend operations. They are executed by the backend service.
    API calls via AMQP (within the ReST API) trigger the handlers to be called.

    """

    def __init__(self):
        super(Handler, self).__init__()

    def sign_certificate(self, context, cluster, certificate):
        LOG.debug("Creating self signed x509 certificate")
        try:
            ca_cert_type = certificate.ca_cert_type
        except Exception:
            LOG.debug("There is no CA cert type specified for the CSR")
            ca_cert_type = "kubernetes"

        signed_cert = cert_manager.sign_node_certificate(cluster,
                                                         certificate.csr,
                                                         ca_cert_type,
                                                         context=context)
        if isinstance(signed_cert, bytes):
            certificate.pem = signed_cert.decode()
        else:
            certificate.pem = signed_cert
        return certificate

    def get_ca_certificate(self, context, cluster, ca_cert_type=None):
        ca_cert = cert_manager.get_cluster_ca_certificate(
            cluster, context=context, ca_cert_type=ca_cert_type)
        certificate = objects.Certificate.from_object_cluster(cluster)
        if isinstance(ca_cert.get_certificate(), bytes):
            certificate.pem = ca_cert.get_certificate().decode()
        else:
            certificate.pem = ca_cert.get_certificate()
        return certificate

    def rotate_ca_certificate(self, context, cluster):
        LOG.info('start rotate_ca_certificate for cluster: %s', cluster.uuid)

        allow_update_status = (
            fields.ClusterStatus.CREATE_COMPLETE,
            fields.ClusterStatus.UPDATE_COMPLETE,
            fields.ClusterStatus.RESUME_COMPLETE,
            fields.ClusterStatus.RESTORE_COMPLETE,
            fields.ClusterStatus.ROLLBACK_COMPLETE,
            fields.ClusterStatus.SNAPSHOT_COMPLETE,
            fields.ClusterStatus.CHECK_COMPLETE,
            fields.ClusterStatus.ADOPT_COMPLETE
        )
        if cluster.status not in allow_update_status:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_FAILURE,
                cluster)
            operation = _('Updating a cluster when status is '
                          '"%s"') % cluster.status
            raise exception.NotSupported(operation=operation)

        try:
            # re-generate the ca certs
            cert_manager.generate_certificates_to_cluster(cluster,
                                                          context=context)
            cluster_driver = driver.Driver.get_driver_for_cluster(context,
                                                                  cluster)
            cluster_driver.rotate_ca_certificate(context, cluster)
            cluster.status = fields.ClusterStatus.UPDATE_IN_PROGRESS
            cluster.status_reason = None
        except Exception as e:
            cluster.status = fields.ClusterStatus.UPDATE_FAILED
            cluster.status_reason = str(e)
            cluster.save()
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_FAILURE,
                cluster)
            if isinstance(e, exc.HTTPBadRequest):
                e = exception.InvalidParameterValue(message=str(e))
                raise e
            raise

        cluster.save()
        return cluster
