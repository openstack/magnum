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

"""
test_magnum
----------------------------------

Tests for `magnum` module.
"""

import os
import subprocess
import tempfile
import time

import fixtures
from six.moves import configparser

from heatclient import client as heatclient
from keystoneauth1.identity import v3 as ksa_v3
from keystoneauth1 import session as ksa_session
from keystoneclient.v3 import client as ksclient
from kubernetes import client as k8s_config
from kubernetes.client import api_client
from kubernetes.client.apis import core_v1_api

from magnum.common.utils import rmtree_without_raise
import magnum.conf
from magnum.tests.functional.common import base
from magnum.tests.functional.common import utils
from magnumclient.common.apiclient import exceptions
from magnumclient.common import cliutils
from magnumclient.v1 import client as v1client

CONF = magnum.conf.CONF


class BaseMagnumClient(base.BaseMagnumTest):

    @classmethod
    def setUpClass(cls):
        # Collecting of credentials:
        #
        # Support the existence of a functional_creds.conf for
        # testing. This makes it possible to use a config file.
        super(BaseMagnumClient, cls).setUpClass()
        user = cliutils.env('OS_USERNAME')
        passwd = cliutils.env('OS_PASSWORD')
        project_name = cliutils.env('OS_PROJECT_NAME')
        auth_url = cliutils.env('OS_AUTH_URL')
        insecure = cliutils.env('INSECURE')
        region_name = cliutils.env('OS_REGION_NAME')
        magnum_url = cliutils.env('BYPASS_URL')
        image_id = cliutils.env('IMAGE_ID')
        nic_id = cliutils.env('NIC_ID')
        flavor_id = cliutils.env('FLAVOR_ID')
        master_flavor_id = cliutils.env('MASTER_FLAVOR_ID')
        keypair_id = cliutils.env('KEYPAIR_ID')
        dns_nameserver = cliutils.env('DNS_NAMESERVER')
        copy_logs = cliutils.env('COPY_LOGS')
        user_domain_id = cliutils.env('OS_USER_DOMAIN_ID')
        project_domain_id = cliutils.env('OS_PROJECT_DOMAIN_ID')

        config = configparser.RawConfigParser()
        if config.read('functional_creds.conf'):
            # the OR pattern means the environment is preferred for
            # override
            user = user or config.get('admin', 'user')
            passwd = passwd or config.get('admin', 'pass')
            project_name = project_name or config.get('admin', 'project_name')
            auth_url = auth_url or config.get('auth', 'auth_url')
            insecure = insecure or config.get('auth', 'insecure')
            magnum_url = magnum_url or config.get('auth', 'magnum_url')
            image_id = image_id or config.get('magnum', 'image_id')
            nic_id = nic_id or config.get('magnum', 'nic_id')
            flavor_id = flavor_id or config.get('magnum', 'flavor_id')
            master_flavor_id = master_flavor_id or config.get(
                'magnum', 'master_flavor_id')
            keypair_id = keypair_id or config.get('magnum', 'keypair_id')
            dns_nameserver = dns_nameserver or config.get(
                'magnum', 'dns_nameserver')
            user_domain_id = user_domain_id or config.get(
                'admin', 'user_domain_id')
            project_domain_id = project_domain_id or config.get(
                'admin', 'project_domain_id')

            try:
                copy_logs = copy_logs or config.get('magnum', 'copy_logs')
            except configparser.NoOptionError:
                pass

        cls.image_id = image_id
        cls.nic_id = nic_id
        cls.flavor_id = flavor_id
        cls.master_flavor_id = master_flavor_id
        cls.keypair_id = keypair_id
        cls.dns_nameserver = dns_nameserver
        cls.copy_logs = str(copy_logs).lower() == 'true'

        # NOTE(clenimar): The recommended way to issue clients is by creating
        # a keystoneauth Session. Using auth parameters (e.g. username and
        # password) directly is deprecated.
        _session = cls._get_auth_session(username=user,
                                         password=passwd,
                                         project_name=project_name,
                                         project_domain_id=project_domain_id,
                                         user_domain_id=user_domain_id,
                                         auth_url=auth_url,
                                         insecure=insecure)

        cls.cs = v1client.Client(session=_session,
                                 insecure=insecure,
                                 service_type='container-infra',
                                 region_name=region_name,
                                 magnum_url=magnum_url,
                                 api_version='latest')

        cls.keystone = ksclient.Client(session=_session)

        # Get heat endpoint from session
        auth_ref = _session.auth.get_auth_ref(_session)
        heat_endpoint = auth_ref.service_catalog.url_for(
            service_type='orchestration')

        cls.heat = heatclient.Client('1', session=_session,
                                     auth=_session.auth,
                                     endpoint=heat_endpoint)

    @classmethod
    def _get_auth_session(cls, username, password, project_name,
                          project_domain_id, user_domain_id, auth_url,
                          insecure):
        """Return a `keystoneauth1.session.Session` from auth parameters."""
        # create v3Password auth plugin
        _auth = ksa_v3.Password(username=username,
                                password=password,
                                project_name=project_name,
                                project_domain_id=project_domain_id,
                                user_domain_id=user_domain_id,
                                auth_url=auth_url)

        # `insecure` is being replaced by `verify`. Please note they have
        # opposite meanings.
        verify = False if insecure else True

        # create a `keystoneauth1.session.Session`
        _session = ksa_session.Session(auth=_auth, verify=verify)

        return _session

    @classmethod
    def _wait_on_status(cls, cluster, wait_status, finish_status,
                        timeout=6000):
        # Check status every 60 seconds for a total of 100 minutes

        def _check_status():
            status = cls.cs.clusters.get(cluster.uuid).status
            cls.LOG.debug("Cluster status is %s", status)
            if status in wait_status:
                return False
            elif status in finish_status:
                return True
            else:
                raise Exception("Unexpected Status: %s" % status)

        # sleep 1s to wait cluster status changes, this will be useful for
        # the first time we wait for the status, to avoid another 59s
        time.sleep(1)
        utils.wait_for_condition(_check_status, interval=60, timeout=timeout)

    @classmethod
    def _create_cluster_template(cls, name, **kwargs):
        # TODO(eliqiao): We don't want these to be have default values,
        #                just leave them here to make things work.
        #                Plan is to support other kinds of ClusterTemplate
        #                creation.
        coe = kwargs.pop('coe', 'kubernetes')
        network_driver = kwargs.pop('network_driver', 'flannel')
        volume_driver = kwargs.pop('volume_driver', 'cinder')
        labels = kwargs.pop('labels', {"K1": "V1", "K2": "V2"})
        tls_disabled = kwargs.pop('tls_disabled', False)
        fixed_subnet = kwargs.pop('fixed_subnet', None)
        server_type = kwargs.pop('server_type', 'vm')

        cluster_template = cls.cs.cluster_templates.create(
            name=name,
            keypair_id=cls.keypair_id,
            external_network_id=cls.nic_id,
            image_id=cls.image_id,
            flavor_id=cls.flavor_id,
            master_flavor_id=cls.master_flavor_id,
            network_driver=network_driver,
            volume_driver=volume_driver,
            dns_nameserver=cls.dns_nameserver,
            coe=coe,
            labels=labels,
            tls_disabled=tls_disabled,
            fixed_subnet=fixed_subnet,
            server_type=server_type,
            **kwargs)
        return cluster_template

    @classmethod
    def _create_cluster(cls, name, cluster_template_uuid):
        cluster = cls.cs.clusters.create(
            name=name,
            cluster_template_id=cluster_template_uuid
        )

        return cluster

    @classmethod
    def _show_cluster(cls, name):
        cluster = cls.cs.clusters.get(name)
        return cluster

    @classmethod
    def _delete_cluster_template(cls, cluster_template_uuid):
        cls.cs.cluster_templates.delete(cluster_template_uuid)

    @classmethod
    def _delete_cluster(cls, cluster_uuid):
        cls.cs.clusters.delete(cluster_uuid)

        try:
            cls._wait_on_status(
                cls.cluster,
                ["CREATE_COMPLETE", "DELETE_IN_PROGRESS", "CREATE_FAILED"],
                ["DELETE_FAILED", "DELETE_COMPLETE"],
                timeout=600
            )
        except exceptions.NotFound:
            pass
        else:
            if cls._show_cluster(cls.cluster.uuid).status == 'DELETE_FAILED':
                raise Exception("Cluster %s delete failed" % cls.cluster.uuid)

    @classmethod
    def get_copy_logs(cls):
        return cls.copy_logs

    def _wait_for_cluster_complete(self, cluster):
        self._wait_on_status(
            cluster,
            [None, "CREATE_IN_PROGRESS"],
            ["CREATE_FAILED", "CREATE_COMPLETE"],
            timeout=self.cluster_complete_timeout
        )

        if self.cs.clusters.get(cluster.uuid).status == 'CREATE_FAILED':
            raise Exception("Cluster %s create failed" % cluster.uuid)

        return cluster


