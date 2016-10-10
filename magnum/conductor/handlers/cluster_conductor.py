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
from oslo_service import loopingcall
from oslo_utils import importutils
from pycadf import cadftaxonomy as taxonomy
import six

from magnum.common import clients
from magnum.common import exception
from magnum.conductor.handlers.common import cert_manager
from magnum.conductor.handlers.common import trust_manager
from magnum.conductor import scale_manager
from magnum.conductor import utils as conductor_utils
import magnum.conf
from magnum.drivers.common import driver
from magnum.i18n import _
from magnum.i18n import _LE
from magnum.i18n import _LI
from magnum import objects
from magnum.objects import fields

CONF = magnum.conf.CONF

LOG = logging.getLogger(__name__)


class Handler(object):

    def __init__(self):
        super(Handler, self).__init__()

    # Cluster Operations

    def cluster_create(self, context, cluster, create_timeout):
        LOG.debug('cluster_heat cluster_create')

        osc = clients.OpenStackClients(context)

        try:
            # Create trustee/trust and set them to cluster
            trust_manager.create_trustee_and_trust(osc, cluster)
            # Generate certificate and set the cert reference to cluster
            cert_manager.generate_certificates_to_cluster(cluster,
                                                          context=context)
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_CREATE, taxonomy.OUTCOME_PENDING)
            # Get driver
            ct = conductor_utils.retrieve_cluster_template(context, cluster)
            cluster_driver = driver.Driver.get_driver(ct.server_type,
                                                      ct.cluster_distro,
                                                      ct.coe)
            # Create cluster
            created_stack = cluster_driver.create_stack(context, osc, cluster,
                                                        create_timeout)
        except Exception as e:
            cluster.status = fields.ClusterStatus.CREATE_FAILED
            cluster.status_reason = six.text_type(e)
            cluster.create()
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_CREATE, taxonomy.OUTCOME_FAILURE)

            if isinstance(e, exc.HTTPBadRequest):
                e = exception.InvalidParameterValue(message=six.text_type(e))

                raise e
            raise

        cluster.stack_id = created_stack['stack']['id']
        cluster.status = fields.ClusterStatus.CREATE_IN_PROGRESS
        cluster.create()

        self._poll_and_check(osc, cluster, cluster_driver)

        return cluster

    def cluster_update(self, context, cluster, rollback=False):
        LOG.debug('cluster_heat cluster_update')

        osc = clients.OpenStackClients(context)
        stack = osc.heat().stacks.get(cluster.stack_id)
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
        if stack.stack_status not in allow_update_status:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_FAILURE)
            operation = _('Updating a cluster when stack status is '
                          '"%s"') % stack.stack_status
            raise exception.NotSupported(operation=operation)

        delta = cluster.obj_what_changed()
        if not delta:
            return cluster

        manager = scale_manager.get_scale_manager(context, osc, cluster)

        conductor_utils.notify_about_cluster_operation(
            context, taxonomy.ACTION_UPDATE, taxonomy.OUTCOME_PENDING)

        # Get driver
        ct = conductor_utils.retrieve_cluster_template(context, cluster)
        cluster_driver = driver.Driver.get_driver(ct.server_type,
                                                  ct.cluster_distro,
                                                  ct.coe)
        # Create cluster
        cluster_driver.update_stack(context, osc, cluster, manager, rollback)
        self._poll_and_check(osc, cluster, cluster_driver)

        return cluster

    def cluster_delete(self, context, uuid):
        LOG.debug('cluster_heat cluster_delete')
        osc = clients.OpenStackClients(context)
        cluster = objects.Cluster.get_by_uuid(context, uuid)

        stack_id = cluster.stack_id
        # NOTE(sdake): This will execute a stack_delete operation.  This will
        # Ignore HTTPNotFound exceptions (stack wasn't present).  In the case
        # that Heat couldn't find the stack representing the cluster, likely a
        # user has deleted the stack outside the context of Magnum.  Therefore
        # the contents of the cluster are forever lost.
        #
        # If the exception is unhandled, the original exception will be raised.
        try:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_DELETE, taxonomy.OUTCOME_PENDING)
            osc.heat().stacks.delete(stack_id)
        except exc.HTTPNotFound:
            LOG.info(_LI('The stack %s was not found during cluster'
                         ' deletion.'), stack_id)
            try:
                trust_manager.delete_trustee_and_trust(osc, context, cluster)
                cert_manager.delete_certificates_from_cluster(cluster,
                                                              context=context)
                cluster.destroy()
            except exception.ClusterNotFound:
                LOG.info(_LI('The cluster %s has been deleted by others.'),
                         uuid)
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_DELETE, taxonomy.OUTCOME_SUCCESS)
            return None
        except exc.HTTPConflict:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_DELETE, taxonomy.OUTCOME_FAILURE)
            raise exception.OperationInProgress(cluster_name=cluster.name)
        except Exception:
            conductor_utils.notify_about_cluster_operation(
                context, taxonomy.ACTION_DELETE, taxonomy.OUTCOME_FAILURE)
            raise

        cluster.status = fields.ClusterStatus.DELETE_IN_PROGRESS
        cluster.save()

        self._poll_and_check(osc, cluster)

        return None

    def _poll_and_check(self, osc, cluster, cluster_driver=None):
        poller = HeatPoller(osc, cluster, cluster_driver)
        lc = loopingcall.FixedIntervalLoopingCall(f=poller.poll_and_check)
        lc.start(CONF.cluster_heat.wait_interval, True)


