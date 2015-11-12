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


from magnum.common import docker_utils
from magnum.conductor.handlers.common import docker_client
from magnum.tests.functional.python_client_base import BayAPITLSTest
from magnum.tests.functional.python_client_base import BayTest


class TestBayModelResource(BayTest):
    coe = 'swarm'

    def test_baymodel_create_and_delete(self):
        self._test_baymodel_create_and_delete(
            'test_swarm_baymodel',
            network_driver=None)


class TestSwarmAPIs(BayAPITLSTest):

    """This class will cover swarm bay basic functional testing.

       Will test all kinds of container action with tls_disabled=False mode.
    """

    @classmethod
    def setUpClass(cls):
        super(TestSwarmAPIs, cls).setUpClass()

        cls.baymodel = cls._create_baymodel('testSwarmApi',
                                            coe='swarm',
                                            tls_disabled=False,
                                            network_driver=None,
                                            docker_volume_size=5,
                                            labels={},
                                            fixed_network='192.168.0.0/24',
                                            dns_nameserver='8.8.8.8')
        cls.bay = cls._create_bay('testSwarmApi', cls.baymodel.uuid)

        config_contents = """[req]
distinguished_name = req_distinguished_name
req_extensions     = req_ext
prompt = no
[req_distinguished_name]
CN = Your Name
[req_ext]
extendedKeyUsage = clientAuth
"""
        url = cls.cs.bays.get(cls.bay.uuid).api_address
        cls._create_tls_ca_files(config_contents)
        cls.docker_client = docker_client.DockerHTTPClient(
            url,
            docker_utils.CONF.docker.docker_remote_api_version,
            docker_utils.CONF.docker.default_timeout,
            client_key=cls.key_file,
            client_cert=cls.cert_file,
            ca_cert=cls.ca_file)

    def _create_container(self, **kwargs):
        name = kwargs.get('name', 'test_container')
        image = kwargs.get('image', 'docker.io/cirros:latest')
        command = kwargs.get('command', 'ping -c 1000 8.8.8.8')
        return self.docker_client.create_container(name=name,
                                                   image=image,
                                                   command=command)

    def test_start_stop_container_from_api(self):
        # TODO(eliqiao): add test case here

        pass
