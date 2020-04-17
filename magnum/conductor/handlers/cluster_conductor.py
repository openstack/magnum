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

    def cluster_create(self, context, cluster, master_count, node_count,
                       create_timeout):
        LOG.debug('cluster_heat cluster_create')

        osc = clients.OpenStackClients(context)

        cluster.status = fields.ClusterStatus.CREATE_IN_PROGRESS
        cluster.status_reason = None
        cluster.create()

        # Master nodegroup
        master_ng = conductor_utils._get_nodegroup_object(
            context, cluster, master_count, is_master=True)
        master_ng.create()
        # Minion nodegroup
        minion_ng = conductor_utils._get_nodegroup_object(
            context, cluster, node_count, is_master=False)
        minion_ng.create()

        try:
            # Create trustee/trust and set them to cluster
            trust_manager.create_trustee_and_trust(osc, cluster)
            # Generate certificate and set the cert reference to cluster
            cert_manager.generate_certificates_to_cluster(cluster,
                                                          context=context)
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_CREATE, taxonomy.OUTCOME_PENDING,
                cluster)
            # Get driver
            cluster_driver = driver.Driver.get_driver_for_cluster(context,
                                                                  cluster)
            # Create cluster
            cluster_driver.create_cluster(context, cluster, create_timeout)
            cluster.save()
            for ng in cluster.nodegroups:
                ng.stack_id = cluster.stack_id
                ng.save()

        except Exception as e:
            cluster.status = fields.ClusterStatus.CREATE_FAILED
            cluster.status_reason = six.text_type(e)
            cluster.save()
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_CREATE, taxonomy.OUTCOME_FAILURE,
                cluster)

            if isinstance(e, exc.HTTPBadRequest):
                e = exception.InvalidParameterValue(message=six.text_type(e))

                raise e
            raise

        return cluster

    def cluster_update(self, context, cluster, node_count,
                       health_status, health_status_reason, rollback=False):
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
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_FAILURE,
                cluster)
            operation = _('Updating a cluster when status is '
                          '"%s"') % cluster.status
            raise exception.NotSupported(operation=operation)

        # Updates will be only reflected to the default worker
        # nodegroup.
        worker_ng = cluster.default_ng_worker
        if (worker_ng.node_count == node_count and
                cluster.health_status == health_status and
                cluster.health_status_reason == health_status_reason):
            return

        cluster.health_status = health_status
        cluster.health_status_reason = health_status_reason

        # It's not necessary to trigger driver's cluster update if it's
        # only health status update
        if worker_ng.node_count == node_count:
            cluster.save()
            return cluster

        # Backup the old node count so that we can restore it
        # in case of an exception.
        old_node_count = worker_ng.node_count

        manager = scale_manager.get_scale_manager(context, osc, cluster)

        # Get driver
        ct = conductor_utils.retrieve_cluster_template(context, cluster)
        cluster_driver = driver.Driver.get_driver(ct.server_type,
                                                  ct.cluster_distro,
                                                  ct.coe)
        # Update cluster
        try:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_PENDING,
                cluster)
            worker_ng.node_count = node_count
            worker_ng.save()
            cluster_driver.update_cluster(context, cluster, manager, rollback)
            cluster.status = fields.ClusterStatus.UPDATE_IN_PROGRESS
            cluster.status_reason = None
        except Exception as e:
            cluster.status = fields.ClusterStatus.UPDATE_FAILED
            cluster.status_reason = six.text_type(e)
            cluster.save()
            # Restore the node_count
            worker_ng.node_count = old_node_count
            worker_ng.save()
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_FAILURE,
                cluster)
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
                context, taxonomy.ACTION_DELETE, taxonomy.OUTCOME_PENDING,
                cluster)
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
                # delete all cluster's nodegroups
                for ng in cluster.nodegroups:
                    ng.destroy()
                cluster.destroy()
            except exception.ClusterNotFound:
                LOG.info('The cluster %s has been deleted by others.',
                         uuid)
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_DELETE, taxonomy.OUTCOME_SUCCESS,
                cluster)
            return None
        except exc.HTTPConflict:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_DELETE, taxonomy.OUTCOME_FAILURE,
                cluster)
            raise exception.OperationInProgress(cluster_name=cluster.name)
        except Exception as unexp:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_DELETE, taxonomy.OUTCOME_FAILURE,
                cluster)
            cluster.status = fields.ClusterStatus.DELETE_FAILED
            cluster.status_reason = six.text_type(unexp)
            cluster.save()
            raise

        cluster.save()
        return None

    def cluster_resize(self, context, cluster,
                       node_count, nodes_to_remove, nodegroup):
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
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_FAILURE,
                cluster)
            operation = _('Resizing a cluster when status is '
                          '"%s"') % cluster.status
            raise exception.NotSupported(operation=operation)

        resize_manager = scale_manager.get_scale_manager(context, osc, cluster)

        # Get driver
        ct = conductor_utils.retrieve_cluster_template(context, cluster)
        cluster_driver = driver.Driver.get_driver(ct.server_type,
                                                  ct.cluster_distro,
                                                  ct.coe)
        # Backup the old node count so that we can restore it
        # in case of an exception.
        old_node_count = nodegroup.node_count

        # Resize cluster
        try:
            nodegroup.node_count = node_count
            nodegroup.status = fields.ClusterStatus.UPDATE_IN_PROGRESS
            nodegroup.save()
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_PENDING,
                cluster)
            cluster_driver.resize_cluster(context, cluster, resize_manager,
                                          node_count, nodes_to_remove,
                                          nodegroup)
            cluster.status = fields.ClusterStatus.UPDATE_IN_PROGRESS
            cluster.status_reason = None
        except Exception as e:
            cluster.status = fields.ClusterStatus.UPDATE_FAILED
            cluster.status_reason = six.text_type(e)
            cluster.save()
            nodegroup.node_count = old_node_count
            nodegroup.status = fields.ClusterStatus.UPDATE_FAILED
            nodegroup.status_reason = six.text_type(e)
            nodegroup.save()
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_FAILURE,
                cluster)
            if isinstance(e, exc.HTTPBadRequest):
                e = exception.InvalidParameterValue(message=six.text_type(e))
                raise e
            raise

        cluster.save()
        return cluster

    def cluster_upgrade(self, context, cluster, cluster_template,
                        max_batch_size, nodegroup, rollback=False):
        LOG.debug('cluster_conductor cluster_upgrade')

        # osc = clients.OpenStackClients(context)
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
            operation = _('Upgrading a cluster when status is '
                          '"%s"') % cluster.status
            raise exception.NotSupported(operation=operation)

        # Get driver
        ct = conductor_utils.retrieve_cluster_template(context, cluster)
        cluster_driver = driver.Driver.get_driver(ct.server_type,
                                                  ct.cluster_distro,
                                                  ct.coe)
        # Upgrade cluster
        try:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_PENDING,
                cluster)
            cluster_driver.upgrade_cluster(context, cluster, cluster_template,
                                           max_batch_size, nodegroup, rollback)
            cluster.status = fields.ClusterStatus.UPDATE_IN_PROGRESS
            nodegroup.status = fields.ClusterStatus.UPDATE_IN_PROGRESS
            cluster.status_reason = None
        except Exception as e:
            cluster.status = fields.ClusterStatus.UPDATE_FAILED
            cluster.status_reason = six.text_type(e)
            cluster.save()
            nodegroup.status = fields.ClusterStatus.UPDATE_FAILED
            nodegroup.status_reason = six.text_type(e)
            nodegroup.save()
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_FAILURE,
                cluster)
            if isinstance(e, exc.HTTPBadRequest):
                e = exception.InvalidParameterValue(message=six.text_type(e))
                raise e
            raise

        nodegroup.save()
        cluster.save()
        return cluster
