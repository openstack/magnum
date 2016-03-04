# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import random
import socket
import string
import struct

from tempest.lib.common.utils import data_utils

from magnum.tests.functional.api.v1.models import bay_model
from magnum.tests.functional.api.v1.models import baymodel_model
from magnum.tests.functional.api.v1.models import baymodelpatch_model
from magnum.tests.functional.api.v1.models import baypatch_model
from magnum.tests.functional.api.v1.models import cert_model
from magnum.tests.functional.common import config


def random_int(min_int=1, max_int=100):
    return random.randrange(min_int, max_int)


def gen_coe_dep_network_driver(coe):
    allowed_driver_types = {
        'kubernetes': ['flannel', None],
        'swarm': ['docker', 'flannel', None],
        'mesos': ['docker', None],
    }
    driver_types = allowed_driver_types[coe]
    return driver_types[random.randrange(0, len(driver_types))]


def gen_coe_dep_volume_driver(coe):
    allowed_driver_types = {
        'kubernetes': ['cinder', None],
        'swarm': ['rexray', None],
        'mesos': ['rexray', None],
    }
    driver_types = allowed_driver_types[coe]
    return driver_types[random.randrange(0, len(driver_types))]


def gen_random_port():
    return random_int(49152, 65535)


def gen_docker_volume_size(min_int=3, max_int=5):
    return random_int(min_int, max_int)


def gen_fake_ssh_pubkey():
    chars = "".join(
        random.choice(string.ascii_uppercase +
                      string.ascii_letters + string.digits + '/+=')
        for _ in range(372))
    return "ssh-rsa " + chars


def gen_random_ip():
    return socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xffffffff)))


def gen_url(scheme="http", domain="example.com", port=80):
    return "%s://%s:%s" % (scheme, domain, port)


def gen_http_proxy():
    return gen_url(port=gen_random_port())


def gen_https_proxy():
    return gen_url(scheme="https", port=gen_random_port())


def gen_no_proxy():
    return ",".join(gen_random_ip() for x in range(3))


def baymodel_data(**kwargs):
    """Generates random baymodel data

    Keypair and image id cannot be random for the baymodel to be valid due to
    validations for the presence of keypair and image id prior to baymodel
    creation.

    :param keypair_id: keypair name
    :param image_id: image id or name
    :returns: BayModelEntity with generated data
    """

    data = {
        "name": data_utils.rand_name('bay'),
        "coe": "swarm",
        "tls_disabled": False,
        "network_driver": None,
        "volume_driver": None,
        "docker_volume_size": 3,
        "labels": {},
        "fixed_network": "192.168.0.0/24",
        "dns_nameserver": "8.8.8.8",
        "flavor_id": data_utils.rand_name('bay'),
        "master_flavor_id": data_utils.rand_name('bay'),
        "external_network_id": "public",
        "keypair_id": data_utils.rand_name('bay'),
        "image_id": data_utils.rand_name('bay')
    }

    data.update(kwargs)
    model = baymodel_model.BayModelEntity.from_dict(data)

    return model


def baymodel_name_patch_data(name=data_utils.rand_name('bay')):
    """Generates random baymodel patch data

    :param name: name to replace in patch
    :returns: BayModelPatchCollection with generated data
    """

    data = [{
        "path": "/name",
        "value": name,
        "op": "replace"
    }]
    return baymodelpatch_model.BayModelPatchCollection.from_dict(data)


def baymodel_flavor_patch_data(flavor=data_utils.rand_name('bay')):
    """Generates random baymodel patch data

    :param flavor: flavor to replace in patch
    :returns: BayModelPatchCollection with generated data
    """

    data = [{
        "path": "/flavor_id",
        "value": flavor,
        "op": "replace"
    }]
    return baymodelpatch_model.BayModelPatchCollection.from_dict(data)


def baymodel_data_with_valid_keypair_image_flavor():
    """Generates random baymodel data with valid keypair,image and flavor

    :returns: BayModelEntity with generated data
    """

    return baymodel_data(keypair_id=config.Config.keypair_id,
                         image_id=config.Config.image_id,
                         flavor_id=config.Config.flavor_id,
                         master_flavor_id=config.Config.master_flavor_id)


def baymodel_data_with_valid_keypair():
    """Generates random baymodel data with valid keypair

    :returns: BayModelEntity with generated data
    """

    return baymodel_data(keypair_id=config.Config.keypair_id)


