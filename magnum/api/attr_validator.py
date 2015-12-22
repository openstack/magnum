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

from glanceclient import exc as glance_exception
from novaclient import exceptions as nova_exception

from magnum.api import utils as api_utils
from magnum.common import clients
from magnum.common import exception
from magnum.objects.baymodel import BayModel


def validate_image(cli, image):
    """Validate image"""

    try:
        image_found = api_utils.get_openstack_resource(cli.glance().images,
                                                       image, 'images')
    except (glance_exception.NotFound, exception.ResourceNotFound):
        raise exception.ImageNotFound(image_id=image)
    except glance_exception.HTTPForbidden:
        raise exception.ImageNotAuthorized(image_id=image)
    if not image_found.get('os_distro'):
        raise exception.OSDistroFieldNotFound(image_id=image)
    return image_found


def validate_flavor(cli, flavor):
    """Validate flavor"""

    flavor_id = None
    flavor_list = cli.nova().flavors.list()
    for f in flavor_list:
        if f.name == flavor or f.id == flavor:
            flavor_id = f.id
            break
    if flavor_id is None:
        raise exception.FlavorNotFound(flavor=flavor)


def validate_keypair(cli, keypair):
    """Validate keypair"""

    try:
        cli.nova().keypairs.get(keypair)
    except nova_exception.NotFound:
        raise exception.KeyPairNotFound(keypair=keypair)


def validate_external_network(cli, external_network):
    """Validate external network"""

    network_id = None
    networks = cli.neutron().list_networks()
    for net in networks.get('networks'):
        if (net.get('name') == external_network or
                net.get('id') == external_network):
            network_id = net.get('id')
            break
    if network_id is None:
        raise exception.NetworkNotFound(network=external_network)


def validate_fixed_network(cli, fixed_network):
    """Validate fixed network"""

    # TODO(houming):this method implement will be added after this
    # first pathch for bay's OpenStack resources validation is merged.
    pass


def validate_os_resources(context, baymodel_id):
    """Validate baymodel's OpenStack Resources"""

    baymodel = BayModel.get_by_uuid(context, baymodel_id)
    cli = clients.OpenStackClients(context)

    for attr, validate_method in validators.items():
        if attr in baymodel and baymodel[attr] is not None:
            validate_method(cli, baymodel[attr])


# Dictionary that maintains a list of validation functions
validators = {'image_id': validate_image,
              'flavor_id': validate_flavor,
              'master_flavor_id': validate_flavor,
              'keypair_id': validate_keypair,
              'external_network_id': validate_external_network,
              'fixed_network': validate_fixed_network}
