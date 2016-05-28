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
from oslo_serialization import jsonutils as json

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
    """Validate flavor"""

    if flavor is None:
        return
    flavor_list = cli.nova().flavors.list()
    for f in flavor_list:
        if f.name == flavor or f.id == flavor:
            return
    raise exception.FlavorNotFound(flavor=flavor)


def validate_keypair(cli, keypair):
    """Validate keypair"""

    try:
        cli.nova().keypairs.get(keypair)
    except nova_exception.NotFound:
        raise exception.KeyPairNotFound(keypair=keypair)


def validate_external_network(cli, external_network):
    """Validate external network"""

    networks = cli.neutron().list_networks()
    for net in networks.get('networks'):
        if (net.get('name') == external_network or
                net.get('id') == external_network):
            return
    raise exception.NetworkNotFound(network=external_network)


def validate_fixed_network(cli, fixed_network):
    """Validate fixed network"""

    # TODO(houming):this method implement will be added after this
    # first pathch for bay's OpenStack resources validation is merged.
    pass


def validate_labels(labels):
    """"Validate labels"""

    for attr, validate_method in labels_validators.items():
        if labels.get(attr) is not None:
            validate_method(labels)


def validate_labels_isolation(labels):
    """Validate mesos_slave_isolation"""
    mesos_slave_isolation = labels.get('mesos_slave_isolation')
    mesos_slave_isolation_list = mesos_slave_isolation.split(',')
    unsupported_isolations = set(mesos_slave_isolation_list) - set(
        SUPPORTED_ISOLATION)
    if (len(unsupported_isolations) > 0):
        raise exception.InvalidParameterValue(_(
            'property "labels/mesos_salve_isolation" with value '
            '"%(isolation_val)s" is not supported, supported values are: '
            '%(supported_isolation)s') % {
                'isolation_val': ', '.join(list(unsupported_isolations)),
                'supported_isolation': ', '.join(
                    SUPPORTED_ISOLATION + ['unspecified'])})


def validate_labels_image_providers(labels):
    """Validate mesos_slave_image_providers"""
    mesos_slave_image_providers = labels.get('mesos_slave_image_providers')
    mesos_slave_image_providers_list = mesos_slave_image_providers.split(',')
    isolation_with_valid_data = False
    for image_providers_val in mesos_slave_image_providers_list:
        image_providers_val = image_providers_val.lower()
        if image_providers_val not in SUPPORTED_IMAGE_PROVIDERS:
            raise exception.InvalidParameterValue(_(
                'property "labels/mesos_slave_image_providers" with value '
                '"%(image_providers)s" is not supported, supported values '
                'are: %(supported_image_providers)s') % {
                'image_providers': image_providers_val,
                'supported_image_providers': ', '.join(
                    SUPPORTED_IMAGE_PROVIDERS + ['unspecified'])})

        if image_providers_val == 'docker':
            mesos_slave_isolation = labels.get('mesos_slave_isolation')
            if mesos_slave_isolation is not None:
                mesos_slave_isolation_list = mesos_slave_isolation.split(',')
                for isolations_val in mesos_slave_isolation_list:
                    if isolations_val == 'docker/runtime':
                        isolation_with_valid_data = True
            if mesos_slave_isolation is None or not isolation_with_valid_data:
                raise exception.RequiredParameterNotProvided(_(
                    "Docker runtime isolator has to be specified if 'docker' "
                    "is included in 'mesos_slave_image_providers' Please add "
                    "'docker/runtime' to 'mesos_slave_isolation' labels "
                    "flags"))


def validate_labels_executor_env_variables(labels):
    """Validate executor_environment_variables"""
    mesos_slave_executor_env_val = labels.get(
        'mesos_slave_executor_env_variables')
    try:
        json.loads(mesos_slave_executor_env_val)
    except ValueError:
        err = (_("Json format error"))
        raise exception.InvalidParameterValue(err)


def validate_os_resources(context, baymodel):
    """Validate baymodel's OpenStack Resources"""

    cli = clients.OpenStackClients(context)

    for attr, validate_method in validators.items():
        if attr in baymodel and baymodel[attr] is not None:
            if attr != 'labels':
                validate_method(cli, baymodel[attr])
            else:
                validate_method(baymodel[attr])


# Dictionary that maintains a list of validation functions
validators = {'image_id': validate_image,
              'flavor_id': validate_flavor,
              'master_flavor_id': validate_flavor,
              'keypair_id': validate_keypair,
              'external_network_id': validate_external_network,
              'fixed_network': validate_fixed_network,
              'labels': validate_labels}

labels_validators = {'mesos_slave_isolation': validate_labels_isolation,
                     'mesos_slave_image_providers':
                     validate_labels_image_providers,
                     'mesos_slave_executor_env_variables':
                     validate_labels_executor_env_variables}