class ClusterTest(BaseMagnumClient):

    # NOTE (eliqiao) coe should be specified in subclasses
    coe = None
    cluster_template_kwargs = {}
    config_contents = """[req]
distinguished_name = req_distinguished_name
req_extensions     = req_ext
prompt = no
[req_distinguished_name]
CN = admin
O = system:masters
OU=OpenStack/Magnum
C=US
ST=TX
L=Austin
[req_ext]
extendedKeyUsage = clientAuth
"""

    ca_dir = None
    cluster = None
    cluster_template = None
    key_file = None
    cert_file = None
    ca_file = None

    cluster_complete_timeout = 1800

    @classmethod
    def setUpClass(cls):
        super(ClusterTest, cls).setUpClass()
        cls.cluster_template = cls._create_cluster_template(
            cls.__name__, coe=cls.coe, **cls.cluster_template_kwargs)
        cls.cluster = cls._create_cluster(cls.__name__,
                                          cls.cluster_template.uuid)
        if not cls.cluster_template_kwargs.get('tls_disabled', False):
            # NOTE (wangbo) with multiple mangum-conductor processes, client
            # ca files should be created after completion of cluster ca_cert
            try:
                cls._wait_on_status(
                    cls.cluster,
                    [None, "CREATE_IN_PROGRESS"],
                    ["CREATE_FAILED", "CREATE_COMPLETE"],
                    timeout=cls.cluster_complete_timeout
                )
            except Exception:
                # copy logs if setUpClass fails, may be this will not work
                # as master_address, node_address would not be available, if
                # not we can get that from nova
                if cls.copy_logs:
                    cls.copy_logs_handler(
                        cls._get_nodes,
                        cls.cluster_template.coe,
                        'default')
            cls._create_tls_ca_files(cls.config_contents)

    @classmethod
    def tearDownClass(cls):
        if cls.ca_dir:
            rmtree_without_raise(cls.ca_dir)
        if cls.cluster:
            cls._delete_cluster(cls.cluster.uuid)
        if cls.cluster_template:
            cls._delete_cluster_template(cls.cluster_template.uuid)
        super(ClusterTest, cls).tearDownClass()

    def setUp(self):
        super(ClusterTest, self).setUp()

        test_timeout = os.environ.get('OS_TEST_TIMEOUT', 60)
        try:
            test_timeout = int(test_timeout)
        except ValueError:
            # If timeout value is invalid, set a default timeout.
            test_timeout = CONF.cluster_heat.create_timeout
        if test_timeout <= 0:
            test_timeout = CONF.cluster_heat.create_timeout

        self.useFixture(fixtures.Timeout(test_timeout, gentle=True))

        # Copy cluster nodes logs
        if self.copy_logs:
            self.addCleanup(
                self.copy_logs_handler(
                    self._get_nodes,
                    self.cluster_template.coe,
                    'default'))
        self._wait_for_cluster_complete(self.cluster)

    def _get_nodes(self):
        nodes = self._get_nodes_from_cluster()
        if not [x for x in nodes if x]:
            self.LOG.info("the list of nodes from cluster is empty")
            nodes = self._get_nodes_from_stack()
            if not [x for x in nodes if x]:
                self.LOG.info("the list of nodes from stack is empty")
        self.LOG.info("Nodes are: %s", nodes)
        return nodes

    def _get_nodes_from_cluster(self):
        nodes = []
        nodes.append(self.cs.clusters.get(self.cluster.uuid).master_addresses)
        nodes.append(self.cs.clusters.get(self.cluster.uuid).node_addresses)
        return nodes

    def _get_nodes_from_stack(self):
        cluster = self.cs.clusters.get(self.cluster.uuid)
        nodes = []
        stack = self.heat.stacks.get(cluster.stack_id)
        stack_outputs = stack.to_dict().get('outputs', [])
        output_keys = []
        if self.cluster_template.coe == "kubernetes":
            output_keys = ["kube_masters", "kube_minions"]
        elif self.cluster_template.coe == "swarm":
            output_keys = ["swarm_masters", "swarm_nodes"]
        elif self.cluster_template.coe == "swarm-mode":
            output_keys = ["swarm_primary_master",
                           "swarm_secondary_masters",
                           "swarm_nodes"]

        for output in stack_outputs:
            for key in output_keys:
                if output['output_key'] == key:
                    nodes.append(output['output_value'])
        return nodes

    @classmethod
    def _create_tls_ca_files(cls, client_conf_contents):
        """Creates ca files by client_conf_contents."""

        cls.ca_dir = tempfile.mkdtemp()
        cls.csr_file = '%s/client.csr' % cls.ca_dir
        cls.client_config_file = '%s/client.conf' % cls.ca_dir

        cls.key_file = '%s/client.key' % cls.ca_dir
        cls.cert_file = '%s/client.crt' % cls.ca_dir
        cls.ca_file = '%s/ca.crt' % cls.ca_dir

        with open(cls.client_config_file, 'w') as f:
            f.write(client_conf_contents)

        def _write_client_key():
            subprocess.call(['openssl', 'genrsa',
                             '-out', cls.key_file,
                             '4096'])

        def _create_client_csr():
            subprocess.call(['openssl', 'req', '-new',
                             '-days', '365',
                             '-key', cls.key_file,
                             '-out', cls.csr_file,
                             '-config', cls.client_config_file])

        _write_client_key()
        _create_client_csr()

        with open(cls.csr_file, 'r') as f:
            csr_content = f.read()

        # magnum ca-sign --cluster secure-k8scluster --csr client.csr \
        # > client.crt
        resp = cls.cs.certificates.create(cluster_uuid=cls.cluster.uuid,
                                          csr=csr_content)

        with open(cls.cert_file, 'w') as f:
            f.write(resp.pem)

        # magnum ca-show --cluster secure-k8scluster > ca.crt
        resp = cls.cs.certificates.get(cls.cluster.uuid)

        with open(cls.ca_file, 'w') as f:
            f.write(resp.pem)


