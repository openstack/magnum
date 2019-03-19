# Copyright 2014 NEC Corporation.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from heatclient import exc
from oslo_log import log as logging
from pycadf import cadftaxonomy as taxonomy
import six

from magnum.common import clients
from magnum.common import exception
from magnum.common import profiler
from magnum.conductor.handlers.common import cert_manager
from magnum.conductor.handlers.common import trust_manager
from magnum.conductor import scale_manager
from magnum.conductor import utils as conductor_utils
import magnum.conf
from magnum.drivers.common import driver
from magnum.i18n import _
from magnum import objects
from magnum.objects import fields

CONF = magnum.conf.CONF

LOG = logging.getLogger(__name__)


@profiler.trace_cls("rpc")
class Handler(object):

    def __init__(self):
        super(Handler, self).__init__()

    # Cluster Operations

    def cluster_create(self, context, cluster, create_timeout):
        LOG.debug('cluster_heat cluster_create')

        osc = clients.OpenStackClients(context)

        cluster.status = fields.ClusterStatus.CREATE_IN_PROGRESS
        cluster.status_reason = None
        cluster.create()

        try:
            # Create trustee/trust and set them to cluster
            trust_manager.create_trustee_and_trust(osc, cluster)
            # Generate certificate and set the cert reference to cluster
            cert_manager.generate_certificates_to_cluster(cluster,
                                                          context=context)
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_CREATE, taxonomy.OUTCOME_PENDING)
            # Get driver
            cluster_driver = driver.Driver.get_driver_for_cluster(context,
                                                                  cluster)
            # Create cluster
            cluster_driver.create_cluster(context, cluster, create_timeout)
            cluster.save()

        except Exception as e:
            cluster.status = fields.ClusterStatus.CREATE_FAILED
            cluster.status_reason = six.text_type(e)
            cluster.save()
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_CREATE, taxonomy.OUTCOME_FAILURE)

            if isinstance(e, exc.HTTPBadRequest):
                e = exception.InvalidParameterValue(message=six.text_type(e))

                raise e
            raise

        return cluster

    def cluster_update(self, context, cluster, rollback=False):
        LOG.debug('cluster_heat cluster_update')

        osc = clients.OpenStackClients(context)
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
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_FAILURE)
            operation = _('Updating a cluster when status is '
                          '"%s"') % cluster.status
            raise exception.NotSupported(operation=operation)

        delta = cluster.obj_what_changed()
        if not delta:
            return cluster

        manager = scale_manager.get_scale_manager(context, osc, cluster)

        # Get driver
        ct = conductor_utils.retrieve_cluster_template(context, cluster)
        cluster_driver = driver.Driver.get_driver(ct.server_type,
                                                  ct.cluster_distro,
                                                  ct.coe)
        # Update cluster
        try:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_PENDING)
            cluster_driver.update_cluster(context, cluster, manager, rollback)
            cluster.status = fields.ClusterStatus.UPDATE_IN_PROGRESS
            cluster.status_reason = None
        except Exception as e:
            cluster.status = fields.ClusterStatus.UPDATE_FAILED
            cluster.status_reason = six.text_type(e)
            cluster.save()
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_FAILURE)
            if isinstance(e, exc.HTTPBadRequest):
                e = exception.InvalidParameterValue(message=six.text_type(e))
                raise e
            raise

        cluster.save()
        return cluster

    def cluster_delete(self, context, uuid):
        LOG.debug('cluster_conductor cluster_delete')
        osc = clients.OpenStackClients(context)
        cluster = objects.Cluster.get_by_uuid(context, uuid)
        ct = conductor_utils.retrieve_cluster_template(context, cluster)
        cluster_driver = driver.Driver.get_driver(ct.server_type,
                                                  ct.cluster_distro,
                                                  ct.coe)
        try:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_DELETE, taxonomy.OUTCOME_PENDING)
            cluster_driver.delete_cluster(context, cluster)
            cluster.status = fields.ClusterStatus.DELETE_IN_PROGRESS
            cluster.status_reason = None
        except exc.HTTPNotFound:
            LOG.info('The cluster %s was not found during cluster'
                     ' deletion.', cluster.id)
            try:
                trust_manager.delete_trustee_and_trust(osc, context, cluster)
                cert_manager.delete_certificates_from_cluster(cluster,
                                                              context=context)
                cluster.destroy()
            except exception.ClusterNotFound:
                LOG.info('The cluster %s has been deleted by others.',
                         uuid)
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_DELETE, taxonomy.OUTCOME_SUCCESS)
            return None
        except exc.HTTPConflict:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_DELETE, taxonomy.OUTCOME_FAILURE)
            raise exception.OperationInProgress(cluster_name=cluster.name)
        except Exception as unexp:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_DELETE, taxonomy.OUTCOME_FAILURE)
            cluster.status = fields.ClusterStatus.DELETE_FAILED
            cluster.status_reason = six.text_type(unexp)
            cluster.save()
            raise

        cluster.save()
        return None

    def cluster_resize(self, context, cluster,
                       node_count, nodes_to_remove, nodegroup=None):
        LOG.debug('cluster_conductor cluster_resize')

        osc = clients.OpenStackClients(context)
        # NOTE(flwang): One of important user cases of /resize API is
        # supporting the auto scaling action triggered by Kubernetes Cluster
        # Autoscaler, so there are 2 cases may happen:
        # 1. API could be triggered very offen
        # 2. Scale up or down may fail and we would like to offer the ability
        #    that recover the cluster to allow it being resized when last
        #    update failed.
        allow_update_status = (
            fields.ClusterStatus.CREATE_COMPLETE,
            fields.ClusterStatus.UPDATE_COMPLETE,
            fields.ClusterStatus.RESUME_COMPLETE,
            fields.ClusterStatus.RESTORE_COMPLETE,
            fields.ClusterStatus.ROLLBACK_COMPLETE,
            fields.ClusterStatus.SNAPSHOT_COMPLETE,
            fields.ClusterStatus.CHECK_COMPLETE,
            fields.ClusterStatus.ADOPT_COMPLETE,
            fields.ClusterStatus.UPDATE_FAILED,
            fields.ClusterStatus.UPDATE_IN_PROGRESS,
        )
        if cluster.status not in allow_update_status:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_FAILURE)
            operation = _('Resizing a cluster when status is '
                          '"%s"') % cluster.status
            raise exception.NotSupported(operation=operation)

        resize_manager = scale_manager.get_scale_manager(context, osc, cluster)

        # Get driver
        ct = conductor_utils.retrieve_cluster_template(context, cluster)
        cluster_driver = driver.Driver.get_driver(ct.server_type,
                                                  ct.cluster_distro,
                                                  ct.coe)
        # Resize cluster
        try:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_PENDING)
            cluster_driver.resize_cluster(context, cluster, resize_manager,
                                          node_count, nodes_to_remove,
                                          nodegroup)
            cluster.status = fields.ClusterStatus.UPDATE_IN_PROGRESS
            cluster.status_reason = None
        except Exception as e:
            cluster.status = fields.ClusterStatus.UPDATE_FAILED
            cluster.status_reason = six.text_type(e)
            cluster.save()
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_FAILURE)
            if isinstance(e, exc.HTTPBadRequest):
                e = exception.InvalidParameterValue(message=six.text_type(e))
                raise e
            raise

        cluster.save()
        return cluster
