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
from unittest import mock

from magnum.common import exception
from magnum.common.x509 import operations as x509
from magnum.conductor.handlers.common import cert_manager
from magnum import conf
from magnum.drivers.cluster_api import app_creds
from magnum.drivers.cluster_api import driver
from magnum.drivers.cluster_api import helm
from magnum.drivers.cluster_api import kubernetes
from magnum.drivers.common import k8s_monitor
from magnum import objects
from magnum.objects import fields
from magnum.tests.unit.db import base
from magnum.tests.unit.objects import utils as obj_utils

CONF = conf.CONF


class ClusterAPIDriverTest(base.DbTestCase):
    def setUp(self):
        super(ClusterAPIDriverTest, self).setUp()
        self.driver = driver.Driver()
        self.cluster_obj = obj_utils.create_test_cluster(
            self.context,
            name="cluster_example_$A",
            master_flavor_id="flavor_small",
            flavor_id="flavor_medium",
            stack_id="cluster-example-a-111111111111",
        )

    def test_provides(self):
        self.assertEqual(
            [{"server_type": "vm", "os": "ubuntu", "coe": "kubernetes"}],
            self.driver.provides,
        )

    @mock.patch.object(driver.Driver, "_update_status_deleting")
    @mock.patch.object(driver.Driver, "_update_status_updating")
    @mock.patch.object(driver.Driver, "_update_all_nodegroups_status")
    @mock.patch.object(driver.Driver, "_get_capi_cluster")
    def test_update_cluster_status_creating(
        self, mock_capi, mock_ng, mock_update, mock_delete
    ):
        mock_ng.return_value = True
        mock_capi.return_value = {"spec": {}}
        self.cluster_obj.status = fields.ClusterStatus.CREATE_IN_PROGRESS

        self.driver.update_cluster_status(self.context, self.cluster_obj)

        mock_ng.assert_called_once_with(self.cluster_obj)
        mock_update.assert_not_called()
        mock_delete.assert_not_called()

    @mock.patch.object(driver.Driver, "_update_status_deleting")
    @mock.patch.object(driver.Driver, "_update_status_updating")
    @mock.patch.object(driver.Driver, "_update_all_nodegroups_status")
    @mock.patch.object(driver.Driver, "_get_capi_cluster")
    def test_update_cluster_status_creating_not_found(
        self, mock_capi, mock_ng, mock_update, mock_delete
    ):
        mock_ng.return_value = True
        mock_capi.return_value = None
        self.cluster_obj.status = fields.ClusterStatus.CREATE_IN_PROGRESS

        self.driver.update_cluster_status(self.context, self.cluster_obj)

        mock_ng.assert_called_once_with(self.cluster_obj)
        mock_update.assert_not_called()
        mock_delete.assert_not_called()

    @mock.patch.object(driver.Driver, "_update_status_deleting")
    @mock.patch.object(driver.Driver, "_update_status_updating")
    @mock.patch.object(driver.Driver, "_update_all_nodegroups_status")
    @mock.patch.object(driver.Driver, "_get_capi_cluster")
    def test_update_cluster_status_created(
        self, mock_capi, mock_ng, mock_update, mock_delete
    ):
        mock_ng.return_value = False
        mock_capi.return_value = {"spec": {}}
        self.cluster_obj.status = fields.ClusterStatus.CREATE_IN_PROGRESS

        self.driver.update_cluster_status(self.context, self.cluster_obj)

        mock_ng.assert_called_once_with(self.cluster_obj)
        mock_update.assert_called_once_with(self.cluster_obj, {"spec": {}})
        mock_delete.assert_not_called()

    @mock.patch.object(driver.Driver, "_update_status_deleting")
    @mock.patch.object(driver.Driver, "_update_status_updating")
    @mock.patch.object(driver.Driver, "_update_all_nodegroups_status")
    @mock.patch.object(driver.Driver, "_get_capi_cluster")
    def test_update_cluster_status_deleted(
        self, mock_capi, mock_ng, mock_update, mock_delete
    ):
        mock_capi.return_value = None
        self.cluster_obj.status = fields.ClusterStatus.DELETE_IN_PROGRESS

        self.driver.update_cluster_status(self.context, self.cluster_obj)

        mock_ng.assert_called_once_with(self.cluster_obj)
        mock_update.assert_not_called()
        mock_delete.assert_called_once_with(self.context, self.cluster_obj)

    @mock.patch.object(driver.Driver, "_update_status_deleting")
    @mock.patch.object(driver.Driver, "_update_status_updating")
    @mock.patch.object(driver.Driver, "_update_all_nodegroups_status")
    @mock.patch.object(driver.Driver, "_get_capi_cluster")
    def test_update_cluster_status_deleting(
        self, mock_capi, mock_ng, mock_update, mock_delete
    ):
        mock_capi.return_value = {"spec": {}}
        self.cluster_obj.status = fields.ClusterStatus.DELETE_IN_PROGRESS

        self.driver.update_cluster_status(self.context, self.cluster_obj)

        mock_ng.assert_called_once_with(self.cluster_obj)
        mock_update.assert_not_called()
        mock_delete.assert_not_called()

    @mock.patch.object(driver.Driver, "_update_status_deleting")
    @mock.patch.object(driver.Driver, "_update_status_updating")
    @mock.patch.object(driver.Driver, "_update_all_nodegroups_status")
    @mock.patch.object(driver.Driver, "_get_capi_cluster")
    def test_update_cluster_status_create_complete(
        self, mock_capi, mock_ng, mock_update, mock_delete
    ):
        mock_capi.return_value = {"spec": {}}
        self.cluster_obj.status = fields.ClusterStatus.CREATE_COMPLETE

        self.driver.update_cluster_status(self.context, self.cluster_obj)

        mock_ng.assert_called_once_with(self.cluster_obj)
        mock_update.assert_not_called()
        mock_delete.assert_not_called()

    @mock.patch.object(driver.Driver, "_update_worker_nodegroup_status")
    @mock.patch.object(driver.Driver, "_update_control_plane_nodegroup_status")
    def test_update_all_nodegroups_status_not_in_progress(
        self, mock_cp, mock_w
    ):
        control_plane = [
            ng
            for ng in self.cluster_obj.nodegroups
            if ng.role == driver.NODE_GROUP_ROLE_CONTROLLER
        ][0]
        control_plane.status = fields.ClusterStatus.CREATE_COMPLETE
        mock_cp.return_value = control_plane
        mock_w.return_value = None

        result = self.driver._update_all_nodegroups_status(self.cluster_obj)

        self.assertFalse(result)
        control_plane = [
            ng
            for ng in self.cluster_obj.nodegroups
            if ng.role == driver.NODE_GROUP_ROLE_CONTROLLER
        ][0]
        mock_cp.assert_called_once_with(self.cluster_obj, mock.ANY)
        self.assertEqual(
            control_plane.obj_to_primitive(),
            mock_cp.call_args_list[0][0][1].obj_to_primitive(),
        )
        mock_w.assert_called_once_with(self.cluster_obj, mock.ANY)
        worker = [
            ng
            for ng in self.cluster_obj.nodegroups
            if ng.role != driver.NODE_GROUP_ROLE_CONTROLLER
        ][0]
        self.assertEqual(
            worker.obj_to_primitive(),
            mock_w.call_args_list[0][0][1].obj_to_primitive(),
        )

    @mock.patch.object(driver.Driver, "_update_worker_nodegroup_status")
    @mock.patch.object(driver.Driver, "_update_control_plane_nodegroup_status")
    def test_update_all_nodegroups_status_in_progress(self, mock_cp, mock_w):
        control_plane = [
            ng
            for ng in self.cluster_obj.nodegroups
            if ng.role == driver.NODE_GROUP_ROLE_CONTROLLER
        ][0]
        control_plane.status = fields.ClusterStatus.CREATE_IN_PROGRESS
        mock_cp.return_value = control_plane
        mock_w.return_value = None

        result = self.driver._update_all_nodegroups_status(self.cluster_obj)

        self.assertTrue(result)
        mock_cp.assert_called_once_with(self.cluster_obj, mock.ANY)
        mock_w.assert_called_once_with(self.cluster_obj, mock.ANY)

    @mock.patch.object(driver.Driver, "_update_nodegroup_status")
    @mock.patch.object(kubernetes.Client, "load")
    def test_update_worker_nodegroup_status_empty(
        self, mock_load, mock_update
    ):
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_load.return_value = mock_client
        nodegroup = mock.MagicMock()
        nodegroup.name = "workers"
        mock_client.get_machine_deployment.return_value = None

        self.driver._update_worker_nodegroup_status(
            self.cluster_obj, nodegroup
        )

        mock_client.get_machine_deployment.assert_called_once_with(
            "cluster-example-a-111111111111-workers", "magnum-fakeproject"
        )
        mock_update.assert_called_once_with(
            self.cluster_obj, mock.ANY, driver.NodeGroupState.NOT_PRESENT
        )

    @mock.patch.object(driver.Driver, "_update_nodegroup_status")
    @mock.patch.object(kubernetes.Client, "load")
    def test_update_worker_nodegroup_status_scaling_up(
        self, mock_load, mock_update
    ):
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_load.return_value = mock_client
        nodegroup = mock.MagicMock()
        nodegroup.name = "workers"
        md = {"status": {"phase": "ScalingUp"}}
        mock_client.get_machine_deployment.return_value = md

        self.driver._update_worker_nodegroup_status(
            self.cluster_obj, nodegroup
        )

        mock_client.get_machine_deployment.assert_called_once_with(
            "cluster-example-a-111111111111-workers", "magnum-fakeproject"
        )
        mock_update.assert_called_once_with(
            self.cluster_obj, mock.ANY, driver.NodeGroupState.PENDING
        )

    @mock.patch.object(driver.Driver, "_update_nodegroup_status")
    @mock.patch.object(kubernetes.Client, "load")
    def test_update_worker_nodegroup_status_failed(
        self, mock_load, mock_update
    ):
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_load.return_value = mock_client
        nodegroup = mock.MagicMock()
        nodegroup.name = "workers"
        md = {"status": {"phase": "Failed"}}
        mock_client.get_machine_deployment.return_value = md

        self.driver._update_worker_nodegroup_status(
            self.cluster_obj, nodegroup
        )

        mock_client.get_machine_deployment.assert_called_once_with(
            "cluster-example-a-111111111111-workers", "magnum-fakeproject"
        )
        mock_update.assert_called_once_with(
            self.cluster_obj, mock.ANY, driver.NodeGroupState.FAILED
        )

    @mock.patch.object(driver.Driver, "_update_nodegroup_status")
    @mock.patch.object(kubernetes.Client, "load")
    def test_update_worker_nodegroup_status_running(
        self, mock_load, mock_update
    ):
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_load.return_value = mock_client
        nodegroup = mock.MagicMock()
        nodegroup.name = "workers"
        md = {"status": {"phase": "Running"}}
        mock_client.get_machine_deployment.return_value = md

        self.driver._update_worker_nodegroup_status(
            self.cluster_obj, nodegroup
        )

        mock_client.get_machine_deployment.assert_called_once_with(
            "cluster-example-a-111111111111-workers", "magnum-fakeproject"
        )
        mock_update.assert_called_once_with(
            self.cluster_obj, mock.ANY, driver.NodeGroupState.READY
        )

    @mock.patch.object(driver.Driver, "_update_nodegroup_status")
    @mock.patch.object(kubernetes.Client, "load")
    def test_update_control_plane_nodegroup_status_empty(
        self, mock_load, mock_update
    ):
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_load.return_value = mock_client
        nodegroup = mock.MagicMock()
        nodegroup.name = "masters"
        mock_client.get_kubeadm_control_plane.return_value = None

        self.driver._update_control_plane_nodegroup_status(
            self.cluster_obj, nodegroup
        )

        mock_client.get_kubeadm_control_plane.assert_called_once_with(
            "cluster-example-a-111111111111-control-plane",
            "magnum-fakeproject",
        )
        mock_update.assert_called_once_with(
            self.cluster_obj, mock.ANY, driver.NodeGroupState.NOT_PRESENT
        )

    @mock.patch.object(driver.Driver, "_update_nodegroup_status")
    @mock.patch.object(kubernetes.Client, "load")
    def test_update_control_plane_nodegroup_status_condition_false(
        self, mock_load, mock_update
    ):
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_load.return_value = mock_client
        nodegroup = mock.MagicMock()
        nodegroup.name = "masters"
        kcp = {
            "spec": {
                "replicas": 3,
            },
            "status": {
                "conditions": [
                    {"type": "MachinesReady", "status": "True"},
                    {"type": "Ready", "status": "True"},
                    {"type": "EtcdClusterHealthy", "status": "True"},
                    {
                        "type": "ControlPlaneComponentsHealthy",
                        "status": "False",
                    },
                ],
                "replicas": 3,
                "updatedReplicas": 3,
                "readyReplicas": 3,
            }
        }
        mock_client.get_kubeadm_control_plane.return_value = kcp

        self.driver._update_control_plane_nodegroup_status(
            self.cluster_obj, nodegroup
        )

        mock_client.get_kubeadm_control_plane.assert_called_once_with(
            "cluster-example-a-111111111111-control-plane",
            "magnum-fakeproject",
        )
        mock_update.assert_called_once_with(
            self.cluster_obj, mock.ANY, driver.NodeGroupState.PENDING
        )

    @mock.patch.object(driver.Driver, "_update_nodegroup_status")
    @mock.patch.object(kubernetes.Client, "load")
    def test_update_control_plane_nodegroup_status_mismatched_replicas(
        self, mock_load, mock_update
    ):
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_load.return_value = mock_client
        nodegroup = mock.MagicMock()
        nodegroup.name = "masters"
        kcp = {
            "spec": {
                "replicas": 3,
            },
            "status": {
                "conditions": [
                    {"type": "MachinesReady", "status": "True"},
                    {"type": "Ready", "status": "True"},
                    {"type": "EtcdClusterHealthy", "status": "True"},
                    {
                        "type": "ControlPlaneComponentsHealthy",
                        "status": "True",
                    },
                ],
                "replicas": 3,
                "updatedReplicas": 2,
                "readyReplicas": 2,
            }
        }
        mock_client.get_kubeadm_control_plane.return_value = kcp

        self.driver._update_control_plane_nodegroup_status(
            self.cluster_obj, nodegroup
        )

        mock_client.get_kubeadm_control_plane.assert_called_once_with(
            "cluster-example-a-111111111111-control-plane",
            "magnum-fakeproject",
        )
        mock_update.assert_called_once_with(
            self.cluster_obj, mock.ANY, driver.NodeGroupState.PENDING
        )

    @mock.patch.object(driver.Driver, "_update_nodegroup_status")
    @mock.patch.object(kubernetes.Client, "load")
    def test_update_control_plane_nodegroup_status_ready(
        self, mock_load, mock_update
    ):
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_load.return_value = mock_client
        nodegroup = mock.MagicMock()
        nodegroup.name = "masters"
        kcp = {
            "spec": {
                "replicas": 3,
            },
            "status": {
                "conditions": [
                    {"type": "MachinesReady", "status": "True"},
                    {"type": "Ready", "status": "True"},
                    {"type": "EtcdClusterHealthy", "status": "True"},
                    {
                        "type": "ControlPlaneComponentsHealthy",
                        "status": "True",
                    },
                ],
                "replicas": 3,
                "updatedReplicas": 3,
                "readyReplicas": 3,
            }
        }
        mock_client.get_kubeadm_control_plane.return_value = kcp

        self.driver._update_control_plane_nodegroup_status(
            self.cluster_obj, nodegroup
        )

        mock_client.get_kubeadm_control_plane.assert_called_once_with(
            "cluster-example-a-111111111111-control-plane",
            "magnum-fakeproject",
        )
        mock_update.assert_called_once_with(
            self.cluster_obj, mock.ANY, driver.NodeGroupState.READY
        )

    @mock.patch.object(k8s_monitor, "K8sMonitor")
    def test_get_monitor(self, mock_mon):
        self.driver.get_monitor(self.context, self.cluster_obj)
        mock_mon.assert_called_once_with(self.context, self.cluster_obj)

    @mock.patch.object(kubernetes.Client, "load")
    def test_get_capi_cluster(self, mock_load):
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_load.return_value = mock_client

        self.driver._get_capi_cluster(self.cluster_obj)

        mock_client.get_capi_cluster.assert_called_once_with(
            "cluster-example-a-111111111111", "magnum-fakeproject"
        )

    @mock.patch.object(app_creds, "delete_app_cred")
    @mock.patch.object(kubernetes.Client, "load")
    def test_update_status_deleting(self, mock_load, mock_delete):
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_load.return_value = mock_client

        self.driver._update_status_deleting(self.context, self.cluster_obj)

        self.assertEqual("DELETE_COMPLETE", self.cluster_obj.status)
        mock_delete.assert_called_once_with(self.context, self.cluster_obj)
        mock_client.delete_all_secrets_by_label.assert_called_once_with(
            "magnum.openstack.org/cluster-uuid",
            self.cluster_obj.uuid,
            "magnum-fakeproject",
        )

    def test_update_status_updating_not_ready(self):
        self.cluster_obj.status = fields.ClusterStatus.CREATE_IN_PROGRESS
        capi_cluster = {}

        self.driver._update_status_updating(self.cluster_obj, capi_cluster)

        self.assertEqual(
            fields.ClusterStatus.CREATE_IN_PROGRESS, self.cluster_obj.status
        )

    @mock.patch.object(kubernetes.Client, "load")
    def test_update_status_updating_condition_false(self, mock_load):
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_client.get_addons_by_label.return_value = []
        mock_load.return_value = mock_client

        self.cluster_obj.status = fields.ClusterStatus.CREATE_IN_PROGRESS
        capi_cluster = {
            "status": {
                "conditions": [
                    dict(type="InfrastructureReady", status="True"),
                    dict(type="ControlPlaneReady", status="True"),
                    dict(type="Ready", status="False"),
                ]
            }
        }

        self.driver._update_status_updating(self.cluster_obj, capi_cluster)

        self.assertEqual(
            fields.ClusterStatus.CREATE_IN_PROGRESS, self.cluster_obj.status
        )

    @mock.patch.object(kubernetes.Client, "load")
    def test_update_status_updating_ready_created(self, mock_load):
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_client.get_addons_by_label.return_value = []
        mock_load.return_value = mock_client

        self.cluster_obj.status = fields.ClusterStatus.CREATE_IN_PROGRESS
        capi_cluster = {
            "status": {
                "conditions": [
                    dict(type="InfrastructureReady", status="True"),
                    dict(type="ControlPlaneReady", status="True"),
                    dict(type="Ready", status="True"),
                ]
            }
        }

        self.driver._update_status_updating(self.cluster_obj, capi_cluster)

        self.assertEqual(
            fields.ClusterStatus.CREATE_COMPLETE, self.cluster_obj.status
        )

    @mock.patch.object(kubernetes.Client, "load")
    def test_update_status_updating_addons_unknown(self, mock_load):
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_client.get_addons_by_label.return_value = [
            {
                "metadata": {"name": "cni"},
                "status": {},
            },
            {
                "metadata": {"name": "monitoring"},
                "status": {},
            },
        ]
        mock_load.return_value = mock_client

        self.cluster_obj.status = fields.ClusterStatus.CREATE_IN_PROGRESS
        capi_cluster = {
            "status": {
                "conditions": [
                    dict(type="InfrastructureReady", status="True"),
                    dict(type="ControlPlaneReady", status="True"),
                    dict(type="Ready", status="True"),
                ]
            }
        }

        self.driver._update_status_updating(self.cluster_obj, capi_cluster)

        self.assertEqual(
            fields.ClusterStatus.CREATE_IN_PROGRESS, self.cluster_obj.status
        )

    @mock.patch.object(kubernetes.Client, "load")
    def test_update_status_updating_addons_installing(self, mock_load):
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_client.get_addons_by_label.return_value = [
            {
                "metadata": {"name": "cni"},
                "status": {"phase": "Deployed"},
            },
            {
                "metadata": {"name": "monitoring"},
                "status": {"phase": "Installing"},
            },
        ]
        mock_load.return_value = mock_client

        self.cluster_obj.status = fields.ClusterStatus.CREATE_IN_PROGRESS
        capi_cluster = {
            "status": {
                "conditions": [
                    dict(type="InfrastructureReady", status="True"),
                    dict(type="ControlPlaneReady", status="True"),
                    dict(type="Ready", status="True"),
                ]
            }
        }

        self.driver._update_status_updating(self.cluster_obj, capi_cluster)

        self.assertEqual(
            fields.ClusterStatus.CREATE_IN_PROGRESS, self.cluster_obj.status
        )

    @mock.patch.object(kubernetes.Client, "load")
    def test_update_status_updating_addons_deployed(self, mock_load):
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_client.get_addons_by_label.return_value = [
            {
                "metadata": {"name": "cni"},
                "status": {"phase": "Deployed"},
            },
            {
                "metadata": {"name": "monitoring"},
                "status": {"phase": "Deployed"},
            },
        ]
        mock_load.return_value = mock_client

        self.cluster_obj.status = fields.ClusterStatus.CREATE_IN_PROGRESS
        capi_cluster = {
            "status": {
                "conditions": [
                    dict(type="InfrastructureReady", status="True"),
                    dict(type="ControlPlaneReady", status="True"),
                    dict(type="Ready", status="True"),
                ]
            }
        }

        self.driver._update_status_updating(self.cluster_obj, capi_cluster)

        self.assertEqual(
            fields.ClusterStatus.CREATE_COMPLETE, self.cluster_obj.status
        )

    @mock.patch.object(kubernetes.Client, "load")
    def test_update_status_updating_addons_failed(self, mock_load):
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_client.get_addons_by_label.return_value = [
            {
                "metadata": {"name": "cni"},
                "status": {"phase": "Deployed"},
            },
            {
                "metadata": {"name": "monitoring"},
                "status": {"phase": "Failed"},
            },
        ]
        mock_load.return_value = mock_client

        self.cluster_obj.status = fields.ClusterStatus.CREATE_IN_PROGRESS
        capi_cluster = {
            "status": {
                "conditions": [
                    dict(type="InfrastructureReady", status="True"),
                    dict(type="ControlPlaneReady", status="True"),
                    dict(type="Ready", status="True"),
                ]
            }
        }

        self.driver._update_status_updating(self.cluster_obj, capi_cluster)

        self.assertEqual(
            fields.ClusterStatus.CREATE_FAILED, self.cluster_obj.status
        )

    @mock.patch.object(kubernetes.Client, "load")
    def test_update_status_updating_ready_updated(self, mock_load):
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_client.get_addons_by_label.return_value = []
        mock_load.return_value = mock_client

        self.cluster_obj.status = fields.ClusterStatus.UPDATE_IN_PROGRESS
        capi_cluster = {
            "status": {
                "conditions": [
                    dict(type="InfrastructureReady", status="True"),
                    dict(type="ControlPlaneReady", status="True"),
                    dict(type="Ready", status="True"),
                ]
            }
        }

        self.driver._update_status_updating(self.cluster_obj, capi_cluster)

        self.assertEqual(
            fields.ClusterStatus.UPDATE_COMPLETE, self.cluster_obj.status
        )

    def test_update_cluster_api_address(self):
        capi_cluster = {
            "spec": {"controlPlaneEndpoint": {"host": "foo", "port": 6443}}
        }

        self.driver._update_cluster_api_address(self.cluster_obj, capi_cluster)

        self.assertEqual("https://foo:6443", self.cluster_obj.api_address)

    def test_update_cluster_api_address_skip(self):
        self.cluster_obj.api_address = "asdf"
        capi_cluster = {"spec": {"foo": "bar"}}

        self.driver._update_cluster_api_address(self.cluster_obj, capi_cluster)

        self.assertEqual("asdf", self.cluster_obj.api_address)

    def test_update_cluster_api_address_skip_on_delete(self):
        self.cluster_obj.status = fields.ClusterStatus.DELETE_IN_PROGRESS
        self.cluster_obj.api_address = "asdf"
        capi_cluster = {
            "spec": {"controlPlaneEndpoint": {"host": "foo", "port": 6443}}
        }

        self.driver._update_cluster_api_address(self.cluster_obj, capi_cluster)

        self.assertEqual("asdf", self.cluster_obj.api_address)

    def test_update_nodegroup_status_create_complete(self):
        nodegroup = obj_utils.create_test_nodegroup(self.context)
        nodegroup.status = fields.ClusterStatus.CREATE_IN_PROGRESS

        updated = self.driver._update_nodegroup_status(
            self.cluster_obj, nodegroup, driver.NodeGroupState.READY
        )

        self.assertEqual(fields.ClusterStatus.CREATE_COMPLETE, updated.status)

    def test_update_nodegroup_status_update_complete(self):
        nodegroup = obj_utils.create_test_nodegroup(self.context)
        nodegroup.status = fields.ClusterStatus.UPDATE_IN_PROGRESS

        updated = self.driver._update_nodegroup_status(
            self.cluster_obj, nodegroup, driver.NodeGroupState.READY
        )

        self.assertEqual(fields.ClusterStatus.UPDATE_COMPLETE, updated.status)

    def test_update_nodegroup_status_create_failed(self):
        nodegroup = obj_utils.create_test_nodegroup(self.context)
        nodegroup.status = fields.ClusterStatus.CREATE_IN_PROGRESS

        updated = self.driver._update_nodegroup_status(
            self.cluster_obj, nodegroup, driver.NodeGroupState.FAILED
        )

        self.assertEqual(fields.ClusterStatus.CREATE_FAILED, updated.status)

    def test_update_nodegroup_status_update_failed(self):
        nodegroup = obj_utils.create_test_nodegroup(self.context)
        nodegroup.status = fields.ClusterStatus.UPDATE_IN_PROGRESS

        updated = self.driver._update_nodegroup_status(
            self.cluster_obj, nodegroup, driver.NodeGroupState.FAILED
        )

        self.assertEqual(fields.ClusterStatus.UPDATE_FAILED, updated.status)

    def test_update_nodegroup_status_create_in_progress(self):
        nodegroup = obj_utils.create_test_nodegroup(self.context)
        nodegroup.status = fields.ClusterStatus.CREATE_IN_PROGRESS

        updated = self.driver._update_nodegroup_status(
            self.cluster_obj, nodegroup, driver.NodeGroupState.PENDING
        )

        self.assertEqual(
            fields.ClusterStatus.CREATE_IN_PROGRESS, updated.status
        )

    def test_update_nodegroup_status_delete_in_progress(self):
        nodegroup = obj_utils.create_test_nodegroup(self.context)
        nodegroup.status = fields.ClusterStatus.DELETE_IN_PROGRESS

        updated = self.driver._update_nodegroup_status(
            self.cluster_obj, nodegroup, driver.NodeGroupState.PENDING
        )

        self.assertEqual(
            fields.ClusterStatus.DELETE_IN_PROGRESS, updated.status
        )
        self.assertEqual(nodegroup.as_dict(), updated.as_dict())

    def test_update_nodegroup_creating_but_not_found(self):
        nodegroup = obj_utils.create_test_nodegroup(self.context)
        nodegroup.status = fields.ClusterStatus.CREATE_IN_PROGRESS

        updated = self.driver._update_nodegroup_status(
            self.cluster_obj, nodegroup, driver.NodeGroupState.NOT_PRESENT
        )

        self.assertEqual(
            fields.ClusterStatus.CREATE_IN_PROGRESS, updated.status
        )

    def test_update_nodegroup_status_delete_return_none(self):
        nodegroup = obj_utils.create_test_nodegroup(self.context)
        nodegroup.status = fields.ClusterStatus.DELETE_IN_PROGRESS

        result = self.driver._update_nodegroup_status(
            self.cluster_obj, nodegroup, driver.NodeGroupState.NOT_PRESENT
        )

        self.assertIsNone(result)

    def test_update_nodegroup_status_delete_unexpected_state(self):
        nodegroup = obj_utils.create_test_nodegroup(self.context)
        nodegroup.status = fields.ClusterStatus.ROLLBACK_IN_PROGRESS

        updated = self.driver._update_nodegroup_status(
            self.cluster_obj, nodegroup, driver.NodeGroupState.NOT_PRESENT
        )

        self.assertEqual(
            fields.ClusterStatus.ROLLBACK_IN_PROGRESS, updated.status
        )
        self.assertEqual(nodegroup.as_dict(), updated.as_dict())

    def test_namespace(self):
        self.cluster_obj.project_id = "123-456F"

        namespace = self.driver._namespace(self.cluster_obj)

        self.assertEqual("magnum-123456f", namespace)

    def test_label_return_default(self):
        self.cluster_obj.labels = dict()
        self.cluster_obj.cluster_template.labels = dict()

        result = self.driver._label(self.cluster_obj, "foo", "bar")

        self.assertEqual("bar", result)

    def test_label_return_template(self):
        self.cluster_obj.cluster_template.labels = dict(foo=42)

        result = self.driver._label(self.cluster_obj, "foo", "bar")

        self.assertEqual("42", result)

    def test_label_return_cluster(self):
        self.cluster_obj.labels = dict(foo=41)
        self.cluster_obj.cluster_template.labels = dict(foo=42)

        result = self.driver._label(self.cluster_obj, "foo", "bar")

        self.assertEqual("41", result)

    def test_sanitised_name_no_suffix(self):
        self.assertEqual(
            "123-456fab", self.driver._sanitised_name("123-456Fab")
        )

    def test_sanitised_name_with_suffix(self):
        self.assertEqual(
            "123-456-fab-1-asdf",
            self.driver._sanitised_name("123-456_Fab!!_1!!", "asdf"),
        )
        self.assertEqual(
            "123-456-fab-1-asdf",
            self.driver._sanitised_name("123-456_Fab-1", "asdf"),
        )

    def test_get_kube_version_raises(self):
        mock_image = mock.Mock()
        mock_image.get.return_value = None
        mock_image.id = "myid"

        e = self.assertRaises(
            exception.KubeVersionPropertyNotFound,
            self.driver._get_kube_version,
            mock_image,
        )

        self.assertEqual(
            "Image myid does not have a kube_version property.", str(e)
        )
        mock_image.get.assert_called_once_with("kube_version")

    def test_get_kube_version_works(self):
        mock_image = mock.Mock()
        mock_image.get.return_value = "v1.27.9"

        result = self.driver._get_kube_version(mock_image)

        self.assertEqual("1.27.9", result)
        mock_image.get.assert_called_once_with("kube_version")

    @mock.patch("magnum.common.clients.OpenStackClients")
    @mock.patch("magnum.api.utils.get_openstack_resource")
    def test_get_image_details(self, mock_get, mock_osc):
        mock_image = mock.Mock()
        mock_image.get.return_value = "v1.27.9"
        mock_image.id = "myid"
        mock_get.return_value = mock_image

        id, version = self.driver._get_image_details(
            self.context, "myimagename"
        )

        self.assertEqual("1.27.9", version)
        self.assertEqual("myid", id)
        mock_image.get.assert_called_once_with("kube_version")
        mock_get.assert_called_once_with(mock.ANY, "myimagename", "images")

    def test_get_chart_release_name_lenght(self):
        self.cluster_obj.stack_id = "foo"

        result = self.driver._get_chart_release_name(self.cluster_obj)

        self.assertEqual("foo", result)

    def test_generate_release_name_skip(self):
        self.cluster_obj.stack_id = "foo"
        self.driver._generate_release_name(self.cluster_obj)
        self.assertEqual("foo", self.cluster_obj.stack_id)

    def test_generate_release_name_generates(self):
        self.cluster_obj.stack_id = None
        self.cluster_obj.name = "a" * 77

        self.driver._generate_release_name(self.cluster_obj)
        first = self.cluster_obj.stack_id

        self.assertEqual(43, len(first))
        self.assertTrue(self.cluster_obj.name[:30] in first)

        self.cluster_obj.stack_id = None
        self.driver._generate_release_name(self.cluster_obj)
        second = self.cluster_obj.stack_id

        self.assertNotEqual(first, second)
        self.assertEqual(43, len(second))
        self.assertTrue(self.cluster_obj.name[:30] in second)

    def test_get_monitoring_enabled_from_template(self):
        self.cluster_obj.cluster_template.labels["monitoring_enabled"] = "true"

        result = self.driver._get_monitoring_enabled(self.cluster_obj)

        self.assertTrue(result)

    def test_get_kube_dash_enabled_from_template(self):
        self.cluster_obj.cluster_template.labels[
            "kube_dashboard_enabled"
        ] = "false"

        result = self.driver._get_kube_dash_enabled(self.cluster_obj)

        self.assertFalse(result)

    def test_get_chart_version_from_config(self):
        version = self.driver._get_chart_version(self.cluster_obj)

        self.assertEqual(CONF.capi_driver.helm_chart_version, version)

    def test_get_chart_version_from_template(self):
        self.cluster_obj.cluster_template.labels[
            "capi_helm_chart_version"
        ] = "1.42.0"

        version = self.driver._get_chart_version(self.cluster_obj)

        self.assertEqual("1.42.0", version)

    @mock.patch.object(driver.Driver, "_ensure_certificate_secrets")
    @mock.patch.object(driver.Driver, "_create_appcred_secret")
    @mock.patch.object(kubernetes.Client, "load")
    @mock.patch.object(driver.Driver, "_get_image_details")
    @mock.patch.object(helm.Client, "install_or_upgrade")
    def test_create_cluster(
        self,
        mock_install,
        mock_image,
        mock_load,
        mock_appcred,
        mock_certs,
    ):
        mock_image.return_value = ("imageid1", "1.27.4")
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_load.return_value = mock_client
        self.cluster_obj.keypair = "kp1"

        self.driver.create_cluster(self.context, self.cluster_obj, 10)

        app_cred_name = "cluster-example-a-111111111111-cloud-credentials"
        mock_install.assert_called_once_with(
            "cluster-example-a-111111111111",
            "openstack-cluster",
            {
                "kubernetesVersion": "1.27.4",
                "machineImageId": "imageid1",
                "cloudCredentialsSecretName": app_cred_name,
                "clusterNetworking": {
                    "internalNetwork": {"nodeCidr": "10.0.0.0/24"},
                    "dnsNameservers": ["8.8.1.1"],
                },
                "apiServer": {
                    "enableLoadBalancer": True,
                    "loadBalancerProvider": "amphora",
                },
                "controlPlane": {
                    "machineFlavor": "flavor_small",
                    "machineCount": 3,
                },
                "addons": {
                    "monitoring": {"enabled": False},
                    "kubernetesDashboard": {"enabled": True},
                    "ingress": {"enabled": False},
                },
                "nodeGroups": [
                    {
                        "name": "test-worker",
                        "machineFlavor": "flavor_medium",
                        "machineCount": 3,
                    }
                ],
                "machineSSHKeyName": "kp1",
            },
            repo=CONF.capi_driver.helm_chart_repo,
            version=CONF.capi_driver.helm_chart_version,
            namespace="magnum-fakeproject",
        )
        mock_client.ensure_namespace.assert_called_once_with(
            "magnum-fakeproject"
        )
        mock_appcred.assert_called_once_with(self.context, self.cluster_obj)
        mock_certs.assert_called_once_with(self.context, self.cluster_obj)

    @mock.patch.object(driver.Driver, "_ensure_certificate_secrets")
    @mock.patch.object(driver.Driver, "_create_appcred_secret")
    @mock.patch.object(kubernetes.Client, "load")
    @mock.patch.object(driver.Driver, "_get_image_details")
    @mock.patch.object(helm.Client, "install_or_upgrade")
    def test_create_cluster_no_dns(
        self,
        mock_install,
        mock_image,
        mock_load,
        mock_appcred,
        mock_certs,
    ):
        mock_image.return_value = ("imageid1", "1.27.4")
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_load.return_value = mock_client
        self.cluster_obj.cluster_template.dns_nameserver = ""
        self.cluster_obj.keypair = "kp1"

        self.driver.create_cluster(self.context, self.cluster_obj, 10)

        app_cred_name = "cluster-example-a-111111111111-cloud-credentials"
        mock_install.assert_called_once_with(
            "cluster-example-a-111111111111",
            "openstack-cluster",
            {
                "kubernetesVersion": "1.27.4",
                "machineImageId": "imageid1",
                "cloudCredentialsSecretName": app_cred_name,
                "clusterNetworking": {
                    "internalNetwork": {"nodeCidr": "10.0.0.0/24"},
                },
                "apiServer": {
                    "enableLoadBalancer": True,
                    "loadBalancerProvider": "amphora",
                },
                "controlPlane": {
                    "machineFlavor": "flavor_small",
                    "machineCount": 3,
                },
                "addons": {
                    "monitoring": {"enabled": False},
                    "kubernetesDashboard": {"enabled": True},
                    "ingress": {"enabled": False},
                },
                "nodeGroups": [
                    {
                        "name": "test-worker",
                        "machineFlavor": "flavor_medium",
                        "machineCount": 3,
                    }
                ],
                "machineSSHKeyName": "kp1",
            },
            repo=CONF.capi_driver.helm_chart_repo,
            version=CONF.capi_driver.helm_chart_version,
            namespace="magnum-fakeproject",
        )
        mock_client.ensure_namespace.assert_called_once_with(
            "magnum-fakeproject"
        )
        mock_appcred.assert_called_once_with(self.context, self.cluster_obj)
        mock_certs.assert_called_once_with(self.context, self.cluster_obj)

    @mock.patch.object(driver.Driver, "_ensure_certificate_secrets")
    @mock.patch.object(driver.Driver, "_create_appcred_secret")
    @mock.patch.object(kubernetes.Client, "load")
    @mock.patch.object(driver.Driver, "_get_image_details")
    @mock.patch.object(helm.Client, "install_or_upgrade")
    def test_create_cluster_no_keypair(
        self,
        mock_install,
        mock_image,
        mock_load,
        mock_appcred,
        mock_certs,
    ):
        mock_image.return_value = ("imageid1", "1.27.4")
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_load.return_value = mock_client
        self.cluster_obj.keypair = ""

        self.driver.create_cluster(self.context, self.cluster_obj, 10)

        app_cred_name = "cluster-example-a-111111111111-cloud-credentials"
        mock_install.assert_called_once_with(
            "cluster-example-a-111111111111",
            "openstack-cluster",
            {
                "kubernetesVersion": "1.27.4",
                "machineImageId": "imageid1",
                "cloudCredentialsSecretName": app_cred_name,
                "clusterNetworking": {
                    "internalNetwork": {"nodeCidr": "10.0.0.0/24"},
                    "dnsNameservers": ["8.8.1.1"],
                },
                "apiServer": {
                    "enableLoadBalancer": True,
                    "loadBalancerProvider": "amphora",
                },
                "controlPlane": {
                    "machineFlavor": "flavor_small",
                    "machineCount": 3,
                },
                "addons": {
                    "monitoring": {"enabled": False},
                    "kubernetesDashboard": {"enabled": True},
                    "ingress": {"enabled": False},
                },
                "nodeGroups": [
                    {
                        "name": "test-worker",
                        "machineFlavor": "flavor_medium",
                        "machineCount": 3,
                    }
                ],
            },
            repo=CONF.capi_driver.helm_chart_repo,
            version=CONF.capi_driver.helm_chart_version,
            namespace="magnum-fakeproject",
        )
        mock_client.ensure_namespace.assert_called_once_with(
            "magnum-fakeproject"
        )
        mock_appcred.assert_called_once_with(self.context, self.cluster_obj)
        mock_certs.assert_called_once_with(self.context, self.cluster_obj)

    @mock.patch.object(app_creds, "get_app_cred_yaml")
    @mock.patch.object(app_creds, "get_openstack_ca_certificate")
    @mock.patch.object(kubernetes.Client, "load")
    def test_create_appcred_secret(self, mock_load, mock_cert, mock_yaml):
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_load.return_value = mock_client
        mock_cert.return_value = "ca"
        mock_yaml.return_value = "appcred"

        self.driver._create_appcred_secret(self.context, self.cluster_obj)

        uuid = self.cluster_obj.uuid
        mock_client.apply_secret.assert_called_once_with(
            "cluster-example-a-111111111111-cloud-credentials",
            {
                "metadata": {
                    "labels": {
                        "magnum.openstack.org/project-id": "fake_project",
                        "magnum.openstack.org/user-id": "fake_user",
                        "magnum.openstack.org/cluster-uuid": uuid,
                    }
                },
                "stringData": {"cacert": "ca", "clouds.yaml": "appcred"},
            },
            "magnum-fakeproject",
        )

    @mock.patch.object(cert_manager, "get_cluster_magnum_cert")
    @mock.patch.object(cert_manager, "get_cluster_ca_certificate")
    @mock.patch.object(driver.Driver, "_decode_key")
    @mock.patch.object(driver.Driver, "_decode_cert")
    @mock.patch.object(driver.Driver, "_k8s_resource_labels")
    @mock.patch.object(kubernetes.Client, "load")
    def test_ensure_certificate_secrets(
        self, mock_load, mock_labels, mock_cert, mock_key, mock_ca, mock_mag
    ):
        mock_client = mock.MagicMock(spec=kubernetes.Client)
        mock_load.return_value = mock_client
        mock_labels.return_value = dict(foo="bar")
        # TODO(johngarbutt): use side effects here?
        mock_cert.return_value = "cert1"
        mock_key.return_value = "key1"
        mock_ca.return_value = "cert_mgr_ca"
        mock_mag.return_value = "cert_mag"

        self.driver._ensure_certificate_secrets(self.context, self.cluster_obj)

        mock_client.apply_secret.assert_has_calls(
            [
                mock.call(
                    "cluster-example-a-111111111111-ca",
                    {
                        "metadata": {"labels": {"foo": "bar"}},
                        "type": "cluster.x-k8s.io/secret",
                        "stringData": {"tls.crt": "cert1", "tls.key": "key1"},
                    },
                    "magnum-fakeproject",
                ),
                mock.call(
                    "cluster-example-a-111111111111-etcd",
                    {
                        "metadata": {"labels": {"foo": "bar"}},
                        "type": "cluster.x-k8s.io/secret",
                        "stringData": {"tls.crt": "cert1", "tls.key": "key1"},
                    },
                    "magnum-fakeproject",
                ),
                mock.call(
                    "cluster-example-a-111111111111-proxy",
                    {
                        "metadata": {"labels": {"foo": "bar"}},
                        "type": "cluster.x-k8s.io/secret",
                        "stringData": {"tls.crt": "cert1", "tls.key": "key1"},
                    },
                    "magnum-fakeproject",
                ),
                mock.call(
                    "cluster-example-a-111111111111-sa",
                    {
                        "metadata": {"labels": {"foo": "bar"}},
                        "type": "cluster.x-k8s.io/secret",
                        "stringData": {"tls.crt": "cert1", "tls.key": "key1"},
                    },
                    "magnum-fakeproject",
                ),
            ]
        )
        # TODO(johngarbutt): assert more calls for the other mocks here

    def test_decode_cert(self):
        mock_cert = mock.MagicMock()
        mock_cert.get_certificate.return_value = "cert"

        result = self.driver._decode_cert(mock_cert)

        self.assertEqual("cert", result)

    @mock.patch.object(x509, "decrypt_key")
    def test_decode_key(self, mock_decrypt):
        mock_cert = mock.MagicMock()
        mock_cert.get_private_key.return_value = "private"
        mock_cert.get_private_key_passphrase.return_value = "pass"
        mock_decrypt.return_value = "foo"

        result = self.driver._decode_key(mock_cert)

        self.assertEqual("foo", result)
        mock_decrypt.assert_called_once_with("private", "pass")

    @mock.patch.object(helm.Client, "uninstall_release")
    def test_delete_cluster(self, mock_uninstall):
        self.driver.delete_cluster(self.context, self.cluster_obj)

        mock_uninstall.assert_called_once_with(
            "cluster-example-a-111111111111", namespace="magnum-fakeproject"
        )

    def test_update_cluster(self):
        self.assertRaises(
            NotImplementedError,
            self.driver.update_cluster,
            self.context,
            self.cluster_obj,
        )

    def test_resize_cluster(self):
        self.assertRaises(
            NotImplementedError,
            self.driver.resize_cluster,
            self.context,
            self.cluster_obj,
            None,
            4,
            None,
        )

    def test_upgrade_cluster(self):
        self.assertRaises(
            NotImplementedError,
            self.driver.upgrade_cluster,
            self.context,
            self.cluster_obj,
            self.cluster_obj.cluster_template,
            1,
            None,
        )

    def test_create_nodegroup(self):
        self.assertRaises(
            NotImplementedError,
            self.driver.create_nodegroup,
            self.context,
            self.cluster_obj,
            objects.NodeGroup(),
        )

    def test_update_nodegroup(self):
        self.assertRaises(
            NotImplementedError,
            self.driver.update_nodegroup,
            self.context,
            self.cluster_obj,
            objects.NodeGroup(),
        )

    def test_delete_nodegroup(self):
        self.assertRaises(
            NotImplementedError,
            self.driver.delete_nodegroup,
            self.context,
            self.cluster_obj,
            objects.NodeGroup(),
        )

    def test_create_federation(self):
        self.assertRaises(
            NotImplementedError,
            self.driver.create_federation,
            self.context,
            None,
        )

    def test_update_federation(self):
        self.assertRaises(
            NotImplementedError,
            self.driver.update_federation,
            self.context,
            None,
        )

    def test_delete_federation(self):
        self.assertRaises(
            NotImplementedError,
            self.driver.delete_federation,
            self.context,
            None,
        )
