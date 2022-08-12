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
import collections
import os
from pbr.version import SemanticVersion as SV
import six

from string import ascii_letters
from string import digits

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import importutils

from heatclient.common import template_utils
from heatclient import exc as heatexc

from magnum.common import clients
from magnum.common import context as mag_ctx
from magnum.common import exception
from magnum.common import keystone
from magnum.common import octavia
from magnum.common import short_id
from magnum.common.x509 import operations as x509
from magnum.conductor.handlers.common import cert_manager
from magnum.conductor.handlers.common import trust_manager
from magnum.conductor import utils as conductor_utils
from magnum.drivers.common import driver
from magnum.drivers.common import k8s_monitor
from magnum.i18n import _
from magnum.objects import fields

LOG = logging.getLogger(__name__)


NodeGroupStatus = collections.namedtuple('NodeGroupStatus',
                                         'name status reason is_default')


@six.add_metaclass(abc.ABCMeta)
class HeatDriver(driver.Driver):
    """Base Driver class for using Heat

       Abstract class for implementing Drivers that leverage OpenStack Heat for
       orchestrating cluster lifecycle operations
    """

    def _extract_template_definition_up(self, context, cluster,
                                        cluster_template,
                                        scale_manager=None):
        ct_obj = conductor_utils.retrieve_ct_by_name_or_uuid(
            context,
            cluster_template)
        definition = self.get_template_definition()
        return definition.extract_definition(context, ct_obj,
                                             cluster,
                                             scale_manager=scale_manager)

    def _extract_template_definition(self, context, cluster,
                                     scale_manager=None,
                                     nodegroups=None):
        cluster_template = conductor_utils.retrieve_cluster_template(context,
                                                                     cluster)
        definition = self.get_template_definition()
        return definition.extract_definition(context, cluster_template,
                                             cluster,
                                             nodegroups=nodegroups,
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
        """return an implementation of

           magnum.drivers.common.drivers.heat.TemplateDefinition
        """

        raise NotImplementedError("Must implement 'get_template_definition'")

    def create_federation(self, context, federation):
        return NotImplementedError("Must implement 'create_federation'")

    def update_federation(self, context, federation):
        return NotImplementedError("Must implement 'update_federation'")

    def delete_federation(self, context, federation):
        return NotImplementedError("Must implement 'delete_federation'")

    def update_nodegroup(self, context, cluster, nodegroup):
        # we just need to save the nodegroup here. This is because,
        # at the moment, this method is used to update min and max node
        # counts.
        nodegroup.save()

    def delete_nodegroup(self, context, cluster, nodegroup):
        # Default nodegroups share stack_id so it will be deleted
        # as soon as the cluster gets destroyed
        if not nodegroup.stack_id:
            nodegroup.destroy()
        else:
            osc = clients.OpenStackClients(context)
            self._delete_stack(context, osc, nodegroup.stack_id)

    def update_cluster_status(self, context, cluster, use_admin_ctx=False):
        if cluster.stack_id is None:
            # NOTE(mgoddard): During cluster creation it is possible to poll
            # the cluster before its heat stack has been created. See bug
            # 1682058.
            return
        if use_admin_ctx:
            stack_ctx = context
        else:
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
        self._update_stack(context, cluster, scale_manager, rollback)

    def create_nodegroup(self, context, cluster, nodegroup):
        stack = self._create_stack(context, clients.OpenStackClients(context),
                                   cluster, cluster.create_timeout,
                                   nodegroup=nodegroup)
        nodegroup.stack_id = stack['stack']['id']

    def get_nodegroup_extra_params(self, cluster, osc):
        raise NotImplementedError("Must implement "
                                  "'get_nodegroup_extra_params'")

    @abc.abstractmethod
    def upgrade_cluster(self, context, cluster, cluster_template,
                        max_batch_size, nodegroup, scale_manager=None,
                        rollback=False):
        raise NotImplementedError("Must implement 'upgrade_cluster'")

    def delete_cluster(self, context, cluster):
        self.pre_delete_cluster(context, cluster)

        LOG.info("Starting to delete cluster %s", cluster.uuid)
        osc = clients.OpenStackClients(context)
        for ng in cluster.nodegroups:
            ng.status = fields.ClusterStatus.DELETE_IN_PROGRESS
            ng.save()
            if ng.is_default:
                continue
            self._delete_stack(context, osc, ng.stack_id)
        self._delete_stack(context, osc, cluster.default_ng_master.stack_id)

    def resize_cluster(self, context, cluster, resize_manager,
                       node_count, nodes_to_remove, nodegroup=None,
                       rollback=False):
        self._resize_stack(context, cluster, resize_manager,
                           node_count, nodes_to_remove, nodegroup=nodegroup,
                           rollback=rollback)

    def _create_stack(self, context, osc, cluster, cluster_create_timeout,
                      nodegroup=None):

        nodegroups = [nodegroup] if nodegroup else None
        template_path, heat_params, env_files = (
            self._extract_template_definition(context, cluster,
                                              nodegroups=nodegroups))

        tpl_files, template = template_utils.get_template_contents(
            template_path)

        environment_files, env_map = self._get_env_files(template_path,
                                                         env_files)
        tpl_files.update(env_map)

        # Make sure we end up with a valid hostname
        valid_chars = set(ascii_letters + digits + '-')

        # valid hostnames are 63 chars long, leaving enough room
        # to add the random id (for uniqueness)
        if nodegroup is None:
            stack_name = cluster.name[:30]
        else:
            stack_name = "%s-%s" % (cluster.name[:20], nodegroup.name[:9])
        stack_name = stack_name.replace('_', '-')
        stack_name = stack_name.replace('.', '-')
        stack_name = ''.join(filter(valid_chars.__contains__, stack_name))

        # Make sure no duplicate stack name
        stack_name = '%s-%s' % (stack_name, short_id.generate_id())
        stack_name = stack_name.lower()
        if cluster_create_timeout:
            heat_timeout = cluster_create_timeout
        else:
            # no cluster_create_timeout value was passed in to the request
            # so falling back on configuration file value
            heat_timeout = cfg.CONF.cluster_heat.create_timeout

        heat_params['is_cluster_stack'] = nodegroup is None

        if nodegroup:
            # In case we are creating a new stack for a new nodegroup then
            # we need to extract more params.
            heat_params.update(self.get_nodegroup_extra_params(cluster, osc))

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

    def _update_stack(self, context, cluster, scale_manager=None,
                      rollback=False):
        # update worked properly only for scaling nodes up and down
        # before nodegroups. Maintain this logic until we deprecate
        # and remove the command.
        # Fixed behaviour Id84e5d878b21c908021e631514c2c58b3fe8b8b0
        nodegroup = cluster.default_ng_worker
        definition = self.get_template_definition()
        scale_params = definition.get_scale_params(
            context,
            cluster,
            nodegroup.node_count,
            scale_manager,
            nodes_to_remove=None)

        fields = {
            'parameters': scale_params,
            'existing': True,
            'disable_rollback': not rollback
        }

        LOG.info('Updating cluster %s stack %s with these params: %s',
                 cluster.uuid, nodegroup.stack_id, scale_params)
        osc = clients.OpenStackClients(context)
        osc.heat().stacks.update(nodegroup.stack_id, **fields)

    def _resize_stack(self, context, cluster, resize_manager,
                      node_count, nodes_to_remove, nodegroup=None,
                      rollback=False):
        definition = self.get_template_definition()
        scale_params = definition.get_scale_params(
            context,
            cluster,
            nodegroup.node_count,
            resize_manager,
            nodes_to_remove=nodes_to_remove)

        fields = {
            'parameters': scale_params,
            'existing': True,
            'disable_rollback': not rollback
        }

        LOG.info('Resizing cluster %s stack %s with these params: %s',
                 cluster.uuid, nodegroup.stack_id, scale_params)
        osc = clients.OpenStackClients(context)
        osc.heat().stacks.update(nodegroup.stack_id, **fields)

    def _delete_stack(self, context, osc, stack_id):
        osc.heat().stacks.delete(stack_id)


class KubernetesDriver(HeatDriver):
    """Base driver for Kubernetes clusters."""

    def get_monitor(self, context, cluster):
        return k8s_monitor.K8sMonitor(context, cluster)

    def get_scale_manager(self, context, osclient, cluster):
        # FIXME: Until the kubernetes client is fixed, remove
        # the scale_manager.
        # https://bugs.launchpad.net/magnum/+bug/1746510
        return None

    def pre_delete_cluster(self, context, cluster):
        """Delete cloud resources before deleting the cluster."""
        if keystone.is_octavia_enabled():
            LOG.info("Starting to delete loadbalancers for cluster %s",
                     cluster.uuid)
            octavia.delete_loadbalancers(context, cluster)

    def upgrade_cluster(self, context, cluster, cluster_template,
                        max_batch_size, nodegroup, scale_manager=None,
                        rollback=False):
        raise NotImplementedError("Must implement 'upgrade_cluster'")


class FedoraKubernetesDriver(KubernetesDriver):
    """Base driver for Kubernetes clusters."""

    def get_heat_params(self, cluster_template):
        heat_params = {}
        try:
            kube_tag = cluster_template.labels["kube_tag"]
            kube_tag_params = {
                "kube_tag": kube_tag,
                "kube_version": kube_tag,
                "master_kube_tag": kube_tag,
                "minion_kube_tag": kube_tag,
            }
            heat_params.update(kube_tag_params)
        except KeyError:
            LOG.debug(("Cluster template %s does not contain a "
                       "valid kube_tag"), cluster_template.name)

        # If both keys are present, only ostree_commit is chosen.
        for ostree_tag in ["ostree_commit", "ostree_remote"]:
            if ostree_tag not in cluster_template.labels:
                continue
            try:
                ostree_param = {
                    ostree_tag: cluster_template.labels[ostree_tag]
                }
                heat_params.update(ostree_param)
                break
            except KeyError:
                LOG.debug("Cluster template %s does not define %s",
                          cluster_template.name, ostree_tag)

        upgrade_labels = ['kube_tag', 'ostree_remote', 'ostree_commit']
        if not any([u in heat_params.keys() for u in upgrade_labels]):
            reason = ("Cluster template %s does not contain any supported "
                      "upgrade labels: [%s]") % (cluster_template.name,
                                                 ', '.join(upgrade_labels))
            raise exception.InvalidClusterTemplateForUpgrade(reason=reason)

        return heat_params

    @staticmethod
    def get_new_labels(nodegroup, cluster_template):
        new_labels = nodegroup.labels.copy()
        if 'kube_tag' in cluster_template.labels:
            new_kube_tag = cluster_template.labels['kube_tag']
            new_labels.update({'kube_tag': new_kube_tag})
        return new_labels

    def upgrade_cluster(self, context, cluster, cluster_template,  # noqa: C901
                        max_batch_size, nodegroup, scale_manager=None,
                        rollback=False):
        osc = clients.OpenStackClients(context)

        # Use this just to check that we are not downgrading.
        heat_params = {
            "update_max_batch_size": max_batch_size,
        }

        if 'kube_tag' in nodegroup.labels:
            heat_params['kube_tag'] = nodegroup.labels['kube_tag']

        current_addons = {}
        new_addons = {}
        for label in cluster_template.labels:
            # This is upgrade API, so we don't introduce new stuff by this API,
            # but just focus on the version change.
            new_addons[label] = cluster_template.labels[label]
            if ((label.endswith('_tag') or
                 label.endswith('_version')) and label in heat_params):
                current_addons[label] = heat_params[label]
                try:
                    if (SV.from_pip_string(new_addons[label]) <
                            SV.from_pip_string(current_addons[label])):
                        raise exception.InvalidVersion(tag=label)
                except exception.InvalidVersion:
                    raise
                except Exception as e:
                    # NOTE(flwang): Different cloud providers may use different
                    # tag/version format which maybe not able to parse by
                    # SemanticVersion. For this case, let's just skip it.
                    LOG.debug("Failed to parse tag/version %s", str(e))

        # Since the above check passed just
        # hardcode what we want to send to heat.
        # Rules: 1. No downgrade 2. Explicitly override 3. Merging based on set
        # Update heat_params based on the data generated above
        heat_params.update(self.get_heat_params(cluster_template))

        stack_id = nodegroup.stack_id
        if nodegroup is not None and not nodegroup.is_default:
            heat_params['is_cluster_stack'] = False
            # For now set the worker_role explicitly in order to
            # make sure that the is_master condition fails.
            heat_params['worker_role'] = nodegroup.role

        # we need to set the whole dict to the object
        # and not just update the existing labels. This
        # is how obj_what_changed works.
        nodegroup.labels = new_labels = self.get_new_labels(nodegroup,
                                                            cluster_template)

        if nodegroup.is_default:
            cluster.cluster_template_id = cluster_template.uuid
            cluster.labels = new_labels
            if nodegroup.role == 'master':
                other_default_ng = cluster.default_ng_worker
            else:
                other_default_ng = cluster.default_ng_master
            other_default_ng.labels = new_labels
            other_default_ng.save()

        fields = {
            'existing': True,
            'parameters': heat_params,
            'disable_rollback': not rollback
        }
        LOG.info('Upgrading cluster %s stack %s with these params: %s',
                 cluster.uuid, nodegroup.stack_id, heat_params)
        osc.heat().stacks.update(stack_id, **fields)

    def get_nodegroup_extra_params(self, cluster, osc):
        network = osc.heat().resources.get(cluster.stack_id, 'network')
        secgroup = osc.heat().resources.get(cluster.stack_id,
                                            'secgroup_kube_minion')
        for output in osc.heat().stacks.get(cluster.stack_id).outputs:
            if output['output_key'] == 'api_address':
                api_address = output['output_value']
                break
        extra_params = {
            'existing_master_private_ip': api_address,
            'existing_security_group': secgroup.attributes['id'],
            'fixed_network': network.attributes['fixed_network'],
            'fixed_subnet': network.attributes['fixed_subnet'],
        }
        return extra_params

    def rotate_ca_certificate(self, context, cluster):
        cluster_template = conductor_utils.retrieve_cluster_template(context,
                                                                     cluster)
        if cluster_template.cluster_distro not in ["fedora-coreos"]:
            raise exception.NotSupported("Rotating the CA certificate is "
                                         "not supported for cluster with "
                                         "cluster_distro: %s." %
                                         cluster_template.cluster_distro)
        osc = clients.OpenStackClients(context)
        rollback = True
        heat_params = {}

        csr_keys = x509.generate_csr_and_key(u"Kubernetes Service Account")

        heat_params['kube_service_account_key'] = \
            csr_keys["public_key"].replace("\n", "\\n")
        heat_params['kube_service_account_private_key'] = \
            csr_keys["private_key"].replace("\n", "\\n")

        fields = {
            'existing': True,
            'parameters': heat_params,
            'disable_rollback': not rollback
        }
        osc.heat().stacks.update(cluster.stack_id, **fields)


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
        ng_statuses = list()
        self.default_ngs = list()
        for nodegroup in self.cluster.nodegroups:
            self.nodegroup = nodegroup
            if self.nodegroup.is_default:
                self.default_ngs.append(self.nodegroup)
            status = self.extract_nodegroup_status()
            # In case a non-default nodegroup is deleted, None
            # is returned. We shouldn't add None in the list
            if status is not None:
                ng_statuses.append(status)
        self.aggregate_nodegroup_statuses(ng_statuses)

    def extract_nodegroup_status(self):

        if self.nodegroup.stack_id is None:
            # There is a slight window for a race condition here. If
            # a nodegroup is created and just before the stack_id is
            # assigned to it, this periodic task is executed, the
            # periodic task would try to find the status of the
            # stack with id = None. At that time the nodegroup status
            # is already set to CREATE_IN_PROGRESS by the conductor.
            # Keep this status for this loop until the stack_id is assigned.
            return NodeGroupStatus(name=self.nodegroup.name,
                                   status=self.nodegroup.status,
                                   is_default=self.nodegroup.is_default,
                                   reason=self.nodegroup.status_reason)

        try:
            # Do not resolve outputs by default. Resolving all
            # node IPs is expensive on heat.
            stack = self.openstack_client.heat().stacks.get(
                self.nodegroup.stack_id, resolve_outputs=False)

            if stack.stack_status in (fields.ClusterStatus.CREATE_COMPLETE,
                                      fields.ClusterStatus.UPDATE_COMPLETE):
                # Resolve all outputs if the stack is COMPLETE
                stack = self.openstack_client.heat().stacks.get(
                    self.nodegroup.stack_id, resolve_outputs=True)

                self._sync_cluster_and_template_status(stack)
            elif stack.stack_status != self.nodegroup.status:
                self.template_def.nodegroup_output_mappings = list()
                self.template_def.update_outputs(
                    stack, self.cluster_template, self.cluster,
                    nodegroups=[self.nodegroup])
                self._sync_cluster_status(stack)

            # poll_and_check is detached and polling long time to check
            # status, so another user/client can call delete cluster/stack.
            if stack.stack_status == fields.ClusterStatus.DELETE_COMPLETE:
                if self.nodegroup.is_default:
                    self._check_delete_complete()
                else:
                    self.nodegroup.destroy()
                    return

            if stack.stack_status in (fields.ClusterStatus.CREATE_FAILED,
                                      fields.ClusterStatus.DELETE_FAILED,
                                      fields.ClusterStatus.UPDATE_FAILED,
                                      fields.ClusterStatus.ROLLBACK_COMPLETE,
                                      fields.ClusterStatus.ROLLBACK_FAILED):
                self._sync_cluster_and_template_status(stack)
                self._nodegroup_failed(stack)
        except heatexc.NotFound:
            self._sync_missing_heat_stack()
        return NodeGroupStatus(name=self.nodegroup.name,
                               status=self.nodegroup.status,
                               is_default=self.nodegroup.is_default,
                               reason=self.nodegroup.status_reason)

    def aggregate_nodegroup_statuses(self, ng_statuses):
        # NOTE(ttsiouts): Aggregate the nodegroup statuses and set the
        # cluster overall status.
        FAILED = '_FAILED'
        IN_PROGRESS = '_IN_PROGRESS'
        COMPLETE = '_COMPLETE'
        UPDATE = 'UPDATE'
        DELETE = 'DELETE'

        previous_state = self.cluster.status
        self.cluster.status_reason = None

        non_default_ngs_exist = any(not ns.is_default for ns in ng_statuses)
        # Both default nodegroups will have the same status so it's
        # enough to check one of them.
        default_ng_status = self.cluster.default_ng_master.status
        # Whatever action is going on in a cluster that has
        # non-default ngs, we call it update except for delete.
        action = DELETE if default_ng_status.startswith(DELETE) else UPDATE
        # Keep priority to the states below
        for state in (IN_PROGRESS, FAILED, COMPLETE):
            if any(ns.status.endswith(state) for ns in ng_statuses):
                if non_default_ngs_exist:
                    status = getattr(fields.ClusterStatus, action+state)
                else:
                    # If there are no non-default NGs
                    # just use the default NG's status.
                    status = default_ng_status
                self.cluster.status = status
                break

        if self.cluster.status == fields.ClusterStatus.CREATE_COMPLETE:
            # Consider the scenario where the user:
            # - creates the cluster (cluster: create_complete)
            # - adds a nodegroup (cluster: update_complete)
            # - deletes the nodegroup
            # The cluster should go to CREATE_COMPLETE only if the previous
            # state was CREATE_COMPLETE or CREATE_IN_PROGRESS. In all other
            # cases, just go to UPDATE_COMPLETE.
            if previous_state not in (fields.ClusterStatus.CREATE_COMPLETE,
                                      fields.ClusterStatus.CREATE_IN_PROGRESS):
                self.cluster.status = fields.ClusterStatus.UPDATE_COMPLETE

        # Summarize the failed reasons.
        if self.cluster.status.endswith(FAILED):
            reasons = ["%s failed" % (ns.name)
                       for ns in ng_statuses
                       if ns.status.endswith(FAILED)]
            self.cluster.status_reason = ', '.join(reasons)

        self.cluster.save()

    def _delete_complete(self):
        LOG.info('Cluster has been deleted, stack_id: %s',
                 self.cluster.stack_id)
        try:
            trust_manager.delete_trustee_and_trust(self.openstack_client,
                                                   self.context,
                                                   self.cluster)
            cert_manager.delete_certificates_from_cluster(self.cluster,
                                                          context=self.context)
            cert_manager.delete_client_files(self.cluster,
                                             context=self.context)

        except exception.ClusterNotFound:
            LOG.info('The cluster %s has been deleted by others.',
                     self.cluster.uuid)

    def _sync_cluster_status(self, stack):
        self.nodegroup.status = stack.stack_status
        self.nodegroup.status_reason = stack.stack_status_reason
        self.nodegroup.save()

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
        self.template_def.nodegroup_output_mappings = list()
        self.template_def.update_outputs(stack, self.cluster_template,
                                         self.cluster,
                                         nodegroups=[self.nodegroup])
        self.get_version_info(stack)
        self._sync_cluster_status(stack)

    def _nodegroup_failed(self, stack):
        LOG.error('Nodegroup error, stack status: %(ng_status)s, '
                  'stack_id: %(stack_id)s, '
                  'reason: %(reason)s',
                  {'ng_status': stack.stack_status,
                   'stack_id': self.nodegroup.stack_id,
                   'reason': self.nodegroup.status_reason})

    def _sync_missing_heat_stack(self):
        if self.nodegroup.status == fields.ClusterStatus.DELETE_IN_PROGRESS:
            self._sync_missing_stack(fields.ClusterStatus.DELETE_COMPLETE)
            if self.nodegroup.is_default:
                self._check_delete_complete()
        elif self.nodegroup.status == fields.ClusterStatus.CREATE_IN_PROGRESS:
            self._sync_missing_stack(fields.ClusterStatus.CREATE_FAILED)
        elif self.nodegroup.status == fields.ClusterStatus.UPDATE_IN_PROGRESS:
            self._sync_missing_stack(fields.ClusterStatus.UPDATE_FAILED)

    def _check_delete_complete(self):
        default_ng_statuses = [ng.status for ng in self.default_ngs]
        if all(status == fields.ClusterStatus.DELETE_COMPLETE
               for status in default_ng_statuses):
            self._delete_complete()

    def _sync_missing_stack(self, new_status):
        self.nodegroup.status = new_status
        self.nodegroup.status_reason = _("Stack with id %s not found in "
                                         "Heat.") % self.cluster.stack_id
        self.nodegroup.save()
        LOG.info("Nodegroup with id %(id)s has been set to "
                 "%(status)s due to stack with id %(sid)s "
                 "not found in Heat.",
                 {'id': self.nodegroup.uuid, 'status': self.nodegroup.status,
                  'sid': self.nodegroup.stack_id})
