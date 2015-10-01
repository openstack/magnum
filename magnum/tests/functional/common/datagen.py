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

import random
import socket
import string
import struct
import uuid

from magnum.tests.functional.api.v1.models import baymodel_model
from magnum.tests.functional.api.v1.models import baymodelpatch_model
from magnum.tests.functional.common import config


def random_uuid():
    return uuid.uuid4()


def random_string(prefix='rand', n=8, suffix=''):
    """Return a string containing random digits

    :param prefix: the exact text to start the string. Defaults to "rand"
    :param n: the number of random digits to generate
    :param suffix: the exact text to end the string
    """
    digits = "".join(str(random.randrange(0, 10)) for _ in range(n))
    return prefix + digits + suffix


def generate_random_network():
    network_list = ["public", "private"]
    return network_list[random.randrange(0, len(network_list))]


def generate_random_coe():
    coe_list = ["swarm", "kubernetes", "mesos"]
    return coe_list[random.randrange(0, len(coe_list))]


def generate_random_coe_dep_network_driver(coe):
    allowed_driver_types = {
        'kubernetes': ['flannel', None],
        'swarm': [None],
        'mesos': [None],
    }
    driver_types = allowed_driver_types[coe]
    return driver_types[random.randrange(0, len(driver_types))]


def generate_random_port():
    return random.randrange(49152, 65535)


def generate_random_docker_volume_size():
    return random.randrange(1, 100)


def generate_fake_ssh_pubkey():
    chars = "".join(
        random.choice(string.ascii_uppercase +
                      string.ascii_letters + string.digits + '/+=')
        for _ in range(372))
    return "ssh-rsa " + chars


def generate_random_ip():
    return socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xffffffff)))


def random_baymodel_data(keypair_id=random_string(), image_id=random_string()):
    """Generates random baymodel data

    Keypair and image id cannot be random for the baymodel to be valid due to
    validations for the presence of keypair and image id prior to baymodel
    creation.

    :param keypair_id: keypair name
    :param image_id: image id or name
    :returns: BayModelEntity with generated data
    """

    coe = generate_random_coe()
    data = {
        "name": random_string(),
        "image_id": image_id,
        "flavor_id": random_string(),
        "master_flavor_id": random_string(),
        "dns_nameserver": generate_random_ip(),
        "keypair_id": keypair_id,
        "external_network_id": str(random_uuid()),
        "fixed_network": generate_random_network(),
        "apiserver_port": generate_random_port(),
        "docker_volume_size": generate_random_docker_volume_size(),
        "cluster_distro": random_string(),
        "ssh_authorized_key": generate_fake_ssh_pubkey(),
        "coe": coe,
        "http_proxy": "http://proxy.com:%s" % generate_random_port(),
        "https_proxy": "https://proxy.com:%s" % generate_random_port(),
        "no_proxy": ",".join(generate_random_ip() for x in range(3)),
        "network_driver": generate_random_coe_dep_network_driver(coe),
        "labels": {"K1": "V1", "K2": "V2"},
    }
    model = baymodel_model.BayModelEntity.from_dict(data)

    return model


def random_baymodel_name_patch_data(name=random_string()):
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


def random_baymodel_data_w_valid_keypair_and_image_id():
    """Generates random baymodel data with valid keypair and image

    :returns: BayModelEntity with generated data
    """

    return random_baymodel_data(keypair_id=config.Config.keypair_id,
                                image_id=config.Config.image_id)


def random_baymodel_data_w_valid_keypair():
    """Generates random baymodel data with valid keypair

    :returns: BayModelEntity with generated data
    """

    return random_baymodel_data(keypair_id=config.Config.keypair_id)


def random_baymodel_data_w_valid_image_id():
    """Generates random baymodel data with valid image

    :returns: BayModelEntity with generated data
    """

    return random_baymodel_data(image_id=config.Config.image_id)
