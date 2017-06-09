# Copyright 2015 Rackspace  All rights reserved.
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
import contextlib

import docker
from docker.utils import utils

from magnum.conductor.handlers.common import cert_manager
from magnum.conductor import utils as conductor_utils
import magnum.conf


CONF = magnum.conf.CONF


def parse_docker_image(image):
    image_parts = image.split(':', 1)

    image_repo = image_parts[0]
    image_tag = None

    if len(image_parts) > 1:
        image_tag = image_parts[1]

    return image_repo, image_tag


def is_docker_library_version_atleast(version):
    if utils.compare_version(docker.version, version) <= 0:
        return True
    return False


def is_docker_api_version_atleast(docker, version):
    if utils.compare_version(docker.version()['ApiVersion'], version) <= 0:
        return True
    return False


@contextlib.contextmanager
def docker_for_cluster(context, cluster):
    cluster_template = conductor_utils.retrieve_cluster_template(
        context, cluster)

    ca_cert, magnum_key, magnum_cert = None, None, None
    client_kwargs = dict()
    if not cluster_template.tls_disabled:
        (ca_cert, magnum_key,
         magnum_cert) = cert_manager.create_client_files(cluster, context)
        client_kwargs['ca_cert'] = ca_cert.name
        client_kwargs['client_key'] = magnum_key.name
        client_kwargs['client_cert'] = magnum_cert.name

    yield DockerHTTPClient(
        cluster.api_address,
        CONF.docker.docker_remote_api_version,
        CONF.docker.default_timeout,
        **client_kwargs
    )

    if ca_cert:
        ca_cert.close()
    if magnum_key:
        magnum_key.close()
    if magnum_cert:
        magnum_cert.close()


class DockerHTTPClient(docker.APIClient):
    def __init__(self, url='unix://var/run/docker.sock',
                 ver=CONF.docker.docker_remote_api_version,
                 timeout=CONF.docker.default_timeout,
                 ca_cert=None,
                 client_key=None,
                 client_cert=None):

        if ca_cert and client_key and client_cert:
            ssl_config = docker.tls.TLSConfig(
                client_cert=(client_cert, client_key),
                verify=ca_cert,
                assert_hostname=False,
            )
        else:
            ssl_config = False

        super(DockerHTTPClient, self).__init__(
            base_url=url,
            version=ver,
            timeout=timeout,
            tls=ssl_config
        )

    def list_instances(self, inspect=False):
        res = []
        for container in self.containers(all=True):
            info = self.inspect_container(container['Id'])
            if not info:
                continue
            if inspect:
                res.append(info)
            else:
                res.append(info['Config'].get('Hostname'))
        return res
