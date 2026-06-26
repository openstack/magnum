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
import copy
import hashlib
import os
from pbr.version import SemanticVersion as SV
import six
import json
import datetime
import yaml

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
from magnum.common.x509 import operations as x509
from magnum.common import cinder_cleanup
from magnum.common import keystone
from magnum.common import octavia
from magnum.common import short_id
from magnum.conductor.handlers.common import cert_manager
from magnum.conductor.handlers.common import trust_manager
from magnum.conductor import utils as conductor_utils
from magnum.drivers.common import driver
from magnum.drivers.common import k8s_monitor
from magnum.drivers.heat import template_def as heat_tdef
from magnum.i18n import _
from magnum.objects import fields

LOG = logging.getLogger(__name__)


NodeGroupStatus = collections.namedtuple(
    "NodeGroupStatus", "name status reason is_default"
)


def _heat_param_type_for_value(value):
    """Infer the Heat parameter ``type`` for a live stack value.

    Used when re-declaring a dropped parameter during rolling migration so
    the injected declaration accepts the value Heat already stored.  Heat
    ``stack.parameters`` values are usually strings, so this mostly yields
    ``string``; the other branches just harden the rare non-string case so
    we never inject a ``type: string`` that rejects a bool/number/list value.
    """
    # bool is a subclass of int, so check it first.
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, (list, tuple)):
        return "comma_delimited_list"
    if isinstance(value, dict):
        return "json"
    return "string"


