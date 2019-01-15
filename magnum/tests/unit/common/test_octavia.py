# Copyright 2018 Catalyst Cloud Ltd.
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

import mock

from magnum.common import exception
from magnum.common import octavia
from magnum import objects
from magnum.tests import base
from magnum.tests.unit.db import utils


class OctaviaTest(base.TestCase):
    def setUp(self):
        super(OctaviaTest, self).setUp()

        cluster_dict = utils.get_test_cluster(node_count=1)
        self.cluster = objects.Cluster(self.context, **cluster_dict)

    @mock.patch("magnum.common.neutron.delete_floatingip")
    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_delete_loadbalancers(self, mock_clients, mock_delete_fip):
        mock_lbs = {
            "loadbalancers": [
                {
                    "id": "fake_id_1",
                    "description": "Kubernetes external service "
                                   "ad3080723f1c211e88adbfa163ee1203 from "
                                   "cluster %s" % self.cluster.uuid,
                    "name": "fake_name_1",
                    "provisioning_status": "ACTIVE",
                    "vip_port_id": "b4ca07d1-a31e-43e2-891a-7d14f419f342"
                },
                {
                    "id": "fake_id_2",
                    "description": "Kubernetes external service "
                                   "a9f9ba08cf28811e89547fa163ea824f from "
                                   "cluster %s" % self.cluster.uuid,
                    "name": "fake_name_2",
                    "provisioning_status": "ERROR",
                    "vip_port_id": "c17c1a6e-1868-11e9-84cd-00224d6b7bc1"
                },
            ]
        }
        mock_octavie_client = mock.MagicMock()
        mock_octavie_client.load_balancer_list.side_effect = [
            mock_lbs, {"loadbalancers": []}
        ]
        osc = mock.MagicMock()
        mock_clients.return_value = osc
        osc.octavia.return_value = mock_octavie_client

        octavia.delete_loadbalancers(self.context, self.cluster)

        calls = [
            mock.call("fake_id_1", cascade=True),
            mock.call("fake_id_2", cascade=True)
        ]
        mock_octavie_client.load_balancer_delete.assert_has_calls(calls)

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_delete_loadbalancers_no_candidate(self, mock_clients):
        mock_lbs = {
            "loadbalancers": []
        }
        mock_octavie_client = mock.MagicMock()
        mock_octavie_client.load_balancer_list.return_value = mock_lbs
        osc = mock.MagicMock()
        mock_clients.return_value = osc
        osc.octavia.return_value = mock_octavie_client

        octavia.delete_loadbalancers(self.context, self.cluster)

        self.assertFalse(mock_octavie_client.load_balancer_delete.called)

    @mock.patch("magnum.common.neutron.delete_floatingip")
    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_delete_loadbalancers_with_invalid_lb(self, mock_clients,
                                                  mock_delete_fip):
        osc = mock.MagicMock()
        mock_clients.return_value = osc
        mock_octavie_client = mock.MagicMock()
        osc.octavia.return_value = mock_octavie_client

        mock_lbs = {
            "loadbalancers": [
                {
                    "id": "fake_id_1",
                    "description": "Kubernetes external service "
                                   "ad3080723f1c211e88adbfa163ee1203 from "
                                   "cluster %s" % self.cluster.uuid,
                    "name": "fake_name_1",
                    "provisioning_status": "ACTIVE",
                    "vip_port_id": "c17c1a6e-1868-11e9-84cd-00224d6b7bc1"
                },
                {
                    "id": "fake_id_2",
                    "description": "Kubernetes external service "
                                   "a9f9ba08cf28811e89547fa163ea824f from "
                                   "cluster %s" % self.cluster.uuid,
                    "name": "fake_name_2",
                    "provisioning_status": "PENDING_UPDATE",
                    "vip_port_id": "b4ca07d1-a31e-43e2-891a-7d14f419f342"
                },
            ]
        }
        mock_octavie_client.load_balancer_list.return_value = mock_lbs

        self.assertRaises(
            exception.PreDeletionFailed,
            octavia.delete_loadbalancers,
            self.context,
            self.cluster
        )
        mock_octavie_client.load_balancer_delete.assert_called_once_with(
            "fake_id_1", cascade=True)

    @mock.patch("magnum.common.neutron.delete_floatingip")
    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_delete_loadbalancers_timeout(self, mock_clients, mock_delete_fip):
        osc = mock.MagicMock()
        mock_clients.return_value = osc
        mock_octavie_client = mock.MagicMock()
        osc.octavia.return_value = mock_octavie_client

        mock_lbs = {
            "loadbalancers": [
                {
                    "id": "fake_id_1",
                    "description": "Kubernetes external service "
                                   "ad3080723f1c211e88adbfa163ee1203 from "
                                   "cluster %s" % self.cluster.uuid,
                    "name": "fake_name_1",
                    "provisioning_status": "ACTIVE",
                    "vip_port_id": "b4ca07d1-a31e-43e2-891a-7d14f419f342"
                },
                {
                    "id": "fake_id_2",
                    "description": "Kubernetes external service "
                                   "a9f9ba08cf28811e89547fa163ea824f from "
                                   "cluster %s" % self.cluster.uuid,
                    "name": "fake_name_2",
                    "provisioning_status": "ACTIVE",
                    "vip_port_id": "c17c1a6e-1868-11e9-84cd-00224d6b7bc1"
                },
            ]
        }
        mock_octavie_client.load_balancer_list.return_value = mock_lbs

        self.assertRaises(
            exception.PreDeletionFailed,
            octavia.delete_loadbalancers,
            self.context,
            self.cluster
        )
