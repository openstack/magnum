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

import docker
import requests
import time

import magnum.conf
from magnum.tests.functional.python_client_base import ClusterTest


CONF = magnum.conf.CONF


class TestSwarmModeAPIs(ClusterTest):
    """This class will cover swarm cluster basic functional testing.

       Will test all kinds of container action with tls_disabled=False mode.
    """

    coe = "swarm-mode"
    cluster_template_kwargs = {
        "tls_disabled": False,
        "network_driver": None,
        "volume_driver": None,
        "labels": {}
    }

    @classmethod
    def setUpClass(cls):
        super(TestSwarmModeAPIs, cls).setUpClass()
        cls.cluster_is_ready = None

    def setUp(self):
        super(TestSwarmModeAPIs, self).setUp()
        if self.cluster_is_ready is True:
            return
        # Note(eliqiao): In our test cases, docker client or magnum client will
        # try to connect to swarm service which is running on master node,
        # the endpoint is cluster.api_address(listen port is included), but the
        # service is not ready right after the cluster was created, sleep for
        # an acceptable time to wait for service being started.
        # This is required, without this any api call will fail as
        # 'ConnectionError: [Errno 111] Connection refused'.
        msg = ("If you see this error in the functional test, it means "
               "the docker service took too long to come up. This may not "
               "be an actual error, so an option is to rerun the "
               "functional test.")
        if self.cluster_is_ready is False:
            # In such case, no need to test below cases on gate, raise a
            # meanful exception message to indicate ca setup failed after
            # cluster creation, better to do a `recheck`
            # We don't need to test since cluster is not ready.
            raise Exception(msg)

        url = self.cs.clusters.get(self.cluster.uuid).api_address

        # Note(eliqiao): docker_utils.CONF.docker.default_timeout is 10,
        # tested this default configure option not works on gate, it will
        # cause container creation failed due to time out.
        # Debug more found that we need to pull image when the first time to
        # create a container, set it as 180s.

        docker_api_time_out = 180
        tls_config = docker.tls.TLSConfig(
            client_cert=(self.cert_file, self.key_file),
            verify=self.ca_file
        )

        self.docker_client = docker.DockerClient(
            base_url=url,
            tls=tls_config,
            version='auto',
            timeout=docker_api_time_out)

        self.docker_client_non_tls = docker.DockerClient(
            base_url=url,
            version='1.21',
            timeout=docker_api_time_out)

    def test_create_remove_service(self):
        # Create and remove a service using docker python SDK.
        # Wait 15 mins until reach running and 5 mins until the service
        # is removed.

        # Create a nginx service based on alpine linux
        service = self.docker_client.services.create(
            name='nginx',
            image='nginx:mainline-alpine')
        # wait for 15 mins to be running
        for i in range(90):
            if service.tasks()[0]['Status']['State'] == "running":
                break
            time.sleep(10)
        # Verify that it is running
        self.assertEqual('running', service.tasks()[0]['Status']['State'])
        # Remove the service and wait for 5 mins untils it is removed
        service.remove()
        for i in range(30):
            if self.docker_client.services.list() == []:
                break
            time.sleep(10)
        # Verify that it is deleted
        self.assertEqual([], self.docker_client.services.list())

    def test_access_with_non_tls_client(self):
        """Try to contact master's docker using the tcp protocol.

        tcp returns ConnectionError whereas https returns SSLError. The
        default protocol we use in magnum is tcp which works fine docker
        python SDK docker>=2.0.0.
        """
        try:
            self.docker_client_non_tls.info()
        except requests.exceptions.ConnectionError:
            pass