@six.add_metaclass(abc.ABCMeta)
class HeatDriver(driver.Driver):
    """Base Driver class for using Heat

    Abstract class for implementing Drivers that leverage OpenStack Heat for
    orchestrating cluster lifecycle operations
    """

    def _extract_template_definition_up(
        self, context, cluster, cluster_template, scale_manager=None
    ):
        ct_obj = conductor_utils.retrieve_ct_by_name_or_uuid(context, cluster_template)
        definition = self.get_template_definition()
        return definition.extract_definition(
            context, ct_obj, cluster, scale_manager=scale_manager
        )

    def _extract_template_definition(
        self, context, cluster, scale_manager=None, nodegroups=None
    ):
        cluster_template = conductor_utils.retrieve_cluster_template(context, cluster)
        definition = self.get_template_definition()
        return definition.extract_definition(
            context,
            cluster_template,
            cluster,
            nodegroups=nodegroups,
            scale_manager=scale_manager,
        )

    def _get_driver_for_nodegroup(self, context, nodegroup):
        """Return the driver that owns a nodegroup's templates.

        Non-default nodegroups may carry a ``cluster_template_id`` label
        that points to a different cluster template (and therefore a
        different driver) than the cluster itself.  Returns ``self`` when
        no override is present.
        """
        ng_labels = nodegroup.labels or {}
        ct_id = ng_labels.get("cluster_template_id")
        if ct_id:
            ct = conductor_utils.retrieve_ct_by_name_or_uuid(context, ct_id)
            return driver.Driver.get_driver(ct.server_type, ct.cluster_distro, ct.coe)
        return self

    def _extract_template_definition_for_nodegroup(self, context, cluster, nodegroup):
        """Like _extract_template_definition but uses the nodegroup's driver."""
        ng_driver = self._get_driver_for_nodegroup(context, nodegroup)
        cluster_template = conductor_utils.retrieve_cluster_template(context, cluster)
        definition = ng_driver.get_template_definition()
        return definition.extract_definition(
            context, cluster_template, cluster, nodegroups=[nodegroup]
        )

    def _mark_config_unhealthy_in_child_stacks(
        self, osc, parent_stack_id, group_name, config_name
    ):
        """Mark SoftwareConfig and its deployment unhealthy in all child
        stacks of a ResourceGroup so Heat recreates them instead of
        reading the (possibly deleted) old config."""
        try:
            group = osc.heat().resources.get(parent_stack_id, group_name)
        except Exception:
            return
        try:
            members = osc.heat().resources.list(group.physical_resource_id)
        except Exception:
            return
        deploy_name = config_name + "_deployment"
        for member in members:
            child_stack_id = member.physical_resource_id
            if not child_stack_id:
                continue
            for resource_name in (config_name, deploy_name):
                try:
                    osc.heat().resources.mark_unhealthy(
                        child_stack_id,
                        resource_name,
                        True,
                        "pre-template-migration: avoid stale SoftwareConfig reference",
                    )
                    LOG.debug(
                        "Marked %s in %s as unhealthy", resource_name, child_stack_id
                    )
                except Exception as exc:
                    LOG.debug(
                        "Could not mark %s unhealthy in %s: %s",
                        resource_name,
                        child_stack_id,
                        exc,
                    )

    def _mark_failed_nested_resources_unhealthy(self, osc, stack_id):
        """Mark Octavia resources that crash Heat's datetime comparison.

        Octavia's Heat resource plugin compares a resource's ``updated_at``
        during stack update. A resource that is FAILED, or that was created
        but NEVER updated (``updated_at`` is None), makes that comparison
        raise ``'<' not supported between instances of 'datetime.datetime'
        and 'NoneType'`` and fails the whole stack update. On the FIRST
        update of an old multi-master cluster this hits the per-master LBaaS
        pool members (api_lb / etcd_lb), which were created once under the
        legacy templates and have ``updated_at`` None — surfacing as
        ``resources.kube_masters: resources[1]: '<' not supported ...``.

        Marking such resources unhealthy tells Heat to RECREATE them instead
        of diffing against missing/None state. Gating on
        FAILED-or-updated_at-None is self-limiting: after one successful
        update the timestamps are set and nothing more is marked, so steady
        clusters are untouched.
        """
        # Octavia resources are the ones with the datetime(None) comparison
        # bug. PoolMember is included: each master registers itself to the
        # api_lb and etcd_lb pools, and those members are exactly what trips
        # the crash on the first migration update.
        lb_resource_types = (
            "Magnum::Optional::Neutron::LBaaS::LoadBalancer",
            "Magnum::Optional::Neutron::LBaaS::Listener",
            "Magnum::Optional::Neutron::LBaaS::Pool",
            "Magnum::Optional::Neutron::LBaaS::PoolMember",
            "Magnum::Optional::Neutron::LBaaS::HealthMonitor",
            "Magnum::Optional::Neutron::LBaaS::FloatingIP",
        )
        # List ALL nested resources (no status filter): the triggering pool
        # members are CREATE_COMPLETE, not FAILED, so a FAILED-only query
        # would miss them.
        try:
            resources = osc.heat().resources.list(stack_id, nested_depth=2)
        except Exception as e:
            LOG.warning("Could not list nested resources for stack %s: %s", stack_id, e)
            return

        for res in resources:
            if res.resource_type not in lb_resource_types:
                continue
            status = getattr(res, "resource_status", "") or ""
            updated_at = getattr(res, "updated_time", None)
            # Only the two conditions that trigger the Octavia datetime crash.
            if "FAILED" not in status and updated_at is not None:
                continue
            try:
                stack_link = [l for l in res.links if l.get("rel") == "stack"]
                if not stack_link:
                    continue
                href = stack_link[0]["href"]
                res_stack_id = href.split("/")[-1]
                osc.heat().resources.mark_unhealthy(
                    res_stack_id,
                    res.resource_name,
                    True,
                    "pre-update: force recreate to avoid Octavia datetime(None) compare",
                )
                LOG.info(
                    "Marked Octavia resource %s (%s, status=%s, updated_at=%s) "
                    "in stack %s as unhealthy",
                    res.resource_name,
                    res.resource_type,
                    status,
                    updated_at,
                    res_stack_id,
                )
            except Exception as exc:
                LOG.warning("Could not mark %s unhealthy: %s", res.resource_name, exc)

    def _prepare_stack_for_template_update(self, osc, stack_id):
        """Mark problematic resources unhealthy before a template update.

        Handles two cases:
        1. SoftwareConfig resources that reference deleted configs
        2. CREATE_FAILED nested resources (LB listeners, pools) that
           crash Octavia's Heat plugin on datetime comparison
        """
        for group_name, config_name in (
            ("kube_masters", "master_config"),
            ("kube_minions", "node_config"),
        ):
            self._mark_config_unhealthy_in_child_stacks(
                osc, stack_id, group_name, config_name
            )
        self._mark_failed_nested_resources_unhealthy(osc, stack_id)

    def _get_update_timeout(self):
        return cfg.CONF.cluster_heat.update_timeout

    def _get_reconcile_timestamp(self):
        return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    def _set_non_rotation_stack_flags(self, params, is_upgrade=False, is_resize=False):
        # CA rotation is opt-in. When ordinary stack updates omit the
        # parameter, Heat preserves the previous value and later node
        # reconciles can incorrectly re-enter CA rotation.
        params["ca_rotation_id"] = ""
        params["is_upgrade"] = is_upgrade
        params["is_resize"] = is_resize
        return params

    def _get_env_files(self, template_path, env_rel_paths):
        template_dir = os.path.dirname(template_path)
        env_abs_paths = [os.path.join(template_dir, f) for f in env_rel_paths]
        environment_files = []
        env_map, merged_env = template_utils.process_multiple_environments_and_files(
            env_paths=env_abs_paths, env_list_tracker=environment_files
        )
        return environment_files, env_map

    @staticmethod
    def _alias_resource_group_child_templates_for_rolling_migration(
        template, tpl_files
    ):
        """Avoid old/new child-template file collisions during migration.

        Heat ResourceGroup rolling updates keep old member definitions for
        nodes outside the current batch.  Heat merges the update's ``files`` on
        top of the stack's stored files (``new_files = current_stack.t.files;
        new_files.update(files)`` for ``existing=True`` updates), so reusing the
        same child-template filename (kubemaster.yaml/kubeminion.yaml)
        overwrites the old child content with the new one.  Old member
        definitions then fail validation against the new child template before
        their batch is reached (e.g. ``Unknown Property heapster_enabled``).

        Point new ResourceGroup members at a content-stamped alias filename and
        do not send the new child template under the old name.  The merge keeps
        each generation's child content under its own key, so non-batch members
        always validate against the exact content they were created with while
        updated members validate against the new alias.

        The alias is stamped with a short hash of the new child content rather
        than a fixed suffix, so every template generation gets a distinct,
        never-overwritten filename.  This keeps rolling migration correct across
        repeated property-dropping upgrades (a fixed alias collides again on the
        second such hop and re-introduces the validation failure).  Identical
        content yields an identical alias, so re-running the same upgrade is
        idempotent and does not churn the stored file set.

        Returns ``(template, aliased)`` where ``aliased`` maps each rewritten
        group name to the original (pre-alias) child key, so the pin step can
        restore genuine pre-migration content under that key.
        """
        if isinstance(template, dict):
            parsed = copy.deepcopy(template)
            return_dict = True
        else:
            parsed = yaml.safe_load(template) or {}
            return_dict = False

        # group name -> child template filename it must point at
        aliases = {
            "kube_masters": "kubemaster.yaml",
            "kube_minions": "kubeminion.yaml",
        }

        changed = False
        aliased = {}
        resources = parsed.get("resources") or {}
        for group_name, child_name in aliases.items():
            group = resources.get(group_name) or {}
            properties = group.get("properties") or {}
            resource_def = properties.get("resource_def") or {}
            child_ref = resource_def.get("type")
            if not isinstance(child_ref, six.string_types):
                continue
            if not child_ref.endswith(child_name):
                continue
            if child_ref not in tpl_files:
                # Group present but its child template is not in the file map.
                # Should not happen (heatclient keys files and rewrites the
                # ``type`` to the same absolute URL), but log it so a silent
                # no-op here does not quietly reintroduce the multi-node
                # validation failure.
                LOG.warning(
                    "Rolling-migration alias: %s for %s not found in template "
                    "files; skipping (multi-node upgrade may fail validation)",
                    child_ref,
                    group_name,
                )
                continue

            content = tpl_files[child_ref]
            raw = content.encode("utf-8") if isinstance(
                content, six.string_types
            ) else content
            digest = hashlib.sha1(raw).hexdigest()[:10]
            # strip the trailing ".yaml" and stamp with the content hash
            alias_ref = "%s%s-%s.yaml" % (
                child_ref[: -len(child_name)],
                child_name[:-5],
                digest,
            )
            if alias_ref == child_ref:
                continue

            resource_def["type"] = alias_ref
            tpl_files[alias_ref] = tpl_files[child_ref]
            tpl_files.pop(child_ref, None)
            aliased[group_name] = child_ref
            changed = True
            LOG.info(
                "Rolling-migration alias %s -> %s for group %s",
                child_ref,
                alias_ref,
                group_name,
            )

        if not changed:
            return template, aliased
        if return_dict:
            return parsed, aliased
        return yaml.safe_dump(parsed, default_flow_style=False), aliased

    @staticmethod
    def _pin_existing_child_templates_from_members(
        osc, parent_stack_id, aliased, tpl_files
    ):
        """Pin genuine pre-migration child content under the original key.

        The alias step alone only protects clusters that have never had a
        failed migration attempt.  Once an attempt runs, Heat stores the new
        (aliased) parent template, but the existing ResourceGroup member
        definitions in the *nested* group stack still reference the original
        child filename (e.g. kubemaster.yaml) carrying the old, now-removed
        properties (heapster_enabled, ...).  Heat's existing-update file merge
        (``new_files = current_stack.t.files; new_files.update(files)``) keeps
        whatever content is already stored under that key — which, after a
        prior attempt, is the *new* child content — so those old member
        definitions keep failing validation (``Unknown Property
        heapster_enabled``) and the cluster can never be retried.

        The member stacks themselves are never touched (the update dies during
        group validation, before any node), so each still stores its original
        child template.  Fetch one and pin it under the original key, which
        overrides any polluted content and makes recovery independent of what
        the stored parent files contain (and of convergence mode).
        """
        for group_name, orig_ref in (aliased or {}).items():
            try:
                group = osc.heat().resources.get(parent_stack_id, group_name)
                group_stack_id = getattr(group, "physical_resource_id", None)
                if not group_stack_id:
                    continue

                # Pick a member still defined with the original child type
                # (i.e. not yet migrated); its stored child template is the
                # authoritative pre-migration content.  Robust to partially
                # migrated groups, where some members already use the alias.
                group_tmpl = osc.heat().stacks.template(group_stack_id)
                member_defs = group_tmpl.get("resources") or {}
                target = None
                for mname, mdef in member_defs.items():
                    if (mdef or {}).get("type") == orig_ref:
                        target = mname
                        break
                if target is None:
                    continue

                member_stack_id = None
                for res in osc.heat().resources.list(group_stack_id):
                    if getattr(res, "resource_name", None) == target:
                        member_stack_id = getattr(
                            res, "physical_resource_id", None
                        )
                        break
                if not member_stack_id:
                    continue

                old_child = osc.heat().stacks.template(member_stack_id)
                tpl_files[orig_ref] = json.dumps(old_child)
                LOG.info(
                    "Pinned pre-migration child %s for group %s from member "
                    "%s (%s)",
                    orig_ref,
                    group_name,
                    target,
                    member_stack_id,
                )
            except Exception as e:
                LOG.warning(
                    "Could not pin pre-migration child for group %s (%s): %s; "
                    "retry of a previously failed migration may still fail "
                    "validation",
                    group_name,
                    orig_ref,
                    e,
                )

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
        poller = HeatPoller(clients.OpenStackClients(stack_ctx), context, cluster, self)
        poller.poll_and_check()

    def create_cluster(self, context, cluster, cluster_create_timeout):
        stack = self._create_stack(
            context, clients.OpenStackClients(context), cluster, cluster_create_timeout
        )
        # TODO(randall): keeping this for now to reduce/eliminate data
        # migration. Should probably come up with something more generic in
        # the future once actual non-heat-based drivers are implemented.
        cluster.stack_id = stack["stack"]["id"]

    def update_cluster(self, context, cluster, scale_manager=None, rollback=False):
        self._update_stack(context, cluster, scale_manager, rollback)

    def reconfigure_cluster(self, context, cluster):
        """Re-extract template params from cluster labels and push directly
        to each node's child stack. Used for label-only updates (enable/disable
        addons, change chart versions) without a full Kubernetes upgrade.

        Uses the same direct child-stack update pattern as rotate_ca_certificate
        to update all nodes simultaneously instead of going through the
        ResourceGroup rolling update.

        Does NOT set is_upgrade=True, so the reconciler treats it as a normal
        reconcile run — no drain/uncordon, no service restarts unless configs
        actually changed.
        """
        osc = clients.OpenStackClients(context)

        # Re-extract full template definition with updated labels.
        # This picks up all label changes (addon flags, chart versions, etc.)
        _, heat_params, _ = self._extract_template_definition(context, cluster)

        # Filter out None values — these are params not set in cluster
        # labels/template (e.g. etcd_volume_size comes from the cluster
        # template, not labels, so labels.get() returns None).  We must
        # not overwrite existing child stack values with None, or Heat
        # will reject the update with "Parameter was not provided".
        heat_params = {k: v for k, v in heat_params.items() if v is not None}

        heat_params["is_upgrade"] = "false"
        heat_params["is_resize"] = "false"
        heat_params["timestamp_upgrade"] = self._get_reconcile_timestamp()

        # Only update master nodegroup child stacks. Cluster addons
        # (Helm releases, RBAC, etc.) only run on master-0, so there's
        # no need to trigger workers for addon reconfiguration.
        master_ng = cluster.default_ng_master
        if not master_ng or not master_ng.stack_id:
            LOG.warning("No master nodegroup stack found for cluster %s", cluster.uuid)
            return

        stack_ids = self._get_nested_stack_ids(osc, cluster.stack_id, master_ng)
        if not stack_ids:
            LOG.warning(
                "Could not resolve master member stacks for "
                "cluster %s during reconfigure",
                cluster.uuid,
            )
            return

        stack_fields = self._get_nested_stack_update_template_fields(context, master_ng)

        for stack_id in stack_ids:
            for rn in ("master_config", "master_config_deployment"):
                try:
                    osc.heat().resources.mark_unhealthy(
                        stack_id, rn, True, "pre-reconfigure"
                    )
                except Exception:
                    pass

            merged_params = self._get_merged_stack_parameters(
                osc, stack_id, heat_params, template=stack_fields["template"]
            )

            nodegroup_fields = {
                **stack_fields,
                "existing": True,
                "parameters": merged_params,
                "timeout_mins": self._get_update_timeout(),
                "disable_rollback": True,
            }
            LOG.info("Reconfiguring cluster %s master stack %s", cluster.uuid, stack_id)
            osc.heat().stacks.update(stack_id, **nodegroup_fields)

    def create_nodegroup(self, context, cluster, nodegroup):
        stack = self._create_stack(
            context,
            clients.OpenStackClients(context),
            cluster,
            cluster.create_timeout,
            nodegroup=nodegroup,
        )
        nodegroup.stack_id = stack["stack"]["id"]

    def get_nodegroup_extra_params(self, cluster, osc):
        raise NotImplementedError("Must implement 'get_nodegroup_extra_params'")

    @abc.abstractmethod
    def upgrade_cluster(
        self,
        context,
        cluster,
        cluster_template,
        max_batch_size,
        nodegroup,
        scale_manager=None,
        rollback=False,
    ):
        raise NotImplementedError("Must implement 'upgrade_cluster'")

    def _get_cluster_osc(self, context, cluster):
        """Get OpenStack clients for cluster operations.

        Tries the cluster's trust context first.  If that fails (expired
        trust, deleted trustor, etc.), falls back to admin context so
        that delete and other lifecycle operations are not blocked by
        broken trusts.
        """
        try:
            cluster_ctx = mag_ctx.make_cluster_context(cluster)
            osc = clients.OpenStackClients(cluster_ctx)
            # Verify the context works by touching the session
            osc.heat()
            return osc
        except Exception as e:
            LOG.warning(
                "Cluster trust auth failed for %s, falling back to admin context: %s",
                cluster.uuid,
                e,
            )
            adm_ctx = mag_ctx.make_admin_context()
            return clients.OpenStackClients(adm_ctx)

    def delete_cluster(self, context, cluster):
        # On first delete attempt, go straight to Heat stack deletion.
        # Pre-delete cleanup (LB, volumes) only runs as a fallback when
        # retrying a DELETE_FAILED cluster — the cleanup logic can hang
        # on stuck resources and block the entire delete otherwise.
        is_retry = cluster.status == fields.ClusterStatus.DELETE_FAILED
        if is_retry:
            LOG.info(
                "Retrying delete for cluster %s, running pre-delete cleanup first",
                cluster.uuid,
            )
            self.pre_delete_cluster(context, cluster)

        self._delete_stacks(context, cluster)

    def _delete_stacks(self, context, cluster):
        LOG.info("Starting to delete cluster %s", cluster.uuid)
        osc = self._get_cluster_osc(context, cluster)
        errors = []
        for ng in cluster.nodegroups:
            ng.status = fields.ClusterStatus.DELETE_IN_PROGRESS
            ng.save()
            if ng.is_default:
                continue
            if not ng.stack_id:
                LOG.info("Nodegroup %s has no stack_id, skipping", ng.name)
                continue
            try:
                self._delete_stack(context, osc, ng.stack_id)
            except Exception as e:
                LOG.error(
                    "Failed to delete stack for nodegroup %s (stack %s): %s",
                    ng.name,
                    ng.stack_id,
                    e,
                )
                errors.append("nodegroup %s: %s" % (ng.name, e))

        master_stack_id = cluster.default_ng_master.stack_id
        if master_stack_id:
            try:
                self._delete_stack(context, osc, master_stack_id)
            except Exception as e:
                LOG.error("Failed to delete master stack %s: %s", master_stack_id, e)
                errors.append("master stack: %s" % e)
        else:
            LOG.info("Cluster %s master has no stack_id, skipping", cluster.uuid)

        if errors:
            raise exception.OperationInProgress(
                cluster_name="%s (partial delete failures: %s)"
                % (cluster.name, "; ".join(errors))
            )

    def resize_cluster(
        self,
        context,
        cluster,
        resize_manager,
        node_count,
        nodes_to_remove,
        nodegroup=None,
        rollback=False,
    ):
        self._resize_stack(
            context,
            cluster,
            resize_manager,
            node_count,
            nodes_to_remove,
            nodegroup=nodegroup,
            rollback=rollback,
        )

    def _create_stack(
        self, context, osc, cluster, cluster_create_timeout, nodegroup=None
    ):

        nodegroups = [nodegroup] if nodegroup else None
        template_path, heat_params, env_files = self._extract_template_definition(
            context, cluster, nodegroups=nodegroups
        )

        tpl_files, template = template_utils.get_template_contents(template_path)

        environment_files, env_map = self._get_env_files(template_path, env_files)
        tpl_files.update(env_map)

        # Make sure we end up with a valid hostname
        valid_chars = set(ascii_letters + digits + "-")

        # valid hostnames are 63 chars long, leaving enough room
        # to add the random id (for uniqueness)
        if nodegroup is None:
            stack_name = cluster.name[:30]
        else:
            stack_name = "%s-%s" % (cluster.name[:20], nodegroup.name[:9])
        stack_name = stack_name.replace("_", "-")
        stack_name = stack_name.replace(".", "-")
        stack_name = "".join(filter(valid_chars.__contains__, stack_name))

        # Make sure no duplicate stack name
        stack_name = "%s-%s" % (stack_name, short_id.generate_id())
        stack_name = stack_name.lower()
        if cluster_create_timeout:
            heat_timeout = cluster_create_timeout
        else:
            # no cluster_create_timeout value was passed in to the request
            # so falling back on configuration file value
            heat_timeout = cfg.CONF.cluster_heat.create_timeout

        heat_params["is_cluster_stack"] = nodegroup is None
        self._set_non_rotation_stack_flags(heat_params)

        if nodegroup:
            # In case we are creating a new stack for a new nodegroup then
            # we need to extract more params.
            heat_params.update(self.get_nodegroup_extra_params(cluster, osc))

        fields = {
            "stack_name": stack_name,
            "parameters": heat_params,
            "environment_files": environment_files,
            "template": template,
            "files": tpl_files,
            "timeout_mins": heat_timeout,
        }
        created_stack = osc.heat().stacks.create(**fields)

        return created_stack

    def _update_stack(self, context, cluster, scale_manager=None, rollback=False):
        # update worked properly only for scaling nodes up and down
        # before nodegroups. Maintain this logic until we deprecate
        # and remove the command.
        # Fixed behaviour Id84e5d878b21c908021e631514c2c58b3fe8b8b0
        nodegroup = cluster.default_ng_worker
        definition = self.get_template_definition()
        scale_params = definition.get_scale_params(
            context, cluster, nodegroup.node_count, scale_manager, nodes_to_remove=None
        )

        # Get existing stack parameters if available
        osc = self._get_cluster_osc(context, cluster)
        try:
            stack = osc.heat().stacks.get(nodegroup.stack_id)
            existing_params = stack.parameters
            if "timestamp_upgrade" in existing_params:
                scale_params["timestamp_upgrade"] = existing_params["timestamp_upgrade"]
        except Exception:
            pass

        self._set_non_rotation_stack_flags(scale_params)
        scale_params["timestamp_upgrade"] = self._get_reconcile_timestamp()

        nodegroups = None
        if nodegroup and not nodegroup.is_default:
            nodegroups = [nodegroup]

        fields = {
            **self._get_stack_update_template_fields(
                context, cluster, nodegroups=nodegroups
            ),
            "parameters": scale_params,
            "existing": True,
            "disable_rollback": not rollback,
        }

        LOG.info(
            "Updating cluster %s stack %s with these params: %s",
            cluster.uuid,
            nodegroup.stack_id,
            json.dumps(scale_params),
        )
        osc.heat().stacks.update(nodegroup.stack_id, **fields)

    def _resize_stack(
        self,
        context,
        cluster,
        resize_manager,
        node_count,
        nodes_to_remove,
        nodegroup=None,
        rollback=False,
    ):
        # Get current node count from Heat stack to detect scale-down operations
        try:
            osc = clients.OpenStackClients(context)
            stack = osc.heat().stacks.get(nodegroup.stack_id)
            current_node_count = int(
                stack.parameters.get(
                    "number_of_masters"
                    if nodegroup.role == "master"
                    else "number_of_minions",
                    0,
                )
            )
        except Exception:
            # If we can't get current count, assume it's the same as target
            current_node_count = nodegroup.node_count

        # Prevent scale-down operations for master nodes
        if nodegroup.role == "master" and nodegroup.node_count < current_node_count:
            raise exception.InvalidParameterValue(
                "Scale-down operations are not supported for master nodes. "
                f"Current master count: {current_node_count}, "
                f"requested master count: {nodegroup.node_count}. "
                "Master scale-down operations are disabled for cluster stability."
            )

        definition = self.get_template_definition()
        scale_params = definition.get_scale_params(
            context,
            cluster,
            nodegroup.node_count,
            resize_manager,
            nodes_to_remove=nodes_to_remove,
            nodegroup=nodegroup,
        )

        # Refresh ca_key from the cert manager when adding masters.  The parent
        # stack still stores the pre-rotation ca_key (a CA rotation only updates
        # the per-node member stacks), so without this a master added after a
        # rotation renders the stale ca_key while fetching the regenerated
        # ca.crt live from Magnum -- a keypair mismatch that crashes
        # kube-controller-manager and wedges the node NotReady.  Existing
        # masters already hold this exact value (it was pushed to their member
        # stacks during the rotation), so under existing:True their input is
        # unchanged and their deployments are NOT re-fired; only the new member
        # picks it up.  See _fetch_ca_key.
        if nodegroup and nodegroup.role == "master" and nodegroup.node_count > current_node_count:
            ca_key = self._fetch_ca_key(context, cluster)
            if ca_key:
                scale_params["ca_key"] = ca_key

        # Resize is a parameters-only Heat update (matches the legacy ussuri
        # behaviour).  We deliberately do NOT re-push the template, mark any
        # SoftwareConfig unhealthy, or change ca_rotation_id / is_resize /
        # is_upgrade / timestamp_upgrade.  Those values flow into the existing
        # nodes' SoftwareDeployment input_values; touching them (or marking
        # their config unhealthy) re-fires the reconciler on already-converged
        # nodes and can hit "Software config not found" on the immutable
        # SoftwareConfig.
        #
        # With ``existing: True`` Heat preserves every parameter we do not
        # pass, so existing nodes see zero input changes and their deployments
        # are not re-triggered.  Only the ResourceGroup count changes: new
        # members are created fresh (CREATE deployment) and removed members
        # are deleted per removal_policies.
        fields = {
            "parameters": scale_params,
            "existing": True,
            "disable_rollback": not rollback,
        }

        LOG.info(
            "Resizing cluster %s stack %s with these params: %s",
            cluster.uuid,
            nodegroup.stack_id,
            scale_params,
        )
        osc = clients.OpenStackClients(context)
        osc.heat().stacks.update(nodegroup.stack_id, **fields)

        # Special handling for master resize: ensure cluster stack gets updated with total master count
        # This is needed for etcd member cleanup to work properly during master operations
        if nodegroup and nodegroup.role == "master":
            self._update_cluster_stack_for_master_resize(
                context, cluster, nodegroup, scale_params
            )

    def _update_cluster_stack_for_master_resize(
        self, context, cluster, resized_nodegroup, scale_params
    ):
        """Update cluster stack with total master count during master resize operations.

        This ensures that master-0 can perform etcd member cleanup by getting the correct
        total NUMBER_OF_MASTERS parameter, especially when non-default master nodegroups are resized.
        """
        try:
            # Calculate total master count across all master nodegroups
            total_master_count = 0
            for ng in cluster.nodegroups:
                if ng.role == "master":
                    if ng.uuid == resized_nodegroup.uuid:
                        # Use the new count for the resized nodegroup
                        total_master_count += resized_nodegroup.node_count
                    else:
                        # Use existing count for other master nodegroups
                        total_master_count += ng.node_count

            # Check if the cluster stack (default nodegroups) needs updating
            default_master_ng = cluster.default_ng_master

            # If this is the default master nodegroup being resized, it already gets the update
            if default_master_ng.uuid == resized_nodegroup.uuid:
                LOG.debug(
                    "Resized nodegroup is the default master nodegroup, cluster stack already updated"
                )
                return

            # If there's only one master nodegroup (the default), no additional update needed
            master_nodegroups = [ng for ng in cluster.nodegroups if ng.role == "master"]
            if len(master_nodegroups) <= 1:
                LOG.debug(
                    "Only one master nodegroup exists, no cluster stack update needed"
                )
                return

            osc = clients.OpenStackClients(context)

            # Get the cluster stack ID (shared by default nodegroups)
            cluster_stack_id = default_master_ng.stack_id

            # Get existing cluster stack parameters
            try:
                cluster_stack = osc.heat().stacks.get(cluster_stack_id)
                existing_params = heat_tdef.omit_masked_heat_parameters(
                    cluster_stack.parameters.copy()
                )
            except Exception as e:
                LOG.warning(
                    "Could not retrieve existing cluster stack parameters: %s", str(e)
                )
                existing_params = {}

            # Only change the master count.  Same rationale as
            # _resize_stack: do not alter ca_rotation_id, is_resize,
            # is_upgrade, or timestamp_upgrade — those change the
            # SoftwareConfig content on existing nodes and can trigger
            # "Software config not found" failures.
            cluster_params = {
                "number_of_masters": total_master_count,
            }

            fields = {
                "parameters": cluster_params,
                "existing": True,
                "disable_rollback": True,
            }

            LOG.info(
                "Updating cluster stack %s with total master count %s for master resize coordination",
                cluster_stack_id,
                total_master_count,
            )
            osc.heat().stacks.update(cluster_stack_id, **fields)

        except Exception as e:
            LOG.error(
                "Failed to update cluster stack for master resize operation: %s", str(e)
            )
            # Don't fail the main resize operation if this supplementary update fails

    def _delete_stack(self, context, osc, stack_id, retries=3):
        for attempt in range(1, retries + 1):
            try:
                osc.heat().stacks.delete(stack_id)
                return
            except heatexc.NotFound:
                LOG.info("Stack %s already deleted", stack_id)
                return
            except heatexc.HTTPConflict:
                # Stack is already being deleted or in a transitional state.
                # Check if it's DELETE_IN_PROGRESS — if so, that's fine.
                try:
                    stack = osc.heat().stacks.get(stack_id)
                    if stack.stack_status in (
                        fields.ClusterStatus.DELETE_IN_PROGRESS,
                        fields.ClusterStatus.DELETE_COMPLETE,
                    ):
                        LOG.info("Stack %s is already %s", stack_id, stack.stack_status)
                        return
                    if stack.stack_status == fields.ClusterStatus.DELETE_FAILED:
                        LOG.warning(
                            "Stack %s is DELETE_FAILED, retrying "
                            "delete (attempt %d/%d)",
                            stack_id,
                            attempt,
                            retries,
                        )
                        continue
                except heatexc.NotFound:
                    LOG.info("Stack %s gone after conflict", stack_id)
                    return
                if attempt == retries:
                    raise
            except Exception:
                if attempt == retries:
                    raise
                LOG.warning(
                    "Stack delete attempt %d/%d failed for %s, retrying",
                    attempt,
                    retries,
                    stack_id,
                )


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
        """Clean up cloud resources that block Heat stack deletion.

        Only called as a fallback when retrying a DELETE_FAILED cluster.
        On first delete attempt we skip this and let Heat try directly —
        running cleanup upfront can hang on stuck volumes or dead
        amphora and block the entire delete.

        Both LB and volume cleanup are best-effort: if they fail or
        time out, we log a warning and proceed with the stack deletion
        retry anyway.
        """
        if keystone.is_octavia_enabled():
            LOG.info("Starting to delete loadbalancers for cluster %s", cluster.uuid)
            try:
                octavia.delete_loadbalancers(context, cluster)
            except Exception as e:
                LOG.warning(
                    "LB cleanup failed for cluster %s, "
                    "continuing with stack deletion: %s",
                    cluster.uuid,
                    e,
                )

        LOG.info("Starting to clean up volumes for cluster %s", cluster.uuid)
        try:
            cinder_cleanup.delete_volumes(context, cluster)
        except Exception as e:
            LOG.warning(
                "Volume cleanup failed for cluster %s, "
                "continuing with stack deletion: %s",
                cluster.uuid,
                e,
            )

    def _get_stack_update_template_fields(self, context, cluster, nodegroups=None):
        template_path, _, env_files = self._extract_template_definition(
            context, cluster, nodegroups=nodegroups
        )

        tpl_files, template = template_utils.get_template_contents(template_path)

        environment_files, env_map = self._get_env_files(template_path, env_files)
        tpl_files.update(env_map)

        return {
            "template": template,
            "environment_files": environment_files,
            "files": tpl_files,
        }

    def _get_nested_stack_ids(self, osc, parent_stack_id, nodegroup):
        resource_name = "kube_masters" if nodegroup.role == "master" else "kube_minions"
        try:
            resource_group = osc.heat().resources.get(parent_stack_id, resource_name)
        except heatexc.HTTPNotFound:
            return []
        group_stack_id = getattr(resource_group, "physical_resource_id", None)
        if not group_stack_id:
            return []

        member_stack_ids = []
        for resource in osc.heat().resources.list(group_stack_id):
            stack_id = getattr(resource, "physical_resource_id", None)
            if not stack_id:
                continue
            member_name = (
                getattr(resource, "resource_name", None)
                or getattr(resource, "logical_resource_id", None)
                or ""
            )
            if not six.text_type(member_name).isdigit():
                continue
            member_stack_ids.append((int(member_name), stack_id))

        return [stack_id for _, stack_id in sorted(member_stack_ids)]

    def _get_nested_stack_update_template_fields(self, context, nodegroup):
        """Return Heat template fields for a nodegroup's child stack.

        Uses ``_get_driver_for_nodegroup`` so cross-OS nodegroups (e.g.
        an Ubuntu nodepool on a Fedora CoreOS cluster) get their own
        driver's child template, not the cluster driver's.
        """
        ng_driver = self._get_driver_for_nodegroup(context, nodegroup)
        template_dir = os.path.dirname(
            ng_driver.get_template_definition().template_path
        )
        template_name = (
            "kubemaster.yaml" if nodegroup.role == "master" else "kubeminion.yaml"
        )
        template_path = os.path.join(template_dir, template_name)
        tpl_files, template = template_utils.get_template_contents(template_path)
        return {
            "template": template,
            "environment_files": [],
            "files": tpl_files,
        }

    def _get_nested_ca_rotation_params(
        self, nodegroup, heat_params, cluster_stack_params=None
    ):
        # The service-account keypair is intentionally absent: CA rotation must
        # leave it untouched (see _get_ca_rotation_params). Omitting it from a
        # params-only `existing=True` update makes Heat preserve each member's
        # current value, keeping every node's SA key in lockstep with the
        # unchanged parent stack. The deployment still re-fires because
        # ca_rotation_id and timestamp_upgrade change.
        nested_params = {
            "ca_rotation_id": heat_params["ca_rotation_id"],
            "is_upgrade": False,
            "is_resize": False,
            "timestamp_upgrade": heat_params["timestamp_upgrade"],
        }

        if cluster_stack_params:
            for key in (
                "trustee_user_id",
                "trustee_password",
                "trust_id",
                "auth_url",
                "magnum_url",
                "verify_ca",
                "cluster_uuid",
                "tls_disabled",
            ):
                value = heat_tdef.get_unmasked_heat_parameter(cluster_stack_params, key)
                if value is not None:
                    nested_params.setdefault(key, value)

        if nodegroup.role == "master":
            if cluster_stack_params and "number_of_masters" in cluster_stack_params:
                nested_params["number_of_masters"] = cluster_stack_params[
                    "number_of_masters"
                ]
            if "ca_key" in heat_params:
                nested_params["ca_key"] = heat_params["ca_key"]

        return nested_params

    @staticmethod
    def _filter_params_for_template(current_parameters, template):
        """Drop stack parameters not declared in the new template.

        When updating a stack with ``existing: True``, Heat preserves
        every parameter from the old stack.  If the new template no
        longer declares some of them the update fails with
        "Unknown parameter".  This method dynamically compares the old
        parameter set against the new template and removes obsolete
        entries so old clusters migrate cleanly without a hardcoded
        deprecation list.
        """
        if isinstance(template, dict):
            parsed = template
        else:
            parsed = yaml.safe_load(template)
        template_params = set(parsed.get("parameters", {}).keys())
        filtered = {}
        for k, v in current_parameters.items():
            if k in template_params:
                filtered[k] = v
            else:
                LOG.debug("Dropping obsolete stack parameter: %s", k)
        return filtered

    @staticmethod
    def _inject_deprecated_parameters(template, stack_parameters):
        """Re-declare in the new template every live parameter it dropped.

        A rolling ``existing: True`` ResourceGroup update keeps the old
        member definitions for nodes outside the current batch.  Those defs
        still reference removed parameters via ``{get_param: X}``, which
        resolve against the PARENT stack.  When a new release deletes the
        parameter declaration the parent no longer has it and Heat fails the
        update with ``Property X not assigned`` (e.g. ``flannel_cni_tag`` on an
        ussuri cluster migrating to a template that dropped it).

        This is the parameter-side counterpart to the alias/pin step
        (``_alias_resource_group_child_templates_for_rolling_migration`` /
        ``_pin_existing_child_templates_from_members``): alias/pin keep each
        retained member validating against the CHILD schema it was created
        with (so its removed properties are still accepted), and this keeps
        the corresponding PARENT-level parameters declared so the member's
        ``get_param`` resolves.  Together they let templates add and remove
        parameters freely from release to release and still migrate any
        existing cluster, with no hardcoded deprecation list.

        The injected declaration's ``type`` is inferred from the live value so
        a non-string parameter (bool/number/list) is not rejected.  The live
        value is preserved by the caller (the augmented template makes
        ``_filter_params_for_template`` keep it), so no default is needed; one
        is added anyway as a harmless fallback.  New batch members use the new
        resource_def, which does not reference these parameters, so the extra
        declarations are inert for them.

        ``stack_parameters`` is the RAW stack parameter map (NOT
        masked-omitted): a ``hidden: true`` parameter such as ``password``
        comes back masked (``******``), so we must see its NAME here to
        re-declare it, but we deliberately do NOT pass that masked value back
        (the caller filters it out).  For a masked dropped parameter we emit a
        declaration only — Heat's ``existing: True`` update then PRESERVES the
        real stored value for it, so the retained member's ``get_param``
        resolves without the secret ever entering this code path.
        """
        if isinstance(template, dict):
            parsed = template
            return_dict = True
        else:
            parsed = yaml.safe_load(template) or {}
            return_dict = False

        params = parsed.setdefault("parameters", {})
        injected = False
        for name, value in stack_parameters.items():
            if name in params or name.startswith("OS::"):
                continue
            if heat_tdef.is_masked_heat_parameter(value):
                # Declaration only; real value preserved by existing: True.
                params[name] = {"type": "string", "default": ""}
            else:
                params[name] = {
                    "type": _heat_param_type_for_value(value),
                    "default": value,
                }
            injected = True
            LOG.info(
                "Injected deprecated parameter %s for rolling migration", name
            )

        if not injected:
            return template
        if return_dict:
            return parsed
        return yaml.safe_dump(parsed, default_flow_style=False)

    def _get_merged_stack_parameters(
        self, osc, stack_id, updated_params, template=None
    ):
        current_parameters = heat_tdef.omit_masked_heat_parameters(
            osc.heat().stacks.get(stack_id).parameters.copy()
        )
        for param in ("OS::stack_id", "OS::project_id", "OS::stack_name"):
            current_parameters.pop(param, None)
        if template:
            current_parameters = self._filter_params_for_template(
                current_parameters, template
            )
        current_parameters.update(updated_params)
        return current_parameters

    def rotate_ca_certificate(self, context, cluster):
        osc = clients.OpenStackClients(context)

        heat_params = self._get_ca_rotation_params(context, cluster)
        cluster_stack_params = heat_tdef.omit_masked_heat_parameters(
            osc.heat().stacks.get(cluster.stack_id).parameters.copy()
        )

        # Bump timestamp_upgrade so each per-node SoftwareDeployment re-fires
        # (its inputs change).  is_upgrade/is_resize are forced off by
        # _get_nested_ca_rotation_params so upgrade/resize conditional
        # resources don't re-trigger.
        heat_params["timestamp_upgrade"] = self._get_reconcile_timestamp()

        # Params-only, direct-child token bump.  Update each nodegroup's
        # MEMBER (per-node) stacks DIRECTLY with only the rotation parameters
        # (existing: True, NO template push, NO mark_unhealthy):
        #
        #   * every master and worker rotates SIMULTANEOUSLY.  A parent
        #     ResourceGroup update serialises masters before minions (the
        #     minion member stacks depend on the master IP), so masters would
        #     block at the reconciler's dual-CA barrier waiting for workers
        #     Heat has not triggered yet — a guaranteed deadlock.  Direct
        #     child updates fire every node at once, which the hard CA swap
        #     requires.
        #   * the existing *_config_deployment re-fires via its
        #     actions:["CREATE","UPDATE"] because the CA_ROTATION_ID /
        #     TIMESTAMP_UPGRADE inputs change — no SoftwareConfig recreate and
        #     no parent-stack template desync.  (The SA keypair is intentionally
        #     left unchanged; see _get_nested_ca_rotation_params.)
        #
        # Bootstrap-script / template migration deliberately does NOT happen
        # on rotation; it rides on upgrade (full template) or reconfigure.
        for nodegroup in cluster.nodegroups:
            if not nodegroup.stack_id:
                continue

            # For default nodegroups, child stacks live inside the
            # cluster stack.  For non-default, they're in the
            # nodegroup's own stack.
            if nodegroup.is_default:
                parent_stack_id = cluster.stack_id
            else:
                parent_stack_id = nodegroup.stack_id

            stack_ids = self._get_nested_stack_ids(osc, parent_stack_id, nodegroup)
            if not stack_ids:
                LOG.warning(
                    "Could not resolve %s member stacks for "
                    "nodegroup %s in cluster %s during CA rotation",
                    nodegroup.role,
                    nodegroup.uuid,
                    cluster.uuid,
                )
                continue

            for stack_id in stack_ids:
                merged = self._get_merged_stack_parameters(
                    osc,
                    stack_id,
                    self._get_nested_ca_rotation_params(
                        nodegroup, heat_params, cluster_stack_params
                    ),
                )
                osc.heat().stacks.update(
                    stack_id,
                    existing=True,
                    parameters=merged,
                    timeout_mins=self._get_update_timeout(),
                    disable_rollback=True,
                )

        LOG.info("Triggered CA rotation of cluster %s", cluster.uuid)

    def _get_ca_rotation_params(self, context, cluster):
        heat_params = {
            "ca_rotation_id": short_id.generate_id(),
        }

        # NOTE: CA rotation deliberately does NOT rotate the service-account
        # signing keypair. The SA key is an independent trust root from the
        # cluster PKI CA, and rotating it here breaks masters added AFTER a
        # rotation: a new master renders the SA key from the parent cluster
        # stack (never updated by the direct-child rotation), so a freshly
        # generated key would leave it with a different signing/verification
        # key than the rest of the cluster — its apiserver rejects every
        # service-account token (flannel/CSI/etc. 401), the CNI never
        # initializes, and the node stays NotReady. Keeping the SA key stable
        # (kubeadm's `certs renew` does the same) means parent and all members
        # always agree on it. The key is preserved by simply omitting it from
        # the per-node rotation params below.

        ca_key = self._fetch_ca_key(context, cluster)
        if ca_key:
            heat_params["ca_key"] = ca_key

        return heat_params

    def _fetch_ca_key(self, context, cluster):
        """Return the cluster CA private key (newline-escaped) from the cert
        manager, or None when cert_manager_api is disabled / unavailable.

        cert_manager_api defaults to true: the reconciler-driven clusters always
        run the in-cluster cert API manager, which needs the CA private key on
        every master to sign kubelet-serving CSRs.

        This is the single source of the current CA key. After a CA rotation the
        conductor regenerates the cluster CA in the cert manager (Barbican), but
        the parent cluster/nodegroup stack still stores the PRE-rotation ca_key
        (rotation updates the per-node member stacks directly, never the parent).
        A master added later renders ca_key from that stale parent value while
        fetching the regenerated ca.crt live from Magnum — a CA keypair mismatch
        that crashes kube-controller-manager (cluster-signing-cert/key) and
        leaves the node NotReady. Callers refresh ca_key from here so newly added
        masters get the current key.
        """
        cluster_labels = cluster.labels or {}
        cert_manager_api = cluster_labels.get("cert_manager_api", "true")
        if six.text_type(cert_manager_api).lower() != "true":
            return None
        try:
            ca_cert = cert_manager.get_cluster_ca_certificate(cluster, context=context)
            ca_key_password = ca_cert.get_private_key_passphrase()
            if six.PY3 and isinstance(ca_key_password, six.text_type):
                ca_key = x509.decrypt_key(
                    ca_cert.get_private_key(), ca_key_password.encode()
                ).decode()
            else:
                ca_key = x509.decrypt_key(ca_cert.get_private_key(), ca_key_password)
            return ca_key.replace("\n", "\\n")
        except Exception as exc:
            LOG.warning(
                "Could not fetch current CA key for cluster %s: %s",
                cluster.uuid,
                exc,
            )
            return None

    def upgrade_cluster(
        self,
        context,
        cluster,
        cluster_template,
        max_batch_size,
        nodegroup,
        scale_manager=None,
        rollback=False,
    ):
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
            LOG.debug(
                ("Cluster template %s does not contain a valid kube_tag"),
                cluster_template.name,
            )

        # If both keys are present, only ostree_commit is chosen.
        for ostree_tag in ["ostree_commit", "ostree_remote"]:
            if ostree_tag not in cluster_template.labels:
                continue
            try:
                ostree_param = {ostree_tag: cluster_template.labels[ostree_tag]}
                heat_params.update(ostree_param)
                break
            except KeyError:
                LOG.debug(
                    "Cluster template %s does not define %s",
                    cluster_template.name,
                    ostree_tag,
                )

        upgrade_labels = ["kube_tag", "ostree_remote", "ostree_commit"]
        if not any([u in heat_params.keys() for u in upgrade_labels]):
            reason = (
                "Cluster template %s does not contain any supported "
                "upgrade labels: [%s]"
            ) % (cluster_template.name, ", ".join(upgrade_labels))
            raise exception.InvalidClusterTemplateForUpgrade(reason=reason)

        return heat_params

    @staticmethod
    def get_new_labels(nodegroup, cluster_template):
        new_labels = nodegroup.labels.copy()
        if "kube_tag" in cluster_template.labels:
            new_kube_tag = cluster_template.labels["kube_tag"]

            kube_tag_params = {
                "kube_tag": new_kube_tag,
                "kube_version": new_kube_tag,
                "master_kube_tag": new_kube_tag,
                "minion_kube_tag": new_kube_tag,
            }

            new_labels.update(kube_tag_params)
        return new_labels

    def upgrade_cluster(
        self,
        context,
        cluster,
        cluster_template,  # noqa: C901
        max_batch_size,
        nodegroup,
        scale_manager=None,
        rollback=False,
    ):
        osc = self._get_cluster_osc(context, cluster)

        # Use this just to check that we are not downgrading.
        heat_params = {
            "update_max_batch_size": max_batch_size,
        }

        heat_params["is_upgrade"] = True
        heat_params["is_resize"] = False

        if "kube_tag" in nodegroup.labels:
            heat_params["kube_tag"] = nodegroup.labels["kube_tag"]
            heat_params["kube_version"] = nodegroup.labels["kube_tag"]
            heat_params["master_kube_tag"] = nodegroup.labels["kube_tag"]
            heat_params["minion_kube_tag"] = nodegroup.labels["kube_tag"]
        current_addons = {}
        new_addons = {}
        for label in cluster_template.labels:
            # This is upgrade API, so we don't introduce new stuff by this API,
            # but just focus on the version change.
            new_addons[label] = cluster_template.labels[label]
            if (
                label.endswith("_tag") or label.endswith("_version")
            ) and label in heat_params:
                current_addons[label] = heat_params[label]
                try:
                    if SV.from_pip_string(new_addons[label]) < SV.from_pip_string(
                        current_addons[label]
                    ):
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
            heat_params["is_cluster_stack"] = False
            # For now set the worker_role explicitly in order to
            # make sure that the is_master condition fails.
            heat_params["worker_role"] = nodegroup.role

        # we need to set the whole dict to the object
        # and not just update the existing labels. This
        # is how obj_what_changed works.
        nodegroup.labels = new_labels = self.get_new_labels(nodegroup, cluster_template)

        if nodegroup.is_default:
            cluster.cluster_template_id = cluster_template.uuid
            cluster.labels = new_labels
            if nodegroup.role == "master":
                other_default_ng = cluster.default_ng_worker
            else:
                other_default_ng = cluster.default_ng_master
            other_default_ng.labels = new_labels
            other_default_ng.save()
        else:
            # For non-default nodegroups, set the cluster_template_id label to match the upgrade target
            # This allows nodegroups to be upgraded to different templates than the cluster's default
            new_labels["cluster_template_id"] = cluster_template.uuid
            nodegroup.labels = new_labels

        # Always send the full template so old clusters are automatically
        # migrated to the new bootstrap structure.  Use the correct driver
        # for non-default nodegroups (cross-OS nodepool support).
        if nodegroup and not nodegroup.is_default:
            template_path, heat_params, env_files = (
                self._extract_template_definition_for_nodegroup(
                    context, cluster, nodegroup
                )
            )
        else:
            template_path, heat_params, env_files = self._extract_template_definition(
                context, cluster
            )

        tpl_files, template = template_utils.get_template_contents(template_path)
        environment_files, env_map = self._get_env_files(template_path, env_files)
        tpl_files.update(env_map)
        template, aliased = (
            self._alias_resource_group_child_templates_for_rolling_migration(
                template, tpl_files
            )
        )
        # Recover clusters already broken by a prior failed migration attempt:
        # pin the genuine pre-migration child templates (fetched from the
        # untouched member stacks) under their original keys so stale member
        # definitions validate against the schema they were created with.
        self._pin_existing_child_templates_from_members(
            osc, stack_id, aliased, tpl_files
        )

        # Fetch the current stack parameters, then re-declare in the new
        # template any the new template dropped.  A rolling ``existing: True``
        # update keeps retained (non-batch) members referencing those removed
        # parameters via ``{get_param: X}``; re-declaring keeps the references
        # resolvable instead of failing ``Property X not assigned`` (the
        # parameter-side counterpart to the alias/pin child-schema step).
        # Handles removed, renamed, or deprecated parameters automatically —
        # no hardcoded deprecation list.
        raw_parameters = osc.heat().stacks.get(stack_id).parameters.copy()
        current_parameters = heat_tdef.omit_masked_heat_parameters(raw_parameters)
        # Pass RAW params (masked included) so masked-but-dropped parameters
        # like `password` are still re-declared; their masked value is never
        # passed back — existing: True preserves the real one.
        template = self._inject_deprecated_parameters(template, raw_parameters)

        self._set_non_rotation_stack_flags(heat_params, is_upgrade=True)
        heat_params["update_max_batch_size"] = max_batch_size or 1
        heat_params["timestamp_upgrade"] = self._get_reconcile_timestamp()

        fields = {
            "template": template,
            "environment_files": environment_files,
            "files": tpl_files,
            "existing": True,
            "parameters": heat_params,
            "timeout_mins": self._get_update_timeout(),
        }

        # Drop live params not declared in the (now augmented) template; the
        # injected deprecated params survive and their values flow back to the
        # retained members.
        current_parameters = self._filter_params_for_template(
            current_parameters, template
        )

        # Merge: new parameters win over old stack values.
        current_parameters.update(fields["parameters"])

        # Volume types and sizes are immutable on in-use volumes —
        # Cinder rejects retypes.  Drop them so Heat preserves
        # existing values via 'existing: True'.
        for immutable_param in (
            "docker_volume_type",
            "etcd_volume_type",
            "boot_volume_type",
            "docker_volume_size",
            "etcd_volume_size",
            "boot_volume_size",
        ):
            current_parameters.pop(immutable_param, None)

        fields["parameters"] = current_parameters

        # Mark SoftwareConfig resources unhealthy before pushing the
        # template so Heat recreates them instead of failing on stale
        # config references during template migration.
        self._prepare_stack_for_template_update(osc, stack_id)
        osc.heat().stacks.update(stack_id, **fields)

        # save the nodegroup and cluster
        nodegroup.save()
        cluster.save()

        # The update of a nodegroup will trigger a cluster upgrade.
        LOG.info("Triggered upgrade of cluster %s", cluster.uuid)
        return cluster.uuid

    def get_nodegroup_extra_params(self, cluster, osc):
        network = osc.heat().resources.get(cluster.stack_id, "network")
        secgroup = osc.heat().resources.get(cluster.stack_id, "secgroup_kube_minion")
        for output in osc.heat().stacks.get(cluster.stack_id).outputs:
            if output["output_key"] == "api_address":
                api_address = output["output_value"]
                break
        extra_params = {
            "existing_master_private_ip": api_address,
            "existing_security_group": secgroup.attributes["id"],
            "fixed_network": network.attributes["fixed_network"],
            "fixed_subnet": network.attributes["fixed_subnet"],
        }
        return extra_params