class HeatPoller(object):

    def __init__(self, openstack_client, cluster, cluster_driver=None):
        self.openstack_client = openstack_client
        self.context = self.openstack_client.context
        self.cluster = cluster
        self.attempts = 0
        self.cluster_template = conductor_utils.retrieve_cluster_template(
            self.context, cluster)
        if cluster_driver:
            self.template_def = cluster_driver.get_template_definition()

    def poll_and_check(self):
        # TODO(yuanying): temporary implementation to update api_address,
        # node_addresses and cluster status
        stack = self.openstack_client.heat().stacks.get(self.cluster.stack_id)
        self.attempts += 1
        status_to_event = {
            fields.ClusterStatus.DELETE_COMPLETE: taxonomy.ACTION_DELETE,
            fields.ClusterStatus.CREATE_COMPLETE: taxonomy.ACTION_CREATE,
            fields.ClusterStatus.UPDATE_COMPLETE: taxonomy.ACTION_UPDATE,
            fields.ClusterStatus.ROLLBACK_COMPLETE: taxonomy.ACTION_UPDATE,
            fields.ClusterStatus.CREATE_FAILED: taxonomy.ACTION_CREATE,
            fields.ClusterStatus.DELETE_FAILED: taxonomy.ACTION_DELETE,
            fields.ClusterStatus.UPDATE_FAILED: taxonomy.ACTION_UPDATE,
            fields.ClusterStatus.ROLLBACK_FAILED: taxonomy.ACTION_UPDATE
        }
        # poll_and_check is detached and polling long time to check status,
        # so another user/client can call delete cluster/stack.
        if stack.stack_status == fields.ClusterStatus.DELETE_COMPLETE:
            self._delete_complete()
            conductor_utils.notify_about_cluster_operation(
                self.context, status_to_event[stack.stack_status],
                taxonomy.OUTCOME_SUCCESS)
            raise loopingcall.LoopingCallDone()

        if stack.stack_status in (fields.ClusterStatus.CREATE_COMPLETE,
                                  fields.ClusterStatus.UPDATE_COMPLETE):
            self._sync_cluster_and_template_status(stack)
            conductor_utils.notify_about_cluster_operation(
                self.context, status_to_event[stack.stack_status],
                taxonomy.OUTCOME_SUCCESS)
            raise loopingcall.LoopingCallDone()
        elif stack.stack_status != self.cluster.status:
            self._sync_cluster_status(stack)

        if stack.stack_status in (fields.ClusterStatus.CREATE_FAILED,
                                  fields.ClusterStatus.DELETE_FAILED,
                                  fields.ClusterStatus.UPDATE_FAILED,
                                  fields.ClusterStatus.ROLLBACK_COMPLETE,
                                  fields.ClusterStatus.ROLLBACK_FAILED):
            self._sync_cluster_and_template_status(stack)
            self._cluster_failed(stack)
            conductor_utils.notify_about_cluster_operation(
                self.context, status_to_event[stack.stack_status],
                taxonomy.OUTCOME_FAILURE)
            raise loopingcall.LoopingCallDone()
        # only check max attempts when the stack is being created when
        # the timeout hasn't been set. If the timeout has been set then
        # the loop will end when the stack completes or the timeout occurs
        if stack.stack_status == fields.ClusterStatus.CREATE_IN_PROGRESS:
            if (stack.timeout_mins is None and
               self.attempts > CONF.cluster_heat.max_attempts):
                LOG.error(_LE('Cluster check exit after %(attempts)s attempts,'
                              'stack_id: %(id)s, stack_status: %(status)s') %
                          {'attempts': CONF.cluster_heat.max_attempts,
                           'id': self.cluster.stack_id,
                           'status': stack.stack_status})
                raise loopingcall.LoopingCallDone()
        else:
            if self.attempts > CONF.cluster_heat.max_attempts:
                LOG.error(_LE('Cluster check exit after %(attempts)s attempts,'
                              'stack_id: %(id)s, stack_status: %(status)s') %
                          {'attempts': CONF.cluster_heat.max_attempts,
                           'id': self.cluster.stack_id,
                           'status': stack.stack_status})
                raise loopingcall.LoopingCallDone()

    def _delete_complete(self):
        LOG.info(_LI('Cluster has been deleted, stack_id: %s')
                 % self.cluster.stack_id)
        try:
            trust_manager.delete_trustee_and_trust(self.openstack_client,
                                                   self.context,
                                                   self.cluster)
            cert_manager.delete_certificates_from_cluster(self.cluster,
                                                          context=self.context)
            self.cluster.destroy()
        except exception.ClusterNotFound:
            LOG.info(_LI('The cluster %s has been deleted by others.')
                     % self.cluster.uuid)

    def _sync_cluster_status(self, stack):
        self.cluster.status = stack.stack_status
        self.cluster.status_reason = stack.stack_status_reason
        stack_nc_param = self.template_def.get_heat_param(
            cluster_attr='node_count')
        self.cluster.node_count = stack.parameters[stack_nc_param]
        self.cluster.save()

    def get_version_info(self, stack):
        stack_param = self.template_def.get_heat_param(
            cluster_attr='coe_version')
        if stack_param:
            self.cluster.coe_version = stack.parameters[stack_param]

        version_module_path = self.template_def.driver_module_path+'.version'
        try:
            ver = importutils.import_module(version_module_path)
            container_version = ver.container_version
        except Exception:
            container_version = None
        self.cluster.container_version = container_version

    def _sync_cluster_and_template_status(self, stack):
        self.template_def.update_outputs(stack, self.cluster_template,
                                         self.cluster)
        self.get_version_info(stack)
        self._sync_cluster_status(stack)

    def _cluster_failed(self, stack):
        LOG.error(_LE('Cluster error, stack status: %(cluster_status)s, '
                      'stack_id: %(stack_id)s, '
                      'reason: %(reason)s') %
                  {'cluster_status': stack.stack_status,
                   'stack_id': self.cluster.stack_id,
                   'reason': self.cluster.status_reason})
