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

from tempest.lib.common.utils import data_utils

from magnum.tests.functional.api.v1.models import cert_model
from magnum.tests.functional.api.v1.models import cluster_model
from magnum.tests.functional.api.v1.models import cluster_template_model
from magnum.tests.functional.api.v1.models import cluster_templatepatch_model
from magnum.tests.functional.api.v1.models import clusterpatch_model
from magnum.tests.functional.common import config


def random_int(min_int=1, max_int=100):
    return random.randrange(min_int, max_int)


def gen_coe_dep_network_driver(coe):
    allowed_driver_types = {
        'kubernetes': ['flannel', None],
    }
    driver_types = allowed_driver_types[coe]
    return driver_types[random.randrange(0, len(driver_types))]


def gen_coe_dep_volume_driver(coe):
    allowed_driver_types = {
        'kubernetes': ['cinder', None],
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


def cert_data(cluster_uuid, csr_data):
    data = {
        "cluster_uuid": cluster_uuid,
        "csr": csr_data}

    model = cert_model.CertEntity.from_dict(data)

    return model


def cluster_template_data(**kwargs):
    """Generates random cluster_template data

    Keypair and image id cannot be random for the cluster_template to be valid
    due to validations for the presence of keypair and image id prior to
    cluster_template creation.

    :param keypair_id: keypair name
    :param image_id: image id or name
    :returns: ClusterTemplateEntity with generated data
    """

    data = {
        "name": data_utils.rand_name('cluster'),
        "coe": "kubernetes",
        "tls_disabled": False,
        "network_driver": None,
        "volume_driver": None,
        "labels": {},
        "public": False,
        "dns_nameserver": "8.8.8.8",
        "flavor_id": data_utils.rand_name('cluster'),
        "master_flavor_id": data_utils.rand_name('cluster'),
        "external_network_id": config.Config.nic_id,
        "keypair_id": data_utils.rand_name('cluster'),
        "image_id": data_utils.rand_name('cluster')
    }

    data.update(kwargs)
    model = cluster_template_model.ClusterTemplateEntity.from_dict(data)

    return model


def cluster_template_replace_patch_data(path,
                                        value=data_utils.rand_name('cluster')):
    """Generates random ClusterTemplate patch data

    :param path: path to replace
    :param value: value to replace in patch
    :returns: ClusterTemplatePatchCollection with generated data
    """

    data = [{
        "path": path,
        "value": value,
        "op": "replace"
    }]
    collection = cluster_templatepatch_model.ClusterTemplatePatchCollection
    return collection.from_dict(data)


def cluster_template_remove_patch_data(path):
    """Generates ClusterTemplate patch data by removing value

    :param path: path to remove
    :returns: ClusterTemplatePatchCollection with generated data
    """

    data = [{
        "path": path,
        "op": "remove"
    }]
    collection = cluster_templatepatch_model.ClusterTemplatePatchCollection
    return collection.from_dict(data)


def cluster_template_name_patch_data(name=data_utils.rand_name('cluster')):
    """Generates random cluster_template patch data

    :param name: name to replace in patch
    :returns: ClusterTemplatePatchCollection with generated data
    """

    data = [{
        "path": "/name",
        "value": name,
        "op": "replace"
    }]
    collection = cluster_templatepatch_model.ClusterTemplatePatchCollection
    return collection.from_dict(data)


def cluster_template_flavor_patch_data(flavor=data_utils.rand_name('cluster')):
    """Generates random cluster_template patch data

    :param flavor: flavor to replace in patch
    :returns: ClusterTemplatePatchCollection with generated data
    """

    data = [{
        "path": "/flavor_id",
        "value": flavor,
        "op": "replace"
    }]
    collection = cluster_templatepatch_model.ClusterTemplatePatchCollection
    return collection.from_dict(data)


def cluster_template_data_with_valid_keypair_image_flavor():
    """Generates random clustertemplate data with valid data

    :returns: ClusterTemplateEntity with generated data
    """
    master_flavor = config.Config.master_flavor_id
    return cluster_template_data(keypair_id=config.Config.keypair_id,
                                 image_id=config.Config.image_id,
                                 flavor_id=config.Config.flavor_id,
                                 master_flavor_id=master_flavor)


def cluster_template_data_with_missing_image():
    """Generates random cluster_template data with missing image

    :returns: ClusterTemplateEntity with generated data
    """

    return cluster_template_data(
        keypair_id=config.Config.keypair_id,
        flavor_id=config.Config.flavor_id,
        master_flavor_id=config.Config.master_flavor_id)


def cluster_template_data_with_missing_flavor():
    """Generates random cluster_template data with missing flavor

    :returns: ClusterTemplateEntity with generated data
    """

    return cluster_template_data(keypair_id=config.Config.keypair_id,
                                 image_id=config.Config.image_id)


def cluster_template_data_with_missing_keypair():
    """Generates random cluster_template data with missing keypair

    :returns: ClusterTemplateEntity with generated data
    """

    return cluster_template_data(
        image_id=config.Config.image_id,
        flavor_id=config.Config.flavor_id,
        master_flavor_id=config.Config.master_flavor_id)


def cluster_template_valid_data_with_specific_coe(coe):
    """Generates random cluster_template data with valid keypair and image

    :param coe: coe
    :returns: ClusterTemplateEntity with generated data
    """

    return cluster_template_data(keypair_id=config.Config.keypair_id,
                                 image_id=config.Config.image_id, coe=coe)


def cluster_data(name=data_utils.rand_name('cluster'),
                 cluster_template_id=data_utils.rand_uuid(),
                 node_count=random_int(1, 5), discovery_url=gen_random_ip(),
                 create_timeout=random_int(1, 30),
                 master_count=random_int(1, 5)):
    """Generates random cluster data

    cluster_template_id cannot be random for the cluster to be valid due to
    validations for the presence of clustertemplate prior to clustertemplate
    creation.

    :param name: cluster name (must be unique)
    :param cluster_template_id: clustertemplate unique id (must already exist)
    :param node_count: number of agents for cluster
    :param discovery_url: url provided for node discovery
    :param create_timeout: timeout in minutes for cluster create
    :param master_count: number of master nodes for the cluster
    :returns: ClusterEntity with generated data
    """

    data = {
        "name": name,
        "cluster_template_id": cluster_template_id,
        "keypair": config.Config.keypair_id,
        "node_count": node_count,
        "discovery_url": None,
        "create_timeout": create_timeout,
        "master_count": master_count
    }
    model = cluster_model.ClusterEntity.from_dict(data)

    return model


def valid_cluster_data(cluster_template_id,
                       name=data_utils.rand_name('cluster'),
                       node_count=1, master_count=1, create_timeout=None):
    """Generates random cluster data with valid

    :param cluster_template_id: clustertemplate unique id that already exists
    :param name: cluster name (must be unique)
    :param node_count: number of agents for cluster
    :returns: ClusterEntity with generated data
    """

    return cluster_data(cluster_template_id=cluster_template_id, name=name,
                        master_count=master_count, node_count=node_count,
                        create_timeout=create_timeout)


def cluster_name_patch_data(name=data_utils.rand_name('cluster')):
    """Generates random clustertemplate patch data

    :param name: name to replace in patch
    :returns: ClusterPatchCollection with generated data
    """

    data = [{
        "path": "/name",
        "value": name,
        "op": "replace"
    }]
    return clusterpatch_model.ClusterPatchCollection.from_dict(data)


def cluster_api_addy_patch_data(address='0.0.0.0'):
    """Generates random cluster patch data

    :param name: name to replace in patch
    :returns: ClusterPatchCollection with generated data
    """

    data = [{
        "path": "/api_address",
        "value": address,
        "op": "replace"
    }]
    return clusterpatch_model.ClusterPatchCollection.from_dict(data)


def cluster_node_count_patch_data(node_count=2):
    """Generates random cluster patch data

    :param name: name to replace in patch
    :returns: ClusterPatchCollection with generated data
    """

    data = [{
        "path": "/node_count",
        "value": node_count,
        "op": "replace"
    }]
    return clusterpatch_model.ClusterPatchCollection.from_dict(data)
