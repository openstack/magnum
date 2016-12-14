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

import abc
import os
import six

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import importutils

from heatclient.common import template_utils
from heatclient import exc as heatexc

from magnum.common import clients
from magnum.common import context as mag_ctx
from magnum.common import exception
from magnum.common import short_id
from magnum.conductor.handlers.common import cert_manager
from magnum.conductor.handlers.common import trust_manager
from magnum.conductor import utils as conductor_utils
from magnum.drivers.common import driver
from magnum.i18n import _
from magnum.i18n import _LE
from magnum.i18n import _LI
from magnum.objects import fields


LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class HeatDriver(driver.Driver):
    '''Base Driver class for using Heat

       Abstract class for implementing Drivers that leverage OpenStack Heat for
       orchestrating cluster lifecycle operations
    '''

    def _extract_template_definition(self, context, cluster,
                                     scale_manager=None):
        cluster_template = conductor_utils.retrieve_cluster_template(context,
                                                                     cluster)
        definition = self.get_template_definition()
        return definition.extract_definition(context, cluster_template,
                                             cluster,
                                             scale_manager=scale_manager)

    def _get_env_files(self, template_path, env_rel_paths):
        template_dir = os.path.dirname(template_path)
        env_abs_paths = [os.path.join(template_dir, f) for f in env_rel_paths]
        environment_files = []
        env_map, merged_env = (
            template_utils.process_multiple_environments_and_files(
                env_paths=env_abs_paths, env_list_tracker=environment_files))
        return environment_files, env_map

    @abc.abstractmethod
    def get_template_definition(self):
        '''return an implementation of

           magnum.drivers.common.drivers.heat.TemplateDefinition
        '''

        raise NotImplementedError("Must implement 'get_template_definition'")

    def update_cluster_status(self, context, cluster):
        stack_ctx = mag_ctx.make_cluster_context(cluster)
        poller = HeatPoller(clients.OpenStackClients(stack_ctx), context,
                            cluster, self)
        poller.poll_and_check()

    def create_cluster(self, context, cluster, cluster_create_timeout):
        stack = self._create_stack(context, clients.OpenStackClients(context),
                                   cluster, cluster_create_timeout)
        # TODO(randall): keeping this for now to reduce/eliminate data
        # migration. Should probably come up with something more generic in
        # the future once actual non-heat-based drivers are implemented.
        cluster.stack_id = stack['stack']['id']

    def update_cluster(self, context, cluster, scale_manager=None,
                       rollback=False):
        self._update_stack(context, clients.OpenStackClients(context), cluster,
                           scale_manager, rollback)

    def delete_cluster(self, context, cluster):
        self._delete_stack(context, clients.OpenStackClients(context), cluster)

    def _create_stack(self, context, osc, cluster, cluster_create_timeout):
        template_path, heat_params, env_files = (
            self._extract_template_definition(context, cluster))

        tpl_files, template = template_utils.get_template_contents(
            template_path)

        environment_files, env_map = self._get_env_files(template_path,
                                                         env_files)
        tpl_files.update(env_map)

        # Make sure no duplicate stack name
        stack_name = '%s-%s' % (cluster.name, short_id.generate_id())
        if cluster_create_timeout:
            heat_timeout = cluster_create_timeout
        else:
            # no cluster_create_timeout value was passed in to the request
            # so falling back on configuration file value
            heat_timeout = cfg.CONF.cluster_heat.create_timeout
        fields = {
            'stack_name': stack_name,
            'parameters': heat_params,
            'environment_files': environment_files,
            'template': template,
            'files': tpl_files,
            'timeout_mins': heat_timeout
        }
        created_stack = osc.heat().stacks.create(**fields)

        return created_stack

    def _update_stack(self, context, osc, cluster, scale_manager=None,
                      rollback=False):
        template_path, heat_params, env_files = (
            self._extract_template_definition(context, cluster,
                                              scale_manager=scale_manager))

        tpl_files, template = template_utils.get_template_contents(
            template_path)
        environment_files, env_map = self._get_env_files(template_path,
                                                         env_files)
        tpl_files.update(env_map)

        fields = {
            'parameters': heat_params,
            'environment_files': environment_files,
            'template': template,
            'files': tpl_files,
            'disable_rollback': not rollback
        }

        osc.heat().stacks.update(cluster.stack_id, **fields)

    def _delete_stack(self, context, osc, cluster):
        osc.heat().stacks.delete(cluster.stack_id)


class HeatPoller(object):

    def __init__(self, openstack_client, context, cluster, cluster_driver):
        self.openstack_client = openstack_client
        self.context = context
        self.cluster = cluster
        self.cluster_template = conductor_utils.retrieve_cluster_template(
            self.context, cluster)
        self.template_def = cluster_driver.get_template_definition()

    def poll_and_check(self):
        # TODO(yuanying): temporary implementation to update api_address,
        # node_addresses and cluster status
        try:
            stack = self.openstack_client.heat().stacks.get(
                self.cluster.stack_id)
        except heatexc.NotFound:
            self._sync_missing_heat_stack()
            return

        # poll_and_check is detached and polling long time to check status,
        # so another user/client can call delete cluster/stack.
        if stack.stack_status == fields.ClusterStatus.DELETE_COMPLETE:
            self._delete_complete()

        if stack.stack_status in (fields.ClusterStatus.CREATE_COMPLETE,
                                  fields.ClusterStatus.UPDATE_COMPLETE):
            self._sync_cluster_and_template_status(stack)
        elif stack.stack_status != self.cluster.status:
            self._sync_cluster_status(stack)

        if stack.stack_status in (fields.ClusterStatus.CREATE_FAILED,
                                  fields.ClusterStatus.DELETE_FAILED,
                                  fields.ClusterStatus.UPDATE_FAILED,
                                  fields.ClusterStatus.ROLLBACK_COMPLETE,
                                  fields.ClusterStatus.ROLLBACK_FAILED):
            self._sync_cluster_and_template_status(stack)
            self._cluster_failed(stack)

    def _delete_complete(self):
        LOG.info(_LI('Cluster has been deleted, stack_id: %s')
                 % self.cluster.stack_id)
        try:
            trust_manager.delete_trustee_and_trust(self.openstack_client,
                                                   self.context,
                                                   self.cluster)
            cert_manager.delete_certificates_from_cluster(self.cluster,
                                                          context=self.context)
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

    def _sync_missing_heat_stack(self):
        if self.cluster.status == fields.ClusterStatus.DELETE_IN_PROGRESS:
            self._delete_complete()
        elif self.cluster.status == fields.ClusterStatus.CREATE_IN_PROGRESS:
            self._sync_missing_stack(fields.ClusterStatus.CREATE_FAILED)
        elif self.cluster.status == fields.ClusterStatus.UPDATE_IN_PROGRESS:
            self._sync_missing_stack(fields.ClusterStatus.UPDATE_FAILED)

    def _sync_missing_stack(self, new_status):
        self.cluster.status = new_status
        self.cluster.status_reason = _("Stack with id %s not found in "
                                       "Heat.") % self.cluster.stack_id
        self.cluster.save()
        LOG.info(_LI("Cluster with id %(id)s has been set to "
                     "%(status)s due to stack with id %(sid)s "
                     "not found in Heat."),
                 {'id': self.cluster.id, 'status': self.cluster.status,
                  'sid': self.cluster.stack_id})
