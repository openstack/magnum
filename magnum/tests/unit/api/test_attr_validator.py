# Copyright 2015 EasyStack, Inc.
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


from novaclient import exceptions as nova_exc
from openstack import exceptions as sdk_exceptions
from unittest import mock

from magnum.api import attr_validator
from magnum.common import exception
from magnum.tests import base


class TestAttrValidator(base.BaseTestCase):

    def test_validate_flavor_with_vaild_flavor(self):
        mock_flavor = mock.MagicMock()
        mock_flavor.name = 'test_flavor'
        mock_flavor.id = 'test_flavor_id'
        mock_flavors = [mock_flavor]
        mock_nova = mock.MagicMock()
        mock_nova.flavors.list.return_value = mock_flavors
        mock_os_cli = mock.MagicMock()
        mock_os_cli.nova.return_value = mock_nova
        attr_validator.validate_flavor(mock_os_cli, 'test_flavor')
        self.assertTrue(mock_nova.flavors.list.called)

    def test_validate_flavor_with_none_flavor(self):
        mock_flavor = mock.MagicMock()
        mock_flavor.name = 'test_flavor'
        mock_flavor.id = 'test_flavor_id'
        mock_flavors = [mock_flavor]
        mock_nova = mock.MagicMock()
        mock_nova.flavors.list.return_value = mock_flavors
        mock_os_cli = mock.MagicMock()
        mock_os_cli.nova.return_value = mock_nova
        attr_validator.validate_flavor(mock_os_cli, None)
        self.assertEqual(False, mock_nova.flavors.list.called)

    def test_validate_flavor_with_invalid_flavor(self):
        mock_flavor = mock.MagicMock()
        mock_flavor.name = 'test_flavor_not_equal'
        mock_flavor.id = 'test_flavor_id_not_equal'
        mock_flavors = [mock_flavor]
        mock_nova = mock.MagicMock()
        mock_nova.flavors.list.return_value = mock_flavors
        mock_os_cli = mock.MagicMock()
        mock_os_cli.nova.return_value = mock_nova
        self.assertRaises(exception.FlavorNotFound,
                          attr_validator.validate_flavor,
                          mock_os_cli, 'test_flavor')

    def test_validate_external_network_with_valid_network(self):
        mock_net = mock.MagicMock()
        mock_net.name = 'test_ext_net'
        mock_net.id = 'test_ext_net_id'
        mock_neutron = mock.MagicMock()
        mock_neutron.networks.return_value = [mock_net]
        mock_os_cli = mock.MagicMock()
        mock_os_cli.neutron.return_value = mock_neutron
        attr_validator.validate_external_network(mock_os_cli, 'test_ext_net')
        mock_neutron.networks.assert_called_once_with(is_router_external=True)

    def test_validate_external_network_with_multiple_valid_network(self):
        mock_net1 = mock.MagicMock()
        mock_net1.name = 'test_ext_net'
        mock_net1.id = 'test_ext_net_id1'
        mock_net2 = mock.MagicMock()
        mock_net2.name = 'test_ext_net'
        mock_net2.id = 'test_ext_net_id2'
        mock_neutron = mock.MagicMock()
        mock_neutron.networks.return_value = [mock_net1, mock_net2]
        mock_os_cli = mock.MagicMock()
        mock_os_cli.neutron.return_value = mock_neutron
        self.assertRaises(exception.Conflict,
                          attr_validator.validate_external_network,
                          mock_os_cli, 'test_ext_net')

    def test_validate_external_network_with_invalid_network(self):
        mock_net = mock.MagicMock()
        mock_net.name = 'test_ext_net_not_equal'
        mock_net.id = 'test_ext_net_id_not_equal'
        mock_neutron = mock.MagicMock()
        mock_neutron.networks.return_value = [mock_net]
        mock_os_cli = mock.MagicMock()
        mock_os_cli.neutron.return_value = mock_neutron
        self.assertRaises(exception.ExternalNetworkNotFound,
                          attr_validator.validate_external_network,
                          mock_os_cli, 'test_ext_net')

    def test_validate_fixed_network_with_valid_network(self):
        mock_net = mock.MagicMock()
        mock_net.name = 'test_net'
        mock_net.id = 'test_net_id'
        mock_neutron = mock.MagicMock()
        mock_neutron.networks.return_value = [mock_net]
        mock_os_cli = mock.MagicMock()
        mock_os_cli.neutron.return_value = mock_neutron
        self.assertEqual('test_net_id',
                         attr_validator.validate_fixed_network(mock_os_cli,
                                                               'test_net'))
        mock_neutron.networks.assert_called_once_with()

    def test_validate_fixed_network_with_multiple_valid_network(self):
        mock_net1 = mock.MagicMock()
        mock_net1.name = 'test_net'
        mock_net1.id = 'test_net_id1'
        mock_net2 = mock.MagicMock()
        mock_net2.name = 'test_net'
        mock_net2.id = 'test_net_id2'
        mock_neutron = mock.MagicMock()
        mock_neutron.networks.return_value = [mock_net1, mock_net2]
        mock_os_cli = mock.MagicMock()
        mock_os_cli.neutron.return_value = mock_neutron
        self.assertRaises(exception.Conflict,
                          attr_validator.validate_fixed_network,
                          mock_os_cli, 'test_net')

    def test_validate_fixed_network_with_invalid_network(self):
        mock_net = mock.MagicMock()
        mock_net.name = 'test_net_not_equal'
        mock_net.id = 'test_net_id_not_equal'
        mock_neutron = mock.MagicMock()
        mock_neutron.networks.return_value = [mock_net]
        mock_os_cli = mock.MagicMock()
        mock_os_cli.neutron.return_value = mock_neutron
        self.assertRaises(exception.FixedNetworkNotFound,
                          attr_validator.validate_fixed_network,
                          mock_os_cli, 'test_net')

    def test_validate_fixed_subnet_with_valid_subnet(self):
        mock_subnet = mock.MagicMock()
        mock_subnet.name = 'test_subnet'
        mock_subnet.id = 'test_subnet_id'
        mock_neutron = mock.MagicMock()
        mock_neutron.subnets.return_value = [mock_subnet]
        mock_os_cli = mock.MagicMock()
        mock_os_cli.neutron.return_value = mock_neutron
        self.assertEqual('test_subnet_id',
                         attr_validator.validate_fixed_subnet(mock_os_cli,
                                                              'test_subnet'))
        mock_neutron.subnets.assert_called_with()

    def test_validate_fixed_subnet_with_invalid_subnet(self):
        mock_subnet = mock.MagicMock()
        mock_subnet.name = 'test_subnet'
        mock_subnet.id = 'test_subnet_id'
        mock_neutron = mock.MagicMock()
        mock_neutron.subnets.return_value = [mock_subnet]
        mock_os_cli = mock.MagicMock()
        mock_os_cli.neutron.return_value = mock_neutron
        self.assertRaises(exception.FixedSubnetNotFound,
                          attr_validator.validate_fixed_subnet,
                          mock_os_cli, 'test_subnet_not_found')

    def test_validate_fixed_subnet_with_multiple_valid_subnet(self):
        mock_subnet1 = mock.MagicMock()
        mock_subnet1.name = 'test_subnet'
        mock_subnet1.id = 'test_subnet_id'
        mock_subnet2 = mock.MagicMock()
        mock_subnet2.name = 'test_subnet'
        mock_subnet2.id = 'test_subnet_id2'
        mock_neutron = mock.MagicMock()
        mock_neutron.subnets.return_value = [mock_subnet1, mock_subnet2]
        mock_os_cli = mock.MagicMock()
        mock_os_cli.neutron.return_value = mock_neutron
        self.assertRaises(exception.Conflict,
                          attr_validator.validate_fixed_subnet,
                          mock_os_cli, 'test_subnet')

    def test_validate_keypair_with_no_keypair(self):
        mock_keypair = mock.MagicMock()
        mock_keypair.id = None
        mock_nova = mock.MagicMock()
        mock_nova.keypairs.get.return_value = mock_keypair
        mock_os_cli = mock.MagicMock()
        mock_os_cli.nova.return_value = mock_nova
        attr_validator.validate_keypair(mock_os_cli, None)

    def test_validate_keypair_with_valid_keypair(self):
        mock_keypair = mock.MagicMock()
        mock_keypair.id = 'test-keypair'
        mock_nova = mock.MagicMock()
        mock_nova.keypairs.get.return_value = mock_keypair
        mock_os_cli = mock.MagicMock()
        mock_os_cli.nova.return_value = mock_nova
        attr_validator.validate_keypair(mock_os_cli, 'test-keypair')

    def test_validate_keypair_with_invalid_keypair(self):
        mock_nova = mock.MagicMock()
        mock_nova.keypairs.get.side_effect = nova_exc.NotFound('test-keypair')
        mock_os_cli = mock.MagicMock()
        mock_os_cli.nova.return_value = mock_nova
        self.assertRaises(exception.KeyPairNotFound,
                          attr_validator.validate_keypair,
                          mock_os_cli, 'test_keypair')

    def test_validate_labels_main_no_label(self):
        fake_labels = {}
        attr_validator.validate_labels(fake_labels)

    def test_validate_image_with_valid_image_by_name(self):
        mock_image = mock.MagicMock()
        mock_image.os_distro = 'ubuntu'
        mock_os_cli = mock.MagicMock()
        mock_os_cli.glance.return_value.find_image.return_value = mock_image
        attr_validator.validate_image(mock_os_cli, 'ubuntu-24.04')
        mock_os_cli.glance.return_value.find_image.assert_called_once_with(
            'ubuntu-24.04', ignore_missing=False)

    def test_validate_image_with_forbidden_image(self):
        mock_os_cli = mock.MagicMock()
        mock_os_cli.glance.return_value.find_image.side_effect = (
            sdk_exceptions.ForbiddenException())
        self.assertRaises(exception.ImageNotAuthorized,
                          attr_validator.validate_image, mock_os_cli,
                          'ubuntu-24.04')

    def test_validate_image_with_valid_image_by_id(self):
        mock_image = mock.MagicMock()
        mock_image.os_distro = 'ubuntu'
        mock_os_cli = mock.MagicMock()
        mock_os_cli.glance.return_value.find_image.return_value = mock_image
        attr_validator.validate_image(mock_os_cli,
                                      'e33f0988-1730-405e-8401-30cbc8535302')
        mock_os_cli.glance.return_value.find_image.assert_called_once_with(
            'e33f0988-1730-405e-8401-30cbc8535302', ignore_missing=False)

    def test_validate_image_with_nonexist_image_by_name(self):
        mock_os_cli = mock.MagicMock()
        mock_os_cli.glance.return_value.find_image.side_effect = (
            sdk_exceptions.NotFoundException())
        self.assertRaises(exception.ImageNotFound,
                          attr_validator.validate_image,
                          mock_os_cli, 'ubuntu-24.04')

    def test_validate_image_with_nonexist_image_by_id(self):
        mock_os_cli = mock.MagicMock()
        mock_os_cli.glance.return_value.find_image.side_effect = (
            exception.ResourceNotFound(
                name='image',
                id='e33f0988-1730-405e-8401-30cbc8535302'))
        self.assertRaises(exception.ImageNotFound,
                          attr_validator.validate_image,
                          mock_os_cli, 'ubuntu-24.04')

    def test_validate_image_with_multi_images_same_name(self):
        mock_os_cli = mock.MagicMock()
        mock_os_cli.glance.return_value.find_image.side_effect = (
            sdk_exceptions.DuplicateResource())
        self.assertRaises(exception.Conflict,
                          attr_validator.validate_image,
                          mock_os_cli, 'ubuntu-24.04')

    def test_validate_image_without_os_distro(self):
        mock_image = mock.MagicMock()
        mock_image.os_distro = None
        mock_os_cli = mock.MagicMock()
        mock_os_cli.glance.return_value.find_image.return_value = mock_image
        self.assertRaises(exception.OSDistroFieldNotFound,
                          attr_validator.validate_image,
                          mock_os_cli, 'ubuntu-24.04')

    def test_validate_image_when_user_forbidden(self):
        mock_image = mock.MagicMock()
        mock_image.os_distro = ''
        mock_os_cli = mock.MagicMock()
        mock_os_cli.glance.return_value.find_image.return_value = mock_image
        self.assertRaises(exception.OSDistroFieldNotFound,
                          attr_validator.validate_image,
                          mock_os_cli, 'ubuntu-24.04')

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_validate_os_resources_with_invalid_flavor(self,
                                                       mock_os_cli):
        mock_cluster_template = {'flavor_id': 'test_flavor'}
        mock_flavor = mock.MagicMock()
        mock_flavor.name = 'test_flavor_not_equal'
        mock_flavor.id = 'test_flavor_id_not_equal'
        mock_flavors = [mock_flavor]
        mock_nova = mock.MagicMock()
        mock_nova.flavors.list.return_value = mock_flavors
        mock_os_cli.nova.return_value = mock_nova
        mock_context = mock.MagicMock()
        self.assertRaises(exception.FlavorNotFound,
                          attr_validator.validate_os_resources,
                          mock_context, mock_cluster_template)

    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch('magnum.api.attr_validator.validators')
    def test_validate_os_resources_without_validator(self, mock_validators,
                                                     mock_os_cli):
        mock_cluster_template = {}
        mock_context = mock.MagicMock()
        attr_validator.validate_os_resources(mock_context,
                                             mock_cluster_template)

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_validate_os_resources_with_valid_fixed_subnet(self,
                                                           os_clients_klass):
        mock_cluster_template = {'fixed_network': 'test_net',
                                 'fixed_subnet': 'test_subnet'}
        mock_context = mock.MagicMock()
        mock_os_cli = mock.MagicMock()
        os_clients_klass.return_value = mock_os_cli
        mock_neutron = mock.MagicMock()
        mock_net = mock.MagicMock()
        mock_net.name = 'test_net'
        mock_net.id = 'test_net_id'
        mock_neutron.networks.return_value = [mock_net]
        mock_subnet = mock.MagicMock()
        mock_subnet.name = 'test_subnet'
        mock_subnet.id = 'test_subnet_id'
        mock_neutron.subnets.return_value = [mock_subnet]
        mock_os_cli.neutron.return_value = mock_neutron
        attr_validator.validate_os_resources(mock_context,
                                             mock_cluster_template)

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_validate_os_resources_with_invalid_fixed_subnet(self,
                                                             os_clients_klass):
        mock_cluster_template = {'fixed_network': 'test_net',
                                 'fixed_subnet': 'test_subnet2'}
        mock_context = mock.MagicMock()
        mock_os_cli = mock.MagicMock()
        os_clients_klass.return_value = mock_os_cli
        mock_neutron = mock.MagicMock()
        mock_net = mock.MagicMock()
        mock_net.name = 'test_net'
        mock_net.id = 'test_net_id'
        mock_neutron.networks.return_value = [mock_net]
        mock_subnet = mock.MagicMock()
        mock_subnet.name = 'test_subnet'
        mock_subnet.id = 'test_subnet_id'
        mock_neutron.subnets.return_value = [mock_subnet]
        mock_os_cli.neutron.return_value = mock_neutron
        self.assertRaises(exception.FixedSubnetNotFound,
                          attr_validator.validate_os_resources, mock_context,
                          mock_cluster_template)

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_validate_os_resources_with_cluster(self, mock_os_cli):
        mock_cluster_template = {}
        mock_cluster = {
            'keypair': 'test-keypair', 'labels': {'lab1': 'val1'},
            'image_id': 'e33f0988-1730-405e-8401-30cbc8535302'
        }
        mock_keypair = mock.MagicMock()
        mock_keypair.id = 'test-keypair'
        mock_nova = mock.MagicMock()
        mock_nova.keypairs.get.return_value = mock_keypair
        mock_os_cli = mock.MagicMock()
        mock_os_cli.nova.return_value = mock_nova
        mock_context = mock.MagicMock()
        attr_validator.validate_os_resources(mock_context,
                                             mock_cluster_template,
                                             mock_cluster)

    def test_validate_flavor_root_volume_size_with_valid_boot_volume_size(
        self
    ):
        boot_volume_size = 100
        mock_flavor = mock.MagicMock()
        mock_flavor.name = 'test_flavor'
        mock_flavor.id = 'test_flavor_id'
        mock_flavor.disk = 0
        mock_flavors = [mock_flavor]
        mock_nova = mock.MagicMock()
        mock_nova.flavors.list.return_value = mock_flavors
        mock_os_cli = mock.MagicMock()
        mock_os_cli.nova.return_value = mock_nova
        attr_validator.validate_flavor_root_volume_size(
            mock_os_cli, 'test_flavor', boot_volume_size)
        self.assertFalse(mock_nova.flavors.list.called)

    def test_validate_flavor_root_volume_size_with_valid_flavor(self):
        boot_volume_size = 0
        mock_flavor = mock.MagicMock()
        mock_flavor.name = 'test_flavor'
        mock_flavor.id = 'test_flavor_id'
        mock_flavor.disk = 100
        mock_flavors = [mock_flavor]
        mock_nova = mock.MagicMock()
        mock_nova.flavors.list.return_value = mock_flavors
        mock_os_cli = mock.MagicMock()
        mock_os_cli.nova.return_value = mock_nova
        attr_validator.validate_flavor_root_volume_size(
            mock_os_cli, 'test_flavor', boot_volume_size)
        self.assertTrue(mock_nova.flavors.list.called)

    def test_validate_flavor_root_volume_size_with_invalid_resources(self):
        boot_volume_size = 0
        mock_flavor = mock.MagicMock()
        mock_flavor.name = 'test_flavor'
        mock_flavor.id = 'test_flavor_id'
        mock_flavor.disk = 0
        mock_flavors = [mock_flavor]
        mock_nova = mock.MagicMock()
        mock_nova.flavors.list.return_value = mock_flavors
        mock_os_cli = mock.MagicMock()
        mock_os_cli.nova.return_value = mock_nova
        self.assertRaises(exception.FlavorZeroRootVolumeNotSupported,
                          attr_validator.validate_flavor_root_volume_size,
                          mock_os_cli, 'test_flavor', boot_volume_size)
