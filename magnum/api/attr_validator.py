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
from magnum.i18n import _


SUPPORTED_ISOLATION = ['filesystem/posix', 'filesystem/linux',
                       'filesystem/shared', 'posix/cpu',
                       'posix/mem', 'posix/disk', 'cgroups/cpu',
                       'cgroups/mem', 'docker/runtime',
                       'namespaces/pid']
SUPPORTED_IMAGE_PROVIDERS = ['docker', 'appc']


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
    """Validate flavor.

    If flavor is None, skip the validation and use the default value
    from the heat template.
    """

    if flavor is None:
        return
    flavor_list = cli.nova().flavors.list()
    for f in flavor_list:
        if f.name == flavor or f.id == flavor:
            return
    raise exception.FlavorNotFound(flavor=flavor)


def validate_keypair(cli, keypair):
    """Validate keypair

    validate the keypair, if provided.
    """
    if keypair is None:
        return
    try:
        cli.nova().keypairs.get(keypair)
    except nova_exception.NotFound:
        raise exception.KeyPairNotFound(keypair=keypair)


def validate_external_network(cli, external_network):
    """Validate external network"""

    count = 0
    ext_filter = {'router:external': True}
    networks = cli.neutron().list_networks(**ext_filter)
    for net in networks.get('networks'):
        if (net.get('name') == external_network or
                net.get('id') == external_network):
            count = count + 1

    if count == 0:
        # Unable to find the external network.
        # Or the network is private.
        raise exception.ExternalNetworkNotFound(network=external_network)

    if count > 1:
        msg = _("Multiple external networks exist with same name '%s'. "
                "Please use the external network ID instead.")
        raise exception.Conflict(msg % external_network)


def validate_fixed_network(cli, fixed_network):
    """Validate fixed network"""

    count = 0
    network_id = None
    networks = cli.neutron().list_networks()
    for net in networks.get('networks'):
        if fixed_network in [net.get('name'), net.get('id')]:
            count += 1
            network_id = net.get('id')

    if count == 0:
        # Unable to find the configured fixed_network.
        raise exception.FixedNetworkNotFound(network=fixed_network)
    elif count > 1:
        msg = _("Multiple networks exist with same name '%s'. "
                "Please use the network ID instead.")
        raise exception.Conflict(msg % fixed_network)

    return network_id


def validate_fixed_subnet(cli, fixed_subnet):
    """Validate fixed subnet"""

    count = 0
    subnet_id = None
    subnets = cli.neutron().list_subnets()
    for subnet in subnets.get('subnets'):
        if fixed_subnet in [subnet.get('name'), subnet.get('id')]:
            count += 1
            subnet_id = subnet.get('id')

    if count == 0:
        # Unable to find the configured fixed_subnet.
        raise exception.FixedSubnetNotFound(subnet=fixed_subnet)
    elif count > 1:
        msg = _("Multiple subnets exist with same name '%s'. "
                "Please use the subnet ID instead.")
        raise exception.Conflict(msg % fixed_subnet)
    else:
        return subnet_id


def validate_labels(labels):
    """"Validate labels"""

    for attr, validate_method in labels_validators.items():
        if labels.get(attr) is not None:
            validate_method(labels)


def validate_os_resources(context, cluster_template, cluster=None):
    """Validate ClusterTemplate's OpenStack Resources"""

    cli = clients.OpenStackClients(context)

    for attr, validate_method in validators.items():
        if cluster and attr in cluster and cluster[attr]:
            if attr == 'labels':
                validate_method(cluster[attr])
            else:
                validate_method(cli, cluster[attr])
        elif attr in cluster_template and cluster_template[attr] is not None:
            if attr == 'labels':
                validate_method(cluster_template[attr])
            else:
                validate_method(cli, cluster_template[attr])

    if cluster:
        validate_keypair(cli, cluster['keypair'])


def validate_master_count(context, cluster):
    if (
        cluster['master_count'] > 1 and
        not cluster['master_lb_enabled']
    ):
        raise exception.InvalidParameterValue(_(
            "master_count must be 1 when master_lb_enabled is False"))


def validate_federation_hostcluster(cluster_uuid):
    """Validate Federation `hostcluster_id` parameter.

    If the parameter was not specified raise an
    `exceptions.InvalidParameterValue`. If the specified identifier does not
    identify any Cluster, raise `exception.ClusterNotFound`
    """
    if cluster_uuid is not None:
        api_utils.get_resource('Cluster', cluster_uuid)
    else:
        raise exception.InvalidParameterValue(
            "No hostcluster specified. "
            "Please specify a hostcluster_id.")


def validate_federation_properties(properties):
    """Validate Federation `properties` parameter."""
    if properties is None:
        raise exception.InvalidParameterValue(
            "Please specify a `properties` "
            "dict for the federation.")
    # Currently, we only support the property `dns-zone`.
    if properties.get('dns-zone') is None:
        raise exception.InvalidParameterValue("No DNS zone specified. "
                                              "Please specify a `dns-zone`.")


# Dictionary that maintains a list of validation functions
validators = {'image_id': validate_image,
              'flavor_id': validate_flavor,
              'master_flavor_id': validate_flavor,
              'external_network_id': validate_external_network,
              'fixed_network': validate_fixed_network,
              'fixed_subnet': validate_fixed_subnet,
              'labels': validate_labels}

labels_validators = {}