class BaseK8sTest(ClusterTest):
    coe = 'kubernetes'

    @classmethod
    def setUpClass(cls):
        super(BaseK8sTest, cls).setUpClass()
        cls.kube_api_url = cls.cs.clusters.get(cls.cluster.uuid).api_address
        config = k8s_config.Configuration()
        config.host = cls.kube_api_url
        config.ssl_ca_cert = cls.ca_file
        config.cert_file = cls.cert_file
        config.key_file = cls.key_file
        k8s_client = api_client.ApiClient(configuration=config)
        cls.k8s_api = core_v1_api.CoreV1Api(k8s_client)

    def setUp(self):
        super(BaseK8sTest, self).setUp()
        self.kube_api_url = self.cs.clusters.get(self.cluster.uuid).api_address
        config = k8s_config.Configuration()
        config.host = self.kube_api_url
        config.ssl_ca_cert = self.ca_file
        config.cert_file = self.cert_file
        config.key_file = self.key_file
        k8s_client = api_client.ApiClient(configuration=config)
        self.k8s_api = core_v1_api.CoreV1Api(k8s_client)
        # TODO(coreypobrien) https://bugs.launchpad.net/magnum/+bug/1551824
        utils.wait_for_condition(self._is_api_ready, 5, 600)

    def _is_api_ready(self):
        try:
            self.k8s_api.list_node()
            self.LOG.info("API is ready.")
            return True
        except Exception:
            self.LOG.info("API is not ready yet.")
            return False

    def test_pod_apis(self):
        pod_manifest = {'apiVersion': 'v1',
                        'kind': 'Pod',
                        'metadata': {'color': 'blue', 'name': 'test'},
                        'spec': {'containers': [{'image': 'dockerfile/redis',
                                 'name': 'redis'}]}}

        resp = self.k8s_api.create_namespaced_pod(body=pod_manifest,
                                                  namespace='default')
        self.assertEqual('test', resp.metadata.name)
        self.assertTrue(resp.status.phase)

        resp = self.k8s_api.read_namespaced_pod(name='test',
                                                namespace='default')
        self.assertEqual('test', resp.metadata.name)
        self.assertTrue(resp.status.phase)

        resp = self.k8s_api.delete_namespaced_pod(name='test', body={},
                                                  namespace='default')

    def test_service_apis(self):
        service_manifest = {'apiVersion': 'v1',
                            'kind': 'Service',
                            'metadata': {'labels': {'name': 'frontend'},
                                         'name': 'frontend',
                                         'resourceversion': 'v1'},
                            'spec': {'ports': [{'port': 80,
                                                'protocol': 'TCP',
                                                'targetPort': 80}],
                                     'selector': {'name': 'frontend'}}}

        resp = self.k8s_api.create_namespaced_service(body=service_manifest,
                                                      namespace='default')
        self.assertEqual('frontend', resp.metadata.name)
        self.assertTrue(resp.status)

        resp = self.k8s_api.read_namespaced_service(name='frontend',
                                                    namespace='default')
        self.assertEqual('frontend', resp.metadata.name)
        self.assertTrue(resp.status)

        resp = self.k8s_api.delete_namespaced_service(name='frontend', body={},
                                                      namespace='default')

    def test_replication_controller_apis(self):
        rc_manifest = {
            'apiVersion': 'v1',
            'kind': 'ReplicationController',
            'metadata': {'labels': {'name': 'frontend'},
                         'name': 'frontend'},
            'spec': {'replicas': 2,
                     'selector': {'name': 'frontend'},
                     'template': {'metadata': {
                         'labels': {'name': 'frontend'}},
                         'spec': {'containers': [{
                             'image': 'nginx',
                             'name': 'nginx',
                             'ports': [{'containerPort': 80,
                                        'protocol': 'TCP'}]}]}}}}

        resp = self.k8s_api.create_namespaced_replication_controller(
            body=rc_manifest, namespace='default')
        self.assertEqual('frontend', resp.metadata.name)
        self.assertEqual(2, resp.spec.replicas)

        resp = self.k8s_api.read_namespaced_replication_controller(
            name='frontend', namespace='default')
        self.assertEqual('frontend', resp.metadata.name)
        self.assertEqual(2, resp.spec.replicas)

        resp = self.k8s_api.delete_namespaced_replication_controller(
            name='frontend', body={}, namespace='default')