class UbuntuKubernetesDriver(KubernetesDriver):
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
            LOG.debug(
                ("Cluster template %s does not contain a valid kube_tag"),
                cluster_template.name,
            )

        # If both keys are present, only ostree_commit is chosen.
        for ostree_tag in ["ostree_commit", "ostree_remote"]:
            if ostree_tag not in cluster_template.labels:
                continue
            try:
                ostree_param = {ostree_tag: cluster_template.labels[ostree_tag]}
                heat_params.update(ostree_param)
                break
            except KeyError:
                LOG.debug(
                    "Cluster template %s does not define %s",
                    cluster_template.name,
                    ostree_tag,
                )

        upgrade_labels = ["kube_tag", "ostree_remote", "ostree_commit"]
        if not any([u in heat_params.keys() for u in upgrade_labels]):
            reason = (
                "Cluster template %s does not contain any supported "
                "upgrade labels: [%s]"
            ) % (cluster_template.name, ", ".join(upgrade_labels))
            raise exception.InvalidClusterTemplateForUpgrade(reason=reason)

        return heat_params

    @staticmethod
    def get_new_labels(nodegroup, cluster_template):
        new_labels = nodegroup.labels.copy()
        if "kube_tag" in cluster_template.labels:
            new_kube_tag = cluster_template.labels["kube_tag"]

            kube_tag_params = {
                "kube_tag": new_kube_tag,
                "kube_version": new_kube_tag,
                "master_kube_tag": new_kube_tag,
                "minion_kube_tag": new_kube_tag,
            }

            new_labels.update(kube_tag_params)
        return new_labels

    def upgrade_cluster(
        self,
        context,
        cluster,
        cluster_template,  # noqa: C901
        max_batch_size,
        nodegroup,
        scale_manager=None,
        rollback=False,
    ):
        osc = self._get_cluster_osc(context, cluster)

        # Use this just to check that we are not downgrading.
        heat_params = {
            "update_max_batch_size": max_batch_size,
        }

        heat_params["is_upgrade"] = True
        heat_params["is_resize"] = False

        if "kube_tag" in nodegroup.labels:
            heat_params["kube_tag"] = nodegroup.labels["kube_tag"]
            heat_params["kube_version"] = nodegroup.labels["kube_tag"]
            heat_params["master_kube_tag"] = nodegroup.labels["kube_tag"]
            heat_params["minion_kube_tag"] = nodegroup.labels["kube_tag"]
        current_addons = {}
        new_addons = {}
        for label in cluster_template.labels:
            # This is upgrade API, so we don't introduce new stuff by this API,
            # but just focus on the version change.
            new_addons[label] = cluster_template.labels[label]
            if (
                label.endswith("_tag") or label.endswith("_version")
            ) and label in heat_params:
                current_addons[label] = heat_params[label]
                try:
                    if SV.from_pip_string(new_addons[label]) < SV.from_pip_string(
                        current_addons[label]
                    ):
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
            heat_params["is_cluster_stack"] = False
            # For now set the worker_role explicitly in order to
            # make sure that the is_master condition fails.
            heat_params["worker_role"] = nodegroup.role

        # we need to set the whole dict to the object
        # and not just update the existing labels. This
        # is how obj_what_changed works.
        nodegroup.labels = new_labels = self.get_new_labels(nodegroup, cluster_template)

        if nodegroup.is_default:
            cluster.cluster_template_id = cluster_template.uuid
            cluster.labels = new_labels
            if nodegroup.role == "master":
                other_default_ng = cluster.default_ng_worker
            else:
                other_default_ng = cluster.default_ng_master
            other_default_ng.labels = new_labels
            other_default_ng.save()
        else:
            # For non-default nodegroups, set the cluster_template_id label to match the upgrade target
            # This allows nodegroups to be upgraded to different templates than the cluster's default
            new_labels["cluster_template_id"] = cluster_template.uuid
            nodegroup.labels = new_labels

        # Always send the full template so old clusters are automatically
        # migrated to the new bootstrap structure.
        if nodegroup and not nodegroup.is_default:
            template_path, heat_params, env_files = (
                self._extract_template_definition_for_nodegroup(
                    context, cluster, nodegroup
                )
            )
        else:
            template_path, heat_params, env_files = self._extract_template_definition(
                context, cluster
            )

        tpl_files, template = template_utils.get_template_contents(template_path)
        environment_files, env_map = self._get_env_files(template_path, env_files)
        tpl_files.update(env_map)
        template, aliased = (
            self._alias_resource_group_child_templates_for_rolling_migration(
                template, tpl_files
            )
        )
        # Recover clusters already broken by a prior failed migration attempt:
        # pin the genuine pre-migration child templates (fetched from the
        # untouched member stacks) under their original keys so stale member
        # definitions validate against the schema they were created with.
        self._pin_existing_child_templates_from_members(
            osc, stack_id, aliased, tpl_files
        )

        # Fetch the current stack parameters, then re-declare in the new
        # template any the new template dropped.  A rolling ``existing: True``
        # update keeps retained (non-batch) members referencing those removed
        # parameters via ``{get_param: X}``; re-declaring keeps the references
        # resolvable instead of failing ``Property X not assigned`` (the
        # parameter-side counterpart to the alias/pin child-schema step).
        # Handles removed, renamed, or deprecated parameters automatically —
        # no hardcoded deprecation list.
        raw_parameters = osc.heat().stacks.get(stack_id).parameters.copy()
        current_parameters = heat_tdef.omit_masked_heat_parameters(raw_parameters)
        # Pass RAW params (masked included) so masked-but-dropped parameters
        # like `password` are still re-declared; their masked value is never
        # passed back — existing: True preserves the real one.
        template = self._inject_deprecated_parameters(template, raw_parameters)

        self._set_non_rotation_stack_flags(heat_params, is_upgrade=True)
        heat_params["update_max_batch_size"] = max_batch_size or 1
        heat_params["timestamp_upgrade"] = self._get_reconcile_timestamp()

        fields = {
            "template": template,
            "environment_files": environment_files,
            "files": tpl_files,
            "existing": True,
            "parameters": heat_params,
            "timeout_mins": self._get_update_timeout(),
        }

        # Drop live params not declared in the (now augmented) template; the
        # injected deprecated params survive and their values flow back to the
        # retained members.
        current_parameters = self._filter_params_for_template(
            current_parameters, template
        )

        # Merge: new parameters win over old stack values.
        current_parameters.update(fields["parameters"])

        # Volume types and sizes are immutable on in-use volumes —
        # Cinder rejects retypes.  Drop them so Heat preserves
        # existing values via 'existing: True'.
        for immutable_param in (
            "docker_volume_type",
            "etcd_volume_type",
            "boot_volume_type",
            "docker_volume_size",
            "etcd_volume_size",
            "boot_volume_size",
        ):
            current_parameters.pop(immutable_param, None)

        fields["parameters"] = current_parameters

        # Mark SoftwareConfig resources unhealthy before pushing the
        # template so Heat recreates them instead of failing on stale
        # config references during template migration.
        self._prepare_stack_for_template_update(osc, stack_id)
        osc.heat().stacks.update(stack_id, **fields)

        # save the nodegroup and cluster
        nodegroup.save()
        cluster.save()

        # The update of a nodegroup will trigger a cluster upgrade.
        LOG.info("Triggered upgrade of cluster %s", cluster.uuid)
        return cluster.uuid

    def get_nodegroup_extra_params(self, cluster, osc):
        network = osc.heat().resources.get(cluster.stack_id, "network")
        secgroup = osc.heat().resources.get(cluster.stack_id, "secgroup_kube_minion")
        for output in osc.heat().stacks.get(cluster.stack_id).outputs:
            if output["output_key"] == "api_address":
                api_address = output["output_value"]
                break
        extra_params = {
            "existing_master_private_ip": api_address,
            "existing_security_group": secgroup.attributes["id"],
            "fixed_network": network.attributes["fixed_network"],
            "fixed_subnet": network.attributes["fixed_subnet"],
        }
        return extra_params


