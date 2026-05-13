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

from unittest import mock

from magnum.common import exception
from magnum.common import octavia
from magnum import objects
from magnum.tests import base
from magnum.tests.unit.db import utils


def make_lb(id, description, name, provisioning_status, vip_port_id=None):
    lb = mock.Mock()
    lb.id = id
    lb.description = description
    lb.name = name
    lb.provisioning_status = provisioning_status
    lb.vip_port_id = vip_port_id
    return lb


class OctaviaTest(base.TestCase):
    def setUp(self):
        super(OctaviaTest, self).setUp()

        cluster_dict = utils.get_test_cluster(node_count=1)
        nodegroups_dict = utils.get_nodegroups_for_cluster(node_count=1)
        self.cluster = objects.Cluster(self.context, **cluster_dict)
        self.nodegroups = [
            objects.NodeGroup(self.context, **nodegroups_dict['master']),
            objects.NodeGroup(self.context, **nodegroups_dict['worker'])
        ]

    @mock.patch("magnum.common.neutron.delete_floatingip")
    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_delete_loadbalancers(self, mock_clients, mock_delete_fip):
        lb1 = make_lb(
            id="fake_id_1",
            description="Kubernetes external service "
                        "ad3080723f1c211e88adbfa163ee1203 from "
                        "cluster %s" % self.cluster.uuid,
            name="fake_name_1",
            provisioning_status="ACTIVE",
            vip_port_id="b4ca07d1-a31e-43e2-891a-7d14f419f342"
        )
        lb2 = make_lb(
            id="fake_id_2",
            description="Kubernetes Ingress test-octavia-ingress "
                        "in namespace default from cluster %s, "
                        "version: 32207" % self.cluster.uuid,
            name="fake_name_2",
            provisioning_status="ERROR",
            vip_port_id="c17c1a6e-1868-11e9-84cd-00224d6b7bc1"
        )
        mock_octavia_client = mock.MagicMock()
        mock_octavia_client.load_balancers.side_effect = [
            [lb1, lb2],   # first call in delete_loadbalancers (services)
            []            # second call in wait_for_lb_deleted
        ]

        osc = mock.MagicMock()
        mock_clients.return_value = osc
        osc.octavia.return_value = mock_octavia_client

        octavia.delete_loadbalancers(self.context, self.cluster)

        calls = [
            mock.call("fake_id_1", cascade=True),
            mock.call("fake_id_2", cascade=True),
        ]
        mock_octavia_client.delete_load_balancer.assert_has_calls(calls)

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_delete_loadbalancers_no_candidate(self, mock_clients):
        mock_octavia_client = mock.MagicMock()
        mock_octavia_client.load_balancers.return_value = []

        osc = mock.MagicMock()
        mock_clients.return_value = osc
        osc.octavia.return_value = mock_octavia_client

        octavia.delete_loadbalancers(self.context, self.cluster)

        self.assertFalse(mock_octavia_client.delete_load_balancer.called)

    @mock.patch("magnum.common.neutron.delete_floatingip")
    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_delete_loadbalancers_timeout(self, mock_clients, mock_delete_fip):
        # don't wait the full 60 seconds for a unit test
        self.config(pre_delete_lb_timeout=1, group="cluster")
        osc = mock.MagicMock()
        mock_clients.return_value = osc
        mock_octavia_client = mock.MagicMock()
        osc.octavia.return_value = mock_octavia_client

        lb1 = make_lb(
            id="fake_id_1",
            description="Kubernetes external service "
                        "ad3080723f1c211e88adbfa163ee1203 from "
                        "cluster %s" % self.cluster.uuid,
            name="fake_name_1",
            provisioning_status="ACTIVE",
            vip_port_id="b4ca07d1-a31e-43e2-891a-7d14f419f342"
        )
        lb2 = make_lb(
            id="fake_id_2",
            description="Kubernetes external service "
                        "a9f9ba08cf28811e89547fa163ea824f from "
                        "cluster %s" % self.cluster.uuid,
            name="fake_name_2",
            provisioning_status="ACTIVE",
            vip_port_id="c17c1a6e-1868-11e9-84cd-00224d6b7bc1"
        )
        mock_octavia_client.load_balancers.return_value = [lb1, lb2]

        self.assertRaises(
            exception.PreDeletionFailed,
            octavia.delete_loadbalancers,
            self.context,
            self.cluster
        )
