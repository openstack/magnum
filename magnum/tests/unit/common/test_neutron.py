# Copyright 2019 Catalyst Cloud Ltd.
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
from magnum.common import neutron
from magnum import objects
from magnum.tests import base
from magnum.tests.unit.db import utils


class NeutronTest(base.TestCase):
    def setUp(self):
        super(NeutronTest, self).setUp()

        cluster_dict = utils.get_test_cluster(node_count=1)
        nodegroups_dict = utils.get_nodegroups_for_cluster(node_count=1)
        self.cluster = objects.Cluster(self.context, **cluster_dict)
        self.nodegroups = [
            objects.NodeGroup(self.context, **nodegroups_dict['master']),
            objects.NodeGroup(self.context, **nodegroups_dict['worker'])
        ]

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_delete_floatingip(self, mock_clients):
        mock_nclient = mock.MagicMock()
        fake_port_id = "b4518944-c2cf-4c69-a1e3-774041fd5d14"
        fake_fip_id = "0f8c6849-af85-424c-aa8e-745ade9a46a7"
        mock_fip = mock.MagicMock()
        mock_fip.description = ('Floating IP for Kubernetes external '
                                'service ad3080723f1c211e88adbfa163ee1203 '
                                'from cluster %s' % self.cluster.uuid)
        mock_fip.id = fake_fip_id
        mock_nclient.ips.return_value = [mock_fip]

        osc = mock.MagicMock()
        mock_clients.return_value = osc
        osc.neutron.return_value = mock_nclient

        neutron.delete_floatingip(self.context, fake_port_id, self.cluster)

        mock_nclient.ips.assert_called_once_with(port_id=fake_port_id)
        mock_nclient.delete_ip.assert_called_once_with(fake_fip_id)

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_delete_floatingip_empty(self, mock_clients):
        mock_nclient = mock.MagicMock()
        fake_port_id = "b4518944-c2cf-4c69-a1e3-774041fd5d14"
        mock_nclient.ips.return_value = []

        osc = mock.MagicMock()
        mock_clients.return_value = osc
        osc.neutron.return_value = mock_nclient

        neutron.delete_floatingip(self.context, fake_port_id, self.cluster)

        self.assertFalse(mock_nclient.delete_ip.called)

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_delete_floatingip_exception(self, mock_clients):
        mock_nclient = mock.MagicMock()
        fake_port_id = "b4518944-c2cf-4c69-a1e3-774041fd5d14"
        fake_fip_id = "0f8c6849-af85-424c-aa8e-745ade9a46a7"
        mock_fip = mock.MagicMock()
        mock_fip.description = ('Floating IP for Kubernetes external '
                                'service ad3080723f1c211e88adbfa163ee1203 '
                                'from cluster %s' % self.cluster.uuid)
        mock_fip.id = fake_fip_id
        mock_nclient.ips.return_value = [mock_fip]
        mock_nclient.delete_ip.side_effect = Exception

        osc = mock.MagicMock()
        mock_clients.return_value = osc
        osc.neutron.return_value = mock_nclient

        self.assertRaises(
            exception.PreDeletionFailed,
            neutron.delete_floatingip,
            self.context,
            fake_port_id,
            self.cluster
        )

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_get_external_network_id(self, mock_clients):
        fake_name = "fake_network"
        fake_id = "24fe5da0-1ac0-11e9-84cd-00224d6b7bc1"
        mock_nclient = mock.MagicMock()
        mock_net = mock.MagicMock()
        mock_net.name = fake_name
        mock_net.id = fake_id
        mock_nclient.networks.return_value = [mock_net]

        osc = mock.MagicMock()
        mock_clients.return_value = osc
        osc.neutron.return_value = mock_nclient

        network_id = neutron.get_external_network_id(self.context, fake_name)

        self.assertEqual(fake_id, network_id)

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_get_external_network_id_notfound(self, mock_clients):
        fake_name = "fake_network"
        fake_id = "24fe5da0-1ac0-11e9-84cd-00224d6b7bc1"
        mock_nclient = mock.MagicMock()
        mock_net = mock.MagicMock()
        mock_net.name = fake_name
        mock_net.id = fake_id
        mock_nclient.networks.return_value = [mock_net]

        osc = mock.MagicMock()
        mock_clients.return_value = osc
        osc.neutron.return_value = mock_nclient

        self.assertRaises(
            exception.ExternalNetworkNotFound,
            neutron.get_external_network_id,
            self.context,
            "another_network"
        )

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_get_external_network_id_conflict(self, mock_clients):
        fake_name = "fake_network"
        fake_id_1 = "24fe5da0-1ac0-11e9-84cd-00224d6b7bc1"
        fake_id_2 = "93781f82-1ac0-11e9-84cd-00224d6b7bc1"
        mock_nclient = mock.MagicMock()
        mock_net1 = mock.MagicMock()
        mock_net1.name = fake_name
        mock_net1.id = fake_id_1
        mock_net2 = mock.MagicMock()
        mock_net2.name = fake_name
        mock_net2.id = fake_id_2
        mock_nclient.networks.return_value = [mock_net1, mock_net2]

        osc = mock.MagicMock()
        mock_clients.return_value = osc
        osc.neutron.return_value = mock_nclient

        self.assertRaises(
            exception.Conflict,
            neutron.get_external_network_id,
            self.context,
            fake_name
        )

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_get_fixed_network_name(self, mock_clients):
        fake_name = "fake_network"
        fake_id = "24fe5da0-1ac0-11e9-84cd-00224d6b7bc1"
        mock_nclient = mock.MagicMock()
        mock_net = mock.MagicMock()
        mock_net.name = fake_name
        mock_net.id = fake_id
        mock_nclient.networks.return_value = [mock_net]

        osc = mock.MagicMock()
        mock_clients.return_value = osc
        osc.neutron.return_value = mock_nclient

        network_name = neutron.get_fixed_network_name(self.context, fake_id)

        self.assertEqual(fake_name, network_name)

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_get_fixed_network_name_notfound(self, mock_clients):
        fake_name = "fake_network"
        fake_id = "24fe5da0-1ac0-11e9-84cd-00224d6b7bc1"
        another_fake_id = "34fe5da0-1ac0-11e9-84cd-00224d6b7bc1"
        mock_nclient = mock.MagicMock()
        mock_net = mock.MagicMock()
        mock_net.name = fake_name
        mock_net.id = fake_id
        mock_nclient.networks.return_value = [mock_net]

        osc = mock.MagicMock()
        mock_clients.return_value = osc
        osc.neutron.return_value = mock_nclient

        self.assertRaises(
            exception.FixedNetworkNotFound,
            neutron.get_fixed_network_name,
            self.context,
            another_fake_id
        )

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_get_fixed_subnet_id(self, mock_clients):
        fake_name = "fake_subnet"
        fake_id = "35ee5da0-1ac0-11e9-84cd-00224d6b7bc1"
        mock_nclient = mock.MagicMock()
        mock_subnet = mock.MagicMock()
        mock_subnet.name = fake_name
        mock_subnet.id = fake_id
        mock_nclient.subnets.return_value = [mock_subnet]

        osc = mock.MagicMock()
        mock_clients.return_value = osc
        osc.neutron.return_value = mock_nclient

        subnet_id = neutron.get_fixed_subnet_id(self.context, fake_name)

        self.assertEqual(fake_id, subnet_id)

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_get_fixed_subnet_id_notfound(self, mock_clients):
        fake_name = "fake_subnet"
        fake_id = "35ee5da0-1ac0-11e9-84cd-00224d6b7bc1"
        mock_nclient = mock.MagicMock()
        mock_subnet = mock.MagicMock()
        mock_subnet.name = fake_name
        mock_subnet.id = fake_id
        mock_nclient.subnets.return_value = [mock_subnet]

        osc = mock.MagicMock()
        mock_clients.return_value = osc
        osc.neutron.return_value = mock_nclient

        self.assertRaises(
            exception.FixedSubnetNotFound,
            neutron.get_fixed_subnet_id,
            self.context,
            "another_subnet"
        )

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_get_fixed_subnet_id_conflict(self, mock_clients):
        fake_name = "fake_subnet"
        fake_id_1 = "35ee5da0-1ac0-11e9-84cd-00224d6b7bc1"
        fake_id_2 = "93781f82-1ac0-11e9-84cd-00224d6b7bc1"
        mock_nclient = mock.MagicMock()
        mock_subnet1 = mock.MagicMock()
        mock_subnet1.name = fake_name
        mock_subnet1.id = fake_id_1
        mock_subnet2 = mock.MagicMock()
        mock_subnet2.name = fake_name
        mock_subnet2.id = fake_id_2
        mock_nclient.subnets.return_value = [mock_subnet1, mock_subnet2]

        osc = mock.MagicMock()
        mock_clients.return_value = osc
        osc.neutron.return_value = mock_nclient

        self.assertRaises(
            exception.Conflict,
            neutron.get_fixed_subnet_id,
            self.context,
            fake_name
        )