class HeatPoller(object):
    def __init__(self, openstack_client, context, cluster, cluster_driver):
        self.openstack_client = openstack_client
        self.context = context
        self.cluster = cluster
        self.cluster_template = conductor_utils.retrieve_cluster_template(
            self.context, cluster
        )
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

    def _has_member_stack_in_progress(self):
        """Whether any per-node member stack under this nodegroup's stack is
        mid-update.

        A direct-child CA rotation updates the ResourceGroup member (node)
        stacks out-of-band, so the parent stack can read *_COMPLETE while the
        nodes are still converging.  Used to keep the cluster in
        UPDATE_IN_PROGRESS for the duration so a concurrent upgrade is
        rejected by the conductor precondition (which would otherwise corrupt
        the in-flight rotation).
        """
        try:
            resources = self.openstack_client.heat().resources.list(
                self.nodegroup.stack_id, nested_depth=2
            )
        except Exception as e:
            LOG.debug(
                "Could not list nested resources of stack %s: %s",
                self.nodegroup.stack_id,
                e,
            )
            return False
        for res in resources:
            status = getattr(res, "resource_status", "") or ""
            if status.endswith("_IN_PROGRESS"):
                return True
        return False

    def extract_nodegroup_status(self):

        if self.nodegroup.stack_id is None:
            # There is a slight window for a race condition here. If
            # a nodegroup is created and just before the stack_id is
            # assigned to it, this periodic task is executed, the
            # periodic task would try to find the status of the
            # stack with id = None. At that time the nodegroup status
            # is already set to CREATE_IN_PROGRESS by the conductor.
            # Keep this status for this loop until the stack_id is assigned.
            return NodeGroupStatus(
                name=self.nodegroup.name,
                status=self.nodegroup.status,
                is_default=self.nodegroup.is_default,
                reason=self.nodegroup.status_reason,
            )

        try:
            # Do not resolve outputs by default. Resolving all
            # node IPs is expensive on heat.
            stack = self.openstack_client.heat().stacks.get(
                self.nodegroup.stack_id, resolve_outputs=False
            )

            if stack.stack_status in (
                fields.ClusterStatus.CREATE_COMPLETE,
                fields.ClusterStatus.UPDATE_COMPLETE,
            ):
                # A direct-child CA rotation updates the per-node (member)
                # stacks out-of-band, so this parent stack can read
                # UPDATE_COMPLETE while the nodes are still rotating.  Hold the
                # nodegroup in UPDATE_IN_PROGRESS until the member stacks settle
                # so the cluster stays UPDATE_IN_PROGRESS and the conductor
                # rejects a concurrent upgrade (which would corrupt the
                # in-flight rotation).  Self-healing: once the members reach a
                # terminal state this returns False and the sync below flips
                # the cluster to UPDATE_COMPLETE.
                if (
                    stack.stack_status == fields.ClusterStatus.UPDATE_COMPLETE
                    and self.cluster.status
                    == fields.ClusterStatus.UPDATE_IN_PROGRESS
                    and self._has_member_stack_in_progress()
                ):
                    self.nodegroup.status = (
                        fields.ClusterStatus.UPDATE_IN_PROGRESS
                    )
                    self.nodegroup.status_reason = (
                        "CA rotation in progress on member stacks"
                    )
                    self.nodegroup.save()
                    return NodeGroupStatus(
                        name=self.nodegroup.name,
                        status=self.nodegroup.status,
                        is_default=self.nodegroup.is_default,
                        reason=self.nodegroup.status_reason,
                    )

                # Resolve all outputs if the stack is COMPLETE
                stack = self.openstack_client.heat().stacks.get(
                    self.nodegroup.stack_id, resolve_outputs=True
                )

                self._sync_cluster_and_template_status(stack)
            elif stack.stack_status != self.nodegroup.status:
                self.template_def.nodegroup_output_mappings = list()
                self.template_def.update_outputs(
                    stack,
                    self.cluster_template,
                    self.cluster,
                    nodegroups=[self.nodegroup],
                )
                self._sync_cluster_status(stack)

            # poll_and_check is detached and polling long time to check
            # status, so another user/client can call delete cluster/stack.
            if stack.stack_status == fields.ClusterStatus.DELETE_COMPLETE:
                if self.nodegroup.is_default:
                    self._check_delete_complete()
                else:
                    self.nodegroup.destroy()
                    return

            if stack.stack_status in (
                fields.ClusterStatus.CREATE_FAILED,
                fields.ClusterStatus.DELETE_FAILED,
                fields.ClusterStatus.UPDATE_FAILED,
                fields.ClusterStatus.ROLLBACK_COMPLETE,
                fields.ClusterStatus.ROLLBACK_FAILED,
            ):
                try:
                    self._sync_cluster_and_template_status(stack)
                except Exception:
                    # For failed/deleting stacks, output resolution may
                    # fail. Fall back to syncing just the status so the
                    # cluster doesn't stay stuck in *_IN_PROGRESS forever.
                    LOG.warning(
                        "Failed to sync outputs for stack %s "
                        "in %s state, syncing status only",
                        self.nodegroup.stack_id,
                        stack.stack_status,
                    )
                    self._sync_cluster_status(stack)
                self._nodegroup_failed(stack)
        except heatexc.NotFound:
            self._sync_missing_heat_stack()
        return NodeGroupStatus(
            name=self.nodegroup.name,
            status=self.nodegroup.status,
            is_default=self.nodegroup.is_default,
            reason=self.nodegroup.status_reason,
        )

    def aggregate_nodegroup_statuses(self, ng_statuses):
        # NOTE(ttsiouts): Aggregate the nodegroup statuses and set the
        # cluster overall status.
        FAILED = "_FAILED"
        IN_PROGRESS = "_IN_PROGRESS"
        COMPLETE = "_COMPLETE"
        UPDATE = "UPDATE"
        DELETE = "DELETE"

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
                    status = getattr(fields.ClusterStatus, action + state)
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
            if previous_state not in (
                fields.ClusterStatus.CREATE_COMPLETE,
                fields.ClusterStatus.CREATE_IN_PROGRESS,
            ):
                self.cluster.status = fields.ClusterStatus.UPDATE_COMPLETE

        # Summarize the failed reasons.
        if self.cluster.status.endswith(FAILED):
            reasons = [
                "%s failed" % (ns.name)
                for ns in ng_statuses
                if ns.status.endswith(FAILED)
            ]
            self.cluster.status_reason = ", ".join(reasons)

        self.cluster.save()

    def _delete_complete(self):
        LOG.info("Cluster has been deleted, stack_id: %s", self.cluster.stack_id)
        try:
            trust_manager.delete_trustee_and_trust(
                self.openstack_client, self.context, self.cluster
            )
            cert_manager.delete_certificates_from_cluster(
                self.cluster, context=self.context
            )
            cert_manager.delete_client_files(self.cluster, context=self.context)

        except exception.ClusterNotFound:
            LOG.info("The cluster %s has been deleted by others.", self.cluster.uuid)

    def _sync_cluster_status(self, stack):
        self.nodegroup.status = stack.stack_status
        self.nodegroup.status_reason = stack.stack_status_reason
        self.nodegroup.save()

    def get_version_info(self, stack):
        stack_param = self.template_def.get_heat_param(cluster_attr="coe_version")
        if stack_param:
            self.cluster.coe_version = stack.parameters[stack_param]

        version_module_path = self.template_def.driver_module_path + ".version"
        try:
            ver = importutils.import_module(version_module_path)
            container_version = ver.container_version
        except Exception:
            container_version = None
        self.cluster.container_version = container_version

    def _sync_cluster_and_template_status(self, stack):
        self.template_def.nodegroup_output_mappings = list()
        self.template_def.update_outputs(
            stack, self.cluster_template, self.cluster, nodegroups=[self.nodegroup]
        )
        self.get_version_info(stack)
        self._sync_cluster_status(stack)

    def _nodegroup_failed(self, stack):
        LOG.error(
            "Nodegroup error, stack status: %(ng_status)s, "
            "stack_id: %(stack_id)s, "
            "reason: %(reason)s",
            {
                "ng_status": stack.stack_status,
                "stack_id": self.nodegroup.stack_id,
                "reason": self.nodegroup.status_reason,
            },
        )

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
        if all(
            status == fields.ClusterStatus.DELETE_COMPLETE
            for status in default_ng_statuses
        ):
            self._delete_complete()

    def _sync_missing_stack(self, new_status):
        self.nodegroup.status = new_status
        self.nodegroup.status_reason = (
            _("Stack with id %s not found in Heat.") % self.cluster.stack_id
        )
        self.nodegroup.save()
        LOG.info(
            "Nodegroup with id %(id)s has been set to "
            "%(status)s due to stack with id %(sid)s "
            "not found in Heat.",
            {
                "id": self.nodegroup.uuid,
                "status": self.nodegroup.status,
                "sid": self.nodegroup.stack_id,
            },
        )
