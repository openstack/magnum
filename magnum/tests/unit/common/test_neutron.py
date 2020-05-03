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
        mock_nclient.list_floatingips.return_value = {
            'floatingips': [
                {
                    'router_id': '6ed4f7ef-b8c3-4711-93cf-d53cf0e8bdf5',
                    'status': 'ACTIVE',
                    'description': 'Floating IP for Kubernetes external '
                                   'service ad3080723f1c211e88adbfa163ee1203 '
                                   'from cluster %s' % self.cluster.uuid,
                    'tags': [],
                    'tenant_id': 'cd08a539b7c845ddb92c5d08752101d1',
                    'floating_network_id': 'd0b9a8c5-33e5-4ce1-869a-1e2ec7c2f'
                                           '74b',
                    'port_details': {
                        'status': 'ACTIVE',
                        'name': 'test-k8s-master',
                        'admin_state_up': True,
                        'network_id': '7b9110b5-90a2-40bc-b892-07d641387760 ',
                        'device_owner': 'compute:nova',
                        'mac_address': 'fa:16:3e:6f:ad:6c',
                        'device_id': 'a5c1689f-dd76-4164-8562-6990071701cd'
                    },
                    'fixed_ip_address': '10.0.0.4',
                    'floating_ip_address': '172.24.4.74',
                    'revision_number': 14,
                    'project_id': 'cd08a539b7c845ddb92c5d08752101d1',
                    'port_id': fake_port_id,
                    'id': fake_fip_id
                }
            ]
        }

        osc = mock.MagicMock()
        mock_clients.return_value = osc
        osc.neutron.return_value = mock_nclient

        neutron.delete_floatingip(self.context, fake_port_id, self.cluster)

        mock_nclient.delete_floatingip.assert_called_once_with(fake_fip_id)

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_delete_floatingip_empty(self, mock_clients):
        mock_nclient = mock.MagicMock()
        fake_port_id = "b4518944-c2cf-4c69-a1e3-774041fd5d14"
        mock_nclient.list_floatingips.return_value = {
            'floatingips': []
        }

        osc = mock.MagicMock()
        mock_clients.return_value = osc
        osc.neutron.return_value = mock_nclient

        neutron.delete_floatingip(self.context, fake_port_id, self.cluster)

        self.assertFalse(mock_nclient.delete_floatingip.called)

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_delete_floatingip_exception(self, mock_clients):
        mock_nclient = mock.MagicMock()
        fake_port_id = "b4518944-c2cf-4c69-a1e3-774041fd5d14"
        fake_fip_id = "0f8c6849-af85-424c-aa8e-745ade9a46a7"
        mock_nclient.list_floatingips.return_value = {
            'floatingips': [
                {
                    'router_id': '6ed4f7ef-b8c3-4711-93cf-d53cf0e8bdf5',
                    'status': 'ACTIVE',
                    'description': 'Floating IP for Kubernetes external '
                                   'service ad3080723f1c211e88adbfa163ee1203 '
                                   'from cluster %s' % self.cluster.uuid,
                    'tags': [],
                    'tenant_id': 'cd08a539b7c845ddb92c5d08752101d1',
                    'floating_network_id': 'd0b9a8c5-33e5-4ce1-869a-1e2ec7c2f'
                                           '74b',
                    'port_details': {
                        'status': 'ACTIVE',
                        'name': 'test-k8s-master',
                        'admin_state_up': True,
                        'network_id': '7b9110b5-90a2-40bc-b892-07d641387760 ',
                        'device_owner': 'compute:nova',
                        'mac_address': 'fa:16:3e:6f:ad:6c',
                        'device_id': 'a5c1689f-dd76-4164-8562-6990071701cd'
                    },
                    'fixed_ip_address': '10.0.0.4',
                    'floating_ip_address': '172.24.4.74',
                    'revision_number': 14,
                    'project_id': 'cd08a539b7c845ddb92c5d08752101d1',
                    'port_id': fake_port_id,
                    'id': fake_fip_id
                }
            ]
        }
        mock_nclient.delete_floatingip.side_effect = Exception

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
        mock_nclient.list_networks.return_value = {
            'networks': [
                {
                    'id': fake_id,
                    'name': fake_name,
                    'router:external': True
                }
            ]
        }

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
        mock_nclient.list_networks.return_value = {
            'networks': [
                {
                    'id': fake_id,
                    'name': fake_name,
                    'router:external': True
                }
            ]
        }

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
        mock_nclient.list_networks.return_value = {
            'networks': [
                {
                    'id': fake_id_1,
                    'name': fake_name,
                    'router:external': True
                },
                {
                    'id': fake_id_2,
                    'name': fake_name,
                    'router:external': True
                }
            ]
        }

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
        mock_nclient.list_networks.return_value = {
            'networks': [
                {
                    'id': fake_id,
                    'name': fake_name,
                    'router:external': False
                }
            ]
        }

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
        mock_nclient.list_networks.return_value = {
            'networks': [
                {
                    'id': fake_id,
                    'name': fake_name,
                    'router:external': False
                }
            ]
        }

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
        mock_nclient.list_subnets.return_value = {
            'subnets': [
                {
                    'id': fake_id,
                    'name': fake_name,
                }
            ]
        }

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
        mock_nclient.list_subnets.return_value = {
            'subnets': [
                {
                    'id': fake_id,
                    'name': fake_name,
                }
            ]
        }

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
        mock_nclient.list_subnets.return_value = {
            'subnets': [
                {
                    'id': fake_id_1,
                    'name': fake_name,
                },
                {
                    'id': fake_id_2,
                    'name': fake_name,
                }
            ]
        }

        osc = mock.MagicMock()
        mock_clients.return_value = osc
        osc.neutron.return_value = mock_nclient

        self.assertRaises(
            exception.Conflict,
            neutron.get_fixed_subnet_id,
            self.context,
            fake_name
        )
