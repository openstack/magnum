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

import time

from docker import errors
from requests import exceptions as req_exceptions

from magnum.common import docker_utils
import magnum.conf
from magnum.tests.functional.python_client_base import ClusterTest


CONF = magnum.conf.CONF


class TestSwarmAPIs(ClusterTest):
    """This class will cover swarm cluster basic functional testing.

       Will test all kinds of container action with tls_disabled=False mode.
    """

    coe = "swarm"
    cluster_template_kwargs = {
        "tls_disabled": False,
        "network_driver": None,
        "volume_driver": None,
        "labels": {}
    }

    @classmethod
    def setUpClass(cls):
        super(TestSwarmAPIs, cls).setUpClass()
        cls.cluster_is_ready = None

    def setUp(self):
        super(TestSwarmAPIs, self).setUp()
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
        self.docker_client = docker_utils.DockerHTTPClient(
            url,
            CONF.docker.docker_remote_api_version,
            docker_api_time_out,
            client_key=self.key_file,
            client_cert=self.cert_file,
            ca_cert=self.ca_file)

        self.docker_client_non_tls = docker_utils.DockerHTTPClient(
            url,
            CONF.docker.docker_remote_api_version,
            docker_api_time_out)

    def _container_operation(self, func, *args, **kwargs):
        # NOTE(hongbin): Swarm cluster occasionally aborts the connection,
        # so we re-try the operation several times here. In long-term, we
        # need to investigate the cause of this issue. See bug #1583337.
        for i in range(150):
            try:
                self.LOG.info("Calling function %s", func.__name__)
                return func(*args, **kwargs)
            except req_exceptions.ConnectionError:
                self.LOG.info("Connection aborted on calling Swarm API. "
                              "Will retry in 2 seconds.")
            except errors.APIError as e:
                if e.response.status_code != 500:
                    raise
                self.LOG.info("Internal Server Error: %s", e)
            time.sleep(2)

        raise Exception("Cannot connect to Swarm API.")

    def _create_container(self, **kwargs):
        image = kwargs.get('image', 'docker.io/cirros')
        command = kwargs.get('command', 'ping -c 1000 8.8.8.8')
        return self._container_operation(self.docker_client.create_container,
                                         image=image, command=command)

    def test_start_stop_container_from_api(self):
        # Leverage docker client to create a container on the cluster we
        # created, and try to start and stop it then delete it.

        resp = self._create_container(image="docker.io/cirros",
                                      command="ping -c 1000 8.8.8.8")

        resp = self._container_operation(self.docker_client.containers,
                                         all=True)
        container_id = resp[0].get('Id')
        self._container_operation(self.docker_client.start,
                                  container=container_id)

        resp = self._container_operation(self.docker_client.containers)
        self.assertEqual(1, len(resp))
        resp = self._container_operation(self.docker_client.inspect_container,
                                         container=container_id)
        self.assertTrue(resp['State']['Running'])

        self._container_operation(self.docker_client.stop,
                                  container=container_id)
        resp = self._container_operation(self.docker_client.inspect_container,
                                         container=container_id)
        self.assertEqual(False, resp['State']['Running'])

        self._container_operation(self.docker_client.remove_container,
                                  container=container_id)
        resp = self._container_operation(self.docker_client.containers)
        self.assertEqual([], resp)

    def test_access_with_non_tls_client(self):
        """Try to contact master's docker using the TCP protocol.

        TCP returns ConnectionError whereas HTTPS returns SSLError. The
        default protocol we use in magnum is TCP which works fine docker
        python SDK docker>=2.0.0.
        """
        self.assertRaises(req_exceptions.ConnectionError,
                          self.docker_client_non_tls.containers)
