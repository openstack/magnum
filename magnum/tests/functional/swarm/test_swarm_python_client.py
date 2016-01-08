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

from oslo_config import cfg
from requests import exceptions as req_exceptions
import time

from magnum.common import docker_utils
from magnum.tests.functional.python_client_base import BayAPITLSTest
from magnum.tests.functional.python_client_base import BayTest
from magnumclient.openstack.common.apiclient import exceptions


CONF = cfg.CONF
CONF.import_opt('docker_remote_api_version', 'magnum.common.docker_utils',
                group='docker')
CONF.import_opt('default_timeout', 'magnum.common.docker_utils',
                group='docker')


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
                                            docker_volume_size=3,
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

        # Note(eliqiao): docker_utils.CONF.docker.default_timeout is 10,
        # tested this default configure option not works on gate, it will
        # cause container creation failed due to time out.
        # Debug more found that we need to pull image when the first time to
        # create a container, set it as 180s.

        docker_api_time_out = 180
        cls.docker_client = docker_utils.DockerHTTPClient(
            url,
            CONF.docker.docker_remote_api_version,
            docker_api_time_out,
            client_key=cls.key_file,
            client_cert=cls.cert_file,
            ca_cert=cls.ca_file)

        cls.docker_client_non_tls = docker_utils.DockerHTTPClient(
            url,
            CONF.docker.docker_remote_api_version,
            docker_api_time_out)

        # Note(eliqiao): In our test cases, docker client or magnum client will
        # try to connect to swarm service which is running on master node,
        # the endpoint is bay.api_address(listen port is included), but the
        # service is not ready right after the bay was created, sleep for an
        # acceptable time to wait for service being started.
        # This is required, without this any api call will fail as
        # 'ConnectionError: [Errno 111] Connection refused'.

        bay_is_ready = False

        for i in range(150):
            try:
                cls.docker_client.containers()
                # Note(eliqiao): Right after the connection is ready, wait
                # for a while (at least 5s) to aovid this error:
                # docker.errors.APIError: 500 Server Error: Internal
                # Server Error ("No healthy node available in the cluster")
                time.sleep(10)
                bay_is_ready = True
                break
            except req_exceptions.ConnectionError:
                time.sleep(2)
        # In such case, no need to test below cases on gate, raise a meanful
        # exception message to indicate ca setup failed after bay creation,
        # Better to do a `recheck`
        if not bay_is_ready:
            msg = ("If you see this error in the functional test, it means "
                   "the docker service took too long to come up. This may not "
                   "be an actual error, so an option is to rerun the "
                   "functional test.")
            raise Exception(msg)

    def _create_container(self, **kwargs):
        name = kwargs.get('name', 'test_container')
        image = kwargs.get('image', 'docker.io/cirros:latest')
        command = kwargs.get('command', 'ping -c 1000 8.8.8.8')
        return self.docker_client.create_container(name=name,
                                                   image=image,
                                                   command=command)

    def test_start_stop_container_from_api(self):
        # Leverage docker client to create a container on the bay we created,
        # and try to start and stop it then delete it.

        resp = self._create_container(name="test_start_stop",
                                      command="ping -c 1000 8.8.8.8")

        self.assertIsNotNone(resp)
        container_id = resp.get('Id')
        self.docker_client.start(container=container_id)

        resp = self.docker_client.containers()
        self.assertIsNotNone(resp)
        resp = self.docker_client.inspect_container(container=container_id)
        self.assertTrue(resp['State']['Running'])

        self.docker_client.stop(container=container_id)
        resp = self.docker_client.inspect_container(container=container_id)
        self.assertFalse(resp['State']['Running'])

        self.docker_client.remove_container(container=container_id)
        resp = self.docker_client.containers()
        self.assertEqual([], resp)

    def test_access_with_non_tls_client(self):
        self.assertRaises(req_exceptions.SSLError,
                          self.docker_client_non_tls.containers)

    def test_start_stop_container_from_cs(self):
        # Leverage Magnum client to create a container on the bay we created,
        # and try to start and stop it then delete it.

        container = self.cs.containers.create(name="test_cs_start_stop",
                                              image="docker.io/cirros",
                                              bay_uuid=self.bay.uuid,
                                              command='ping -c 1000 8.8.8.8')
        self.assertIsNotNone(container)
        container_uuid = container.uuid

        resp = self.cs.containers.start(container_uuid)
        self.assertEqual(200, resp[0].status_code)

        container = self.cs.containers.get(container_uuid)
        self.assertEqual('Running', container.status)

        resp = self.cs.containers.stop(container_uuid)
        container = self.cs.containers.get(container_uuid)
        self.assertEqual('Stopped', container.status)

        container = self.cs.containers.delete(container_uuid)
        self.assertRaises(exceptions.NotFound,
                          self.cs.containers.get, container_uuid)