def baymodel_valid_data_with_specific_coe(coe):
    """Generates random baymodel data with valid keypair and image

    :param coe: coe
    :returns: BayModelEntity with generated data
    """

    return baymodel_data(keypair_id=config.Config.keypair_id,
                         image_id=config.Config.image_id, coe=coe)


def baymodel_data_with_valid_image_and_flavor():
    """Generates random baymodel data with valid image

    :returns: BayModelEntity with generated data
    """

    return baymodel_data(image_id=config.Config.image_id,
                         flavor_id=config.Config.flavor_id,
                         master_flavor_id=config.Config.master_flavor_id)


def valid_swarm_baymodel():
    """Generates a valid swarm baymodel with valid data

    :returns: BayModelEntity with generated data
    """

    return baymodel_data(image_id=config.Config.image_id,
                         fixed_network="192.168.0.0/24",
                         flavor_id=config.Config.flavor_id, public=False,
                         dns_nameserver=config.Config.dns_nameserver,
                         master_flavor_id=config.Config.master_flavor_id,
                         keypair_id=config.Config.keypair_id, coe="swarm",
                         docker_volume_size=3, cluster_distro=None,
                         external_network_id="public",
                         http_proxy=None, https_proxy=None, no_proxy=None,
                         network_driver=None, volume_driver=None, labels={},
                         tls_disabled=False)


def bay_data(name=data_utils.rand_name('bay'),
             baymodel_id=data_utils.rand_uuid(),
             node_count=random_int(1, 5), discovery_url=gen_random_ip(),
             bay_create_timeout=random_int(1, 30),
             master_count=random_int(1, 5)):
    """Generates random bay data

    BayModel_id cannot be random for the bay to be valid due to
    validations for the presence of baymodel prior to baymodel
    creation.

    :param name: bay name (must be unique)
    :param baymodel_id: baymodel unique id (must already exist)
    :param node_count: number of agents for bay
    :param discovery_url: url provided for node discovery
    :param bay_create_timeout: timeout in minutes for bay create
    :param master_count: number of master nodes for the bay
    :returns: BayEntity with generated data
    """

    data = {
        "name": name,
        "baymodel_id": baymodel_id,
        "node_count": node_count,
        "discovery_url": None,
        "bay_create_timeout": bay_create_timeout,
        "master_count": master_count
    }
    model = bay_model.BayEntity.from_dict(data)

    return model


def valid_bay_data(baymodel_id, name=data_utils.rand_name('bay'), node_count=1,
                   master_count=1, bay_create_timeout=None):
    """Generates random bay data with valid

    :param baymodel_id: baymodel unique id that already exists
    :param name: bay name (must be unique)
    :param node_count: number of agents for bay
    :returns: BayEntity with generated data
    """

    return bay_data(baymodel_id=baymodel_id, name=name,
                    master_count=master_count, node_count=node_count,
                    bay_create_timeout=bay_create_timeout)


def bay_name_patch_data(name=data_utils.rand_name('bay')):
    """Generates random baymodel patch data

    :param name: name to replace in patch
    :returns: BayPatchCollection with generated data
    """

    data = [{
        "path": "/name",
        "value": name,
        "op": "replace"
    }]
    return baypatch_model.BayPatchCollection.from_dict(data)


def bay_api_addy_patch_data(address='0.0.0.0'):
    """Generates random bay patch data

    :param name: name to replace in patch
    :returns: BayPatchCollection with generated data
    """

    data = [{
        "path": "/api_address",
        "value": address,
        "op": "replace"
    }]
    return baypatch_model.BayPatchCollection.from_dict(data)


def bay_node_count_patch_data(node_count=2):
    """Generates random bay patch data

    :param name: name to replace in patch
    :returns: BayPatchCollection with generated data
    """

    data = [{
        "path": "/node_count",
        "value": node_count,
        "op": "replace"
    }]
    return baypatch_model.BayPatchCollection.from_dict(data)


def cert_data(bay_uuid, csr_data=None):
    if csr_data is None:
        csr_data = config.Config.csr_location
    data = {
        "bay_uuid": bay_uuid
    }
    if csr_data is not None and os.path.isfile(csr_data):
        with open(csr_data, 'r') as f:
            data['csr'] = f.read()
    else:
        data['csr'] = csr_data

    model = cert_model.CertEntity.from_dict(data)

    return model
