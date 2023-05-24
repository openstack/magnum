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

import enum
import re

from oslo_log import log as logging
from oslo_utils import encodeutils

from magnum.api import utils as api_utils
from magnum.common import clients
from magnum.common import exception
from magnum.common import short_id
from magnum.common.x509 import operations as x509
from magnum.conductor.handlers.common import cert_manager
from magnum import conf
from magnum.drivers.cluster_api import app_creds
from magnum.drivers.cluster_api import helm
from magnum.drivers.cluster_api import kubernetes
from magnum.drivers.common import driver
from magnum.drivers.common import k8s_monitor
from magnum.objects import fields

LOG = logging.getLogger(__name__)
CONF = conf.CONF
NODE_GROUP_ROLE_CONTROLLER = "master"


class NodeGroupState(enum.Enum):
    NOT_PRESENT = 1
    PENDING = 2
    READY = 3
    FAILED = 4


class Driver(driver.Driver):
    def __init__(self):
        self._helm_client = helm.Client()
        self.__k8s_client = None

    @property
    def _k8s_client(self):
        if not self.__k8s_client:
            self.__k8s_client = kubernetes.Client.load()
        return self.__k8s_client

    @property
    def provides(self):
        return [
            {'server_type': 'vm',
             # NOTE(johngarbutt) we could support any cluster api
             # supported image, but lets start with ubuntu for now.
             # TODO(johngarbutt) os list should probably come from config?
             'os': 'ubuntu',
             'coe': 'kubernetes'},
        ]

    def _update_control_plane_nodegroup_status(self, cluster, nodegroup):
        # The status of the master nodegroup is determined by the Cluster API
        # control plane object
        kcp = self._k8s_client.get_kubeadm_control_plane(
            self._sanitised_name(
                self._get_chart_release_name(cluster), "control-plane"
            ),
            self._namespace(cluster),
        )

        ng_state = NodeGroupState.NOT_PRESENT
        if kcp:
            ng_state = NodeGroupState.PENDING

        kcp_spec = kcp.get("spec", {}) if kcp else {}
        kcp_status = kcp.get("status", {}) if kcp else {}

        # The control plane object is what controls the Kubernetes version
        # If it is known, report it
        kube_version = kcp_status.get("version", kcp_spec.get("version"))
        if cluster.coe_version != kube_version:
            cluster.coe_version = kube_version
            cluster.save()

        kcp_true_conditions = {
            cond["type"]
            for cond in kcp_status.get("conditions", [])
            if cond["status"] == "True"
        }
        kcp_ready = all(
            cond in kcp_true_conditions
            for cond in (
                "MachinesReady",
                "Ready",
                "EtcdClusterHealthy",
                "ControlPlaneComponentsHealthy"
            )
        )
        target_replicas = kcp_spec.get("replicas")
        current_replicas = kcp_status.get("replicas")
        updated_replicas = kcp_status.get("updatedReplicas")
        ready_replicas = kcp_status.get("readyReplicas")
        if (
            kcp_ready and
            target_replicas == current_replicas and
            current_replicas == updated_replicas and
            updated_replicas == ready_replicas
        ):
            ng_state = NodeGroupState.READY

        # TODO(mkjpryor) Work out a way to determine FAILED state
        return self._update_nodegroup_status(cluster, nodegroup, ng_state)

    def _update_worker_nodegroup_status(self, cluster, nodegroup):
        # The status of a worker nodegroup is determined by the corresponding
        # Cluster API machine deployment
        md = self._k8s_client.get_machine_deployment(
            self._sanitised_name(
                self._get_chart_release_name(cluster), nodegroup.name
            ),
            self._namespace(cluster),
        )

        ng_state = NodeGroupState.NOT_PRESENT
        if md:
            ng_state = NodeGroupState.PENDING

        # When a machine deployment is deleted, it disappears straight
        # away even when there are still machines belonging to it that
        # are deleting
        # In that case, we want to keep the nodegroup as DELETE_IN_PROGRESS
        # until all the machines for the node group are gone
        if (
            not md
            and nodegroup.status.startswith("DELETE_")
            and self._nodegroup_machines_exist(cluster, nodegroup)
        ):
            LOG.debug(
                f"Node group {nodegroup.name} "
                f"for cluster {cluster.uuid} "
                "machine deployment gone, but machines still found."
            )
            ng_state = NodeGroupState.PENDING

        md_status = md.get("status", {}) if md else {}
        md_phase = md_status.get("phase")
        if md_phase:
            if md_phase == "Running":
                ng_state = NodeGroupState.READY
            elif md_phase in {"Failed", "Unknown"}:
                ng_state = NodeGroupState.FAILED

        return self._update_nodegroup_status(cluster, nodegroup, ng_state)

    def _update_nodegroup_status(self, cluster, nodegroup, ng_state):
        # For delete we are waiting for not present
        if nodegroup.status.startswith("DELETE_"):
            if ng_state == NodeGroupState.NOT_PRESENT:
                if not nodegroup.is_default:
                    # Conductor will delete default nodegroups
                    # when cluster is deleted, but non default
                    # node groups should be deleted here.
                    nodegroup.destroy()
                LOG.debug(
                    f"Node group deleted: {nodegroup.name} "
                    f"for cluster {cluster.uuid} "
                    f"which is_default: {nodegroup.is_default}"
                )
                # signal the node group has been deleted
                return None

            LOG.debug(
                f"Node group not yet delete: {nodegroup.name} "
                f"for cluster {cluster.uuid}"
            )
            return nodegroup

        is_update_operation = nodegroup.status.startswith("UPDATE_")
        is_create_operation = nodegroup.status.startswith("CREATE_")
        if not is_update_operation and not is_create_operation:
            LOG.warning(
                f"Node group: {nodegroup.name} in unexpected "
                f"state: {nodegroup.status} in cluster {cluster.uuid}"
            )
        elif ng_state == NodeGroupState.READY:
            nodegroup.status = (
                fields.ClusterStatus.UPDATE_COMPLETE
                if is_update_operation
                else fields.ClusterStatus.CREATE_COMPLETE
            )
            LOG.debug(
                f"Node group ready: {nodegroup.name} "
                f"in cluster {cluster.uuid}"
            )
            nodegroup.save()

        elif ng_state == NodeGroupState.FAILED:
            nodegroup.status = (
                fields.ClusterStatus.UPDATE_FAILED
                if is_update_operation
                else fields.ClusterStatus.CREATE_FAILED
            )
            LOG.debug(
                f"Node group failed: {nodegroup.name} "
                f"in cluster {cluster.uuid}"
            )
            nodegroup.save()
        elif ng_state == NodeGroupState.NOT_PRESENT:
            LOG.debug(
                f"Node group not yet found: {nodegroup.name} "
                f"state:{nodegroup.status} in cluster {cluster.uuid}"
            )
        else:
            LOG.debug(
                f"Node group still pending: {nodegroup.name} "
                f"state:{nodegroup.status} in cluster {cluster.uuid}"
            )

        return nodegroup

    def _nodegroup_machines_exist(self, cluster, nodegroup):
        cluster_name = self._get_chart_release_name(cluster)
        nodegroup_name = self._sanitised_name(nodegroup.name)
        machines = self._k8s_client.get_all_machines_by_label(
            {
                "capi.stackhpc.com/cluster": cluster_name,
                "capi.stackhpc.com/component": "worker",
                "capi.stackhpc.com/node-group": nodegroup_name,
            },
            self._namespace(cluster),
        )
        return bool(machines)

    def _update_cluster_api_address(self, cluster, capi_cluster):
        # As soon as we know the API address, we should set it
        # This means users can access the API even if the create is
        # not complete, which could be useful for debugging failures,
        # e.g. with addons
        if not capi_cluster:
            # skip update if cluster not yet created
            return

        if cluster.status not in [
            fields.ClusterStatus.CREATE_IN_PROGRESS,
            fields.ClusterStatus.UPDATE_IN_PROGRESS,
        ]:
            # only update api-address when updating or creating
            return

        api_endpoint = capi_cluster["spec"].get("controlPlaneEndpoint")
        if api_endpoint:
            api_address = (
                f"https://{api_endpoint['host']}:{api_endpoint['port']}"
            )
            if cluster.api_address != api_address:
                cluster.api_address = api_address
                cluster.save()
                LOG.debug(f"Found api_address for {cluster.uuid}")

    def _update_status_updating(self, cluster, capi_cluster):
        # If the cluster is not yet ready then the create/update
        # is still in progress
        true_conditions = {
            cond["type"]
            for cond in capi_cluster.get("status", {}).get("conditions", [])
            if cond["status"] == "True"
        }
        for cond in ("InfrastructureReady", "ControlPlaneReady", "Ready"):
            if cond not in true_conditions:
                return

        is_update_operation = cluster.status.startswith("UPDATE_")

        # Check the status of the addons
        addons = self._k8s_client.get_addons_by_label(
            {
                "addons.stackhpc.com/cluster": self._sanitised_name(
                    self._get_chart_release_name(cluster)
                ),
            },
            self._namespace(cluster)
        )
        for addon in addons:
            addon_phase = addon.get("status", {}).get("phase")
            if addon_phase and addon_phase in {"Failed", "Unknown"}:
                # If the addon is failed, mark the cluster as failed
                cluster.status = (
                    fields.ClusterStatus.UPDATE_FAILED
                    if is_update_operation
                    else fields.ClusterStatus.CREATE_FAILED
                )
                cluster.save()
                return
            elif addon_phase and addon_phase == "Deployed":
                # If the addon is deployed, move on to the next one
                continue
            else:
                # If there are any addons that are not deployed or failed,
                # wait for the next invocation to check again
                LOG.debug(
                    f"addon {addon['metadata']['name']} not yet deployed "
                    f"for {cluster.uuid}"
                )
                return

        # If we get this far, the cluster has completed successfully
        cluster.status = (
            fields.ClusterStatus.UPDATE_COMPLETE
            if is_update_operation
            else fields.ClusterStatus.CREATE_COMPLETE
        )
        cluster.save()

    def _update_status_deleting(self, context, cluster):
        # Once the Cluster API cluster is gone, we need to clean up
        # the secrets we created
        self._k8s_client.delete_all_secrets_by_label(
            "magnum.openstack.org/cluster-uuid",
            cluster.uuid,
            self._namespace(cluster),
        )

        # We also need to clean up the appcred that we made
        app_creds.delete_app_cred(context, cluster)

        cluster.status = fields.ClusterStatus.DELETE_COMPLETE
        cluster.save()

    def _get_capi_cluster(self, cluster):
        return self._k8s_client.get_capi_cluster(
            self._sanitised_name(self._get_chart_release_name(cluster)),
            self._namespace(cluster),
        )

    def _update_all_nodegroups_status(self, cluster):
        """Returns True if any node group still in progress."""
        nodegroups = []
        for nodegroup in cluster.nodegroups:
            if nodegroup.role == NODE_GROUP_ROLE_CONTROLLER:
                updated_nodegroup = (
                    self._update_control_plane_nodegroup_status(
                        cluster, nodegroup
                    )
                )
            else:
                updated_nodegroup = self._update_worker_nodegroup_status(
                    cluster, nodegroup
                )
            if updated_nodegroup:
                nodegroups.append(updated_nodegroup)

        # Return True if any are still in progress
        for nodegroup in nodegroups:
            if nodegroup.status.endswith("_IN_PROGRESS"):
                return True
        return False

    def update_cluster_status(self, context, cluster):
        # NOTE(mkjpryor)
        # Because Kubernetes operators are built around reconciliation loops,
        # Cluster API clusters don't really go into an error state
        # Hence we only currently handle transitioning from IN_PROGRESS
        # states to COMPLETE

        # TODO(mkjpryor) Add a timeout for create/update/delete

        # Update the cluster API address if it is known
        # so users can get their coe credentials
        capi_cluster = self._get_capi_cluster(cluster)
        self._update_cluster_api_address(cluster, capi_cluster)

        # Update the nodegroups first
        # to ensure API never returns an inconsistent state
        nodegroups_in_progress = self._update_all_nodegroups_status(cluster)

        if cluster.status in {
            fields.ClusterStatus.CREATE_IN_PROGRESS,
            fields.ClusterStatus.UPDATE_IN_PROGRESS,
        }:
            LOG.debug("Checking on an update for %s", cluster.uuid)
            # If the cluster does not exist yet,
            # create is still in progress
            if not capi_cluster:
                LOG.debug(f"capi_cluster not yet created for {cluster.uuid}")
                return
            if nodegroups_in_progress:
                LOG.debug(f"Node groups are not all ready for {cluster.uuid}")
                return
            self._update_status_updating(cluster, capi_cluster)

        elif cluster.status == fields.ClusterStatus.DELETE_IN_PROGRESS:
            LOG.debug("Checking on a delete for %s", cluster.uuid)
            # If the Cluster API cluster still exists,
            # the delete is still in progress
            if capi_cluster:
                LOG.debug(f"capi_cluster still found for {cluster.uuid}")
                return
            self._update_status_deleting(context, cluster)

    def get_monitor(self, context, cluster):
        return k8s_monitor.K8sMonitor(context, cluster)

    def _namespace(self, cluster):
        # We create clusters in a project-specific namespace
        # To generate the namespace, first sanitize the project id
        project_id = re.sub("[^a-z0-9]", "", cluster.project_id.lower())
        suffix = CONF.capi_driver.magnum_namespace_suffix
        return f"{suffix}-{project_id}"

    def _label(self, cluster, key, default):
        all_labels = helm.mergeconcat(
            cluster.cluster_template.labels, cluster.labels
        )
        if not all_labels:
            return default
        raw = all_labels.get(key, default)
        # NOTE(johngarbutt): filtering untrusted user input
        return re.sub(r"[^a-z0-9\.\-\/]+", "", raw)

    def _get_chart_version(self, cluster):
        version = cluster.cluster_template.labels.get(
            "capi_helm_chart_version", CONF.capi_driver.helm_chart_version
        )
        # NOTE(johngarbutt): filtering untrusted user input
        return re.sub(r"[^a-z0-9\.\-]+", "", version)

    def _sanitised_name(self, name, suffix=None):
        return re.sub(
            "[^a-z0-9]+",
            "-",
            (f"{name}-{suffix}" if suffix else name).lower(),
        )

    def _get_kube_version(self, image):
        # The image should have a property containing the Kubernetes version
        kube_version = image.get("kube_version")
        if not kube_version:
            raise exception.KubeVersionPropertyNotFound(image_id=image.id)
        return kube_version.lstrip("v")

    def _get_image_details(self, context, image_identifier):
        osc = clients.OpenStackClients(context)
        image = api_utils.get_openstack_resource(
            osc.glance().images, image_identifier, "images"
        )
        return image.id, self._get_kube_version(image)

    def _get_app_cred_name(self, cluster):
        return self._sanitised_name(
            self._get_chart_release_name(cluster), "cloud-credentials"
        )

    def _get_monitoring_enabled(self, cluster):
        mon_label = self._label(cluster, "monitoring_enabled", "")
        # NOTE(mkjpryor) default of, like heat driver,
        # as requires cinder and takes a while
        return mon_label == "true"

    def _get_kube_dash_enabled(self, cluster):
        kube_dash_label = self._label(cluster, "kube_dashboard_enabled", "")
        # NOTE(mkjpryor) default on, like the heat driver
        return kube_dash_label != "false"

    def _update_helm_release(self, context, cluster, nodegroups=None):
        if nodegroups is None:
            nodegroups = cluster.nodegroups
        cluster_template = cluster.cluster_template
        image_id, kube_version = self._get_image_details(
            context, cluster_template.image_id
        )
        values = {
            "kubernetesVersion": kube_version,
            "machineImageId": image_id,
            "cloudCredentialsSecretName": self._get_app_cred_name(cluster),
            # TODO(johngarbutt): need to respect requested networks
            "clusterNetworking": {
                "internalNetwork": {
                    "nodeCidr": self._label(
                        cluster, "fixed_subnet_cidr", "10.0.0.0/24"
                    ),
                }
            },
            "apiServer": {
                "enableLoadBalancer": True,
                "loadBalancerProvider": self._label(
                    cluster, "octavia_provider", "amphora"
                ),
            },
            "controlPlane": {
                "machineFlavor": cluster.master_flavor_id,
                "machineCount": cluster.master_count,
            },
            "addons": {
                "monitoring": {
                    "enabled": self._get_monitoring_enabled(cluster)
                },
                "kubernetesDashboard": {
                    "enabled": self._get_kube_dash_enabled(cluster)
                },
                # TODO(mkjpryor): can't enable ingress until code exists to
                #                 remove the load balancer
                "ingress": {"enabled": False},
            },
            "nodeGroups": [
                {
                    "name": self._sanitised_name(ng.name),
                    "machineFlavor": ng.flavor_id,
                    "machineCount": ng.node_count,
                }
                for ng in nodegroups
                if ng.role != NODE_GROUP_ROLE_CONTROLLER
            ],
        }

        if cluster_template.dns_nameserver:
            dns_nameservers = cluster_template.dns_nameserver.split(",")
            values["clusterNetworking"]["dnsNameservers"] = dns_nameservers

        if cluster.keypair:
            values["machineSSHKeyName"] = cluster.keypair

        chart_version = self._get_chart_version(cluster)

        self._helm_client.install_or_upgrade(
            self._get_chart_release_name(cluster),
            CONF.capi_driver.helm_chart_name,
            values,
            repo=CONF.capi_driver.helm_chart_repo,
            version=chart_version,
            namespace=self._namespace(cluster),
        )

    def _generate_release_name(self, cluster):
        if cluster.stack_id:
            return

        # Make sure no duplicate names
        # by generating 12 character random id
        random_bit = short_id.generate_id()
        base_name = self._sanitised_name(cluster.name)
        # valid release names are 53 chars long
        # and stack_id is 12 characters
        # but we also use this to derive hostnames
        trimmed_name = base_name[:30]
        # Save the full name, so users can rename in the API
        cluster.stack_id = f"{trimmed_name}-{random_bit}".lower()
        # be sure to save this before we use it
        cluster.save()

    def _get_chart_release_name(self, cluster):
        return cluster.stack_id

    def _k8s_resource_labels(self, cluster):
        return {
            "magnum.openstack.org/project-id": cluster.project_id,
            "magnum.openstack.org/user-id": cluster.user_id,
            "magnum.openstack.org/cluster-uuid": cluster.uuid,
        }

    def _create_appcred_secret(self, context, cluster):
        ca_certificate = app_creds.get_openstack_ca_certificate()
        appcred_yaml = app_creds.get_app_cred_yaml(context, cluster)
        name = self._get_app_cred_name(cluster)
        self._k8s_client.apply_secret(
            name,
            {
                "metadata": {"labels": self._k8s_resource_labels(cluster)},
                "stringData": {
                    "cacert": ca_certificate,
                    "clouds.yaml": appcred_yaml,
                },
            },
            self._namespace(cluster),
        )

    def _decode_cert(self, cert):
        return encodeutils.safe_decode(cert.get_certificate())

    def _decode_key(self, cert):
        key = x509.decrypt_key(
            cert.get_private_key(),
            cert.get_private_key_passphrase(),
        )
        return encodeutils.safe_decode(key)

    def _ensure_certificate_secrets(self, context, cluster):
        # Magnum creates CA certs for each of the Kubernetes components that
        # must be trusted by the cluster
        # In particular, this is required for "openstack coe cluster config"
        # to work, as that doesn't communicate with the driver and instead
        # relies on the correct CA being trusted by the cluster

        # Cluster API looks for specific named secrets for each of the CAs,
        # and generates them if they don't exist, so we create them here
        # with the correct certificates in
        certificates = {
            "ca": cert_manager.get_cluster_ca_certificate(cluster, context),
            "etcd": cert_manager.get_cluster_ca_certificate(
                cluster, context, "etcd"
            ),
            "proxy": cert_manager.get_cluster_ca_certificate(
                cluster, context, "front_proxy"
            ),
            "sa": cert_manager.get_cluster_magnum_cert(cluster, context),
        }
        for name, cert in certificates.items():
            self._k8s_client.apply_secret(
                self._sanitised_name(
                    self._get_chart_release_name(cluster), name
                ),
                {
                    "metadata": {"labels": self._k8s_resource_labels(cluster)},
                    "type": "cluster.x-k8s.io/secret",
                    "stringData": {
                        "tls.crt": self._decode_cert(cert),
                        "tls.key": self._decode_key(cert),
                    },
                },
                self._namespace(cluster),
            )

    def create_cluster(self, context, cluster, cluster_create_timeout):
        LOG.info("Starting to create cluster %s", cluster.uuid)

        # we generate this name (on the initial create call only)
        # so we hit no issues with duplicate cluster names
        # and it makes renaming clusters in the API possible
        self._generate_release_name(cluster)

        # NOTE(johngarbutt) all node groups should already
        # be in the CREATE_IN_PROGRESS state
        self._k8s_client.ensure_namespace(self._namespace(cluster))
        self._create_appcred_secret(context, cluster)
        self._ensure_certificate_secrets(context, cluster)

        self._update_helm_release(context, cluster)

    def update_cluster(
        self, context, cluster, scale_manager=None, rollback=False
    ):
        # Cluster API refuses to update things like cluster networking,
        # so it is safest not to implement this for now
        # TODO(mkjpryor) Check what bits of update we can support
        raise NotImplementedError(
            "Updating a cluster in this way is not currently supported"
        )

    def delete_cluster(self, context, cluster):
        LOG.info("Starting to delete cluster %s", cluster.uuid)

        # Copy the helm driver by marking all node groups
        # as delete in progress here, as note done by conductor
        # We do this before calling uninstall_release because
        # update_cluster_status can get called before we return
        for ng in cluster.nodegroups:
            ng.status = fields.ClusterStatus.DELETE_IN_PROGRESS
            ng.save()

        # Begin the deletion of the cluster resources by uninstalling the
        # Helm release
        # Note that this just marks the resources for deletion - it does not
        # wait for the resources to be deleted
        self._helm_client.uninstall_release(
            self._get_chart_release_name(cluster),
            namespace=self._namespace(cluster),
        )

    def resize_cluster(
        self,
        context,
        cluster,
        resize_manager,
        node_count,
        nodes_to_remove,
        nodegroup=None,
    ):
        if nodes_to_remove:
            LOG.warning("Removing specific nodes is not currently supported")
        self._update_helm_release(context, cluster)

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
        # TODO(mkjpryor) check that the upgrade is viable
        # e.g. not a downgrade, not an upgrade by more than one minor version

        # Updating the template will likely apply for all nodegroups
        # So mark them all as having an update in progress
        for nodegroup in cluster.nodegroups:
            nodegroup.status = fields.ClusterStatus.UPDATE_IN_PROGRESS
            nodegroup.save()

        # Move the cluster to the new template
        cluster.cluster_template_id = cluster_template.uuid
        cluster.status = fields.ClusterStatus.UPDATE_IN_PROGRESS
        cluster.save()
        cluster.refresh()

        self._update_helm_release(context, cluster)

    def create_nodegroup(self, context, cluster, nodegroup):
        nodegroup.status = fields.ClusterStatus.CREATE_IN_PROGRESS
        nodegroup.save()

        self._update_helm_release(context, cluster)

    def update_nodegroup(self, context, cluster, nodegroup):
        nodegroup.status = fields.ClusterStatus.UPDATE_IN_PROGRESS
        nodegroup.save()

        self._update_helm_release(context, cluster)

    def delete_nodegroup(self, context, cluster, nodegroup):
        nodegroup.status = fields.ClusterStatus.DELETE_IN_PROGRESS
        nodegroup.save()

        # Remove the nodegroup being deleted from the nodegroups
        # for the Helm release
        self._update_helm_release(
            context,
            cluster,
            [ng for ng in cluster.nodegroups if ng.name != nodegroup.name]
        )

    def create_federation(self, context, federation):
        return NotImplementedError("Will not implement 'create_federation'")

    def update_federation(self, context, federation):
        return NotImplementedError("Will no implement 'update_federation'")

    def delete_federation(self, context, federation):
        return NotImplementedError("Will not implement 'delete_federation'")
