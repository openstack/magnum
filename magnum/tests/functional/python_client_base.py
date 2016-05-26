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
from k8sclient.client import api_client
from k8sclient.client.apis import apiv_api
from keystoneclient.v2_0 import client as ksclient
from magnum.common.utils import rmtree_without_raise
from magnum.tests.functional.common import base
from magnum.tests.functional.common import utils
from magnumclient.common.apiclient import exceptions
from magnumclient.common import cliutils
from magnumclient.v1 import client as v1client


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
        tenant = cliutils.env('OS_TENANT_NAME')
        tenant_id = cliutils.env('OS_TENANT_ID')
        auth_url = cliutils.env('OS_AUTH_URL')
        region_name = cliutils.env('OS_REGION_NAME')
        magnum_url = cliutils.env('BYPASS_URL')
        image_id = cliutils.env('IMAGE_ID')
        nic_id = cliutils.env('NIC_ID')
        flavor_id = cliutils.env('FLAVOR_ID')
        master_flavor_id = cliutils.env('MASTER_FLAVOR_ID')
        keypair_id = cliutils.env('KEYPAIR_ID')
        dns_nameserver = cliutils.env('DNS_NAMESERVER')
        copy_logs = cliutils.env('COPY_LOGS')

        config = configparser.RawConfigParser()
        if config.read('functional_creds.conf'):
            # the OR pattern means the environment is preferred for
            # override
            user = user or config.get('admin', 'user')
            passwd = passwd or config.get('admin', 'pass')
            tenant = tenant or config.get('admin', 'tenant')
            auth_url = auth_url or config.get('auth', 'auth_url')
            magnum_url = magnum_url or config.get('auth', 'magnum_url')
            image_id = image_id or config.get('magnum', 'image_id')
            nic_id = nic_id or config.get('magnum', 'nic_id')
            flavor_id = flavor_id or config.get('magnum', 'flavor_id')
            master_flavor_id = master_flavor_id or config.get(
                'magnum', 'master_flavor_id')
            keypair_id = keypair_id or config.get('magnum', 'keypair_id')
            dns_nameserver = dns_nameserver or config.get(
                'magnum', 'dns_nameserver')
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
        cls.cs = v1client.Client(username=user,
                                 api_key=passwd,
                                 project_id=tenant_id,
                                 project_name=tenant,
                                 auth_url=auth_url,
                                 service_type='container-infra',
                                 region_name=region_name,
                                 magnum_url=magnum_url)
        cls.keystone = ksclient.Client(username=user,
                                       password=passwd,
                                       tenant_name=tenant,
                                       auth_url=auth_url)
        token = cls.keystone.auth_token
        heat_endpoint = cls.keystone.service_catalog.url_for(
            service_type='orchestration')
        cls.heat = heatclient.Client('1', token=token, endpoint=heat_endpoint)

    @classmethod
    def _wait_on_status(cls, bay, wait_status, finish_status, timeout=6000):
        # Check status every 60 seconds for a total of 100 minutes

        def _check_status():
            status = cls.cs.bays.get(bay.uuid).status
            cls.LOG.debug("Bay status is %s" % status)
            if status in wait_status:
                return False
            elif status in finish_status:
                return True
            else:
                raise Exception("Unexpected Status: %s" % status)

        # sleep 1s to wait bay status changes, this will be useful for
        # the first time we wait for the status, to avoid another 59s
        time.sleep(1)
        utils.wait_for_condition(_check_status, interval=60, timeout=timeout)

    @classmethod
    def _create_baymodel(cls, name, **kwargs):
        # TODO(eliqiao): We don't want these to be have default values,
        #                just leave them here to make things work.
        #                Plan is to support other kinds of baymodel creation.
        coe = kwargs.pop('coe', 'kubernetes')
        docker_volume_size = kwargs.pop('docker_volume_size', 3)
        network_driver = kwargs.pop('network_driver', 'flannel')
        volume_driver = kwargs.pop('volume_driver', 'cinder')
        labels = kwargs.pop('labels', {"K1": "V1", "K2": "V2"})
        tls_disabled = kwargs.pop('tls_disabled', False)

        baymodel = cls.cs.baymodels.create(
            name=name,
            keypair_id=cls.keypair_id,
            external_network_id=cls.nic_id,
            image_id=cls.image_id,
            flavor_id=cls.flavor_id,
            master_flavor_id=cls.master_flavor_id,
            docker_volume_size=docker_volume_size,
            network_driver=network_driver,
            volume_driver=volume_driver,
            dns_nameserver=cls.dns_nameserver,
            coe=coe,
            labels=labels,
            tls_disabled=tls_disabled,
            **kwargs)
        return baymodel

    @classmethod
    def _create_bay(cls, name, baymodel_uuid):
        bay = cls.cs.bays.create(
            name=name,
            baymodel_id=baymodel_uuid
        )

        return bay

    @classmethod
    def _show_bay(cls, name):
        bay = cls.cs.bays.get(name)
        return bay

    @classmethod
    def _delete_baymodel(cls, baymodel_uuid):
        cls.cs.baymodels.delete(baymodel_uuid)

    @classmethod
    def _delete_bay(cls, bay_uuid):
        cls.cs.bays.delete(bay_uuid)

        try:
            cls._wait_on_status(
                cls.bay,
                ["CREATE_COMPLETE", "DELETE_IN_PROGRESS", "CREATE_FAILED"],
                ["DELETE_FAILED", "DELETE_COMPLETE"],
                timeout=600
            )
        except exceptions.NotFound:
            pass
        else:
            if cls._show_bay(cls.bay.uuid).status == 'DELETE_FAILED':
                raise Exception("bay %s delete failed" % cls.bay.uuid)

    @classmethod
    def get_copy_logs(cls):
        return cls.copy_logs

    def _wait_for_bay_complete(self, bay):
        self._wait_on_status(
            bay,
            [None, "CREATE_IN_PROGRESS"],
            ["CREATE_FAILED", "CREATE_COMPLETE"],
            timeout=1800
        )

        if self.cs.bays.get(bay.uuid).status == 'CREATE_FAILED':
            raise Exception("bay %s created failed" % bay.uuid)

        return bay


class BayTest(BaseMagnumClient):

    # NOTE (eliqiao) coe should be specified in subclasses
    coe = None
    baymodel_kwargs = {}
    config_contents = """[req]
distinguished_name = req_distinguished_name
req_extensions     = req_ext
prompt = no
[req_distinguished_name]
CN = Your Name
[req_ext]
extendedKeyUsage = clientAuth
"""

    ca_dir = None
    bay = None
    baymodel = None
    key_file = None
    cert_file = None
    ca_file = None

    @classmethod
    def setUpClass(cls):
        super(BayTest, cls).setUpClass()
        cls.baymodel = cls._create_baymodel(
            cls.__name__, coe=cls.coe, **cls.baymodel_kwargs)
        cls.bay = cls._create_bay(cls.__name__, cls.baymodel.uuid)
        if not cls.baymodel_kwargs.get('tls_disabled', False):
            cls._create_tls_ca_files(cls.config_contents)

    @classmethod
    def tearDownClass(cls):
        if cls.ca_dir:
            rmtree_without_raise(cls.ca_dir)
        if cls.bay:
            cls._delete_bay(cls.bay.uuid)
        if cls.baymodel:
            cls._delete_baymodel(cls.baymodel.uuid)
        super(BayTest, cls).tearDownClass()

    def setUp(self):
        super(BayTest, self).setUp()

        test_timeout = os.environ.get('OS_TEST_TIMEOUT', 0)
        try:
            test_timeout = int(test_timeout)
        except ValueError:
            # If timeout value is invalid do not set a timeout.
            test_timeout = 0
        if test_timeout > 0:
            self.useFixture(fixtures.Timeout(test_timeout, gentle=True))

        self.addOnException(
            self.copy_logs_handler(
                self._get_nodes,
                self.baymodel.coe,
                'default'))
        self._wait_for_bay_complete(self.bay)

    def _get_nodes(self):
        nodes = self._get_nodes_from_bay()
        if not nodes:
            self.LOG.info("the list of nodes from bay is empty")
            nodes = self._get_nodes_from_stack()
        return nodes

    def _get_nodes_from_bay(self):
        nodes = []
        nodes.append(self.cs.bays.get(self.bay.uuid).master_addresses)
        nodes.append(self.cs.bays.get(self.bay.uuid).node_addresses)
        return nodes

    def _get_nodes_from_stack(self):
        nodes = []
        stack = self.heat.stacks.get(self.bay.stack_id)
        stack_outputs = stack.to_dict().get('outputs', [])
        output_keys = []
        if self.baymodel.coe == "kubernetes":
            output_keys = ["kube_masters", "kube_minions"]
        elif self.baymodel.coe == "swarm":
            output_keys = ["swarm_masters", "swarm_nodes"]
        elif self.baymodel.coe == "mesos":
            output_keys = ["mesos_master", "mesos_slaves"]
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

        # magnum ca-sign --bay secure-k8sbay --csr client.csr > client.crt
        resp = cls.cs.certificates.create(bay_uuid=cls.bay.uuid,
                                          csr=csr_content)

        with open(cls.cert_file, 'w') as f:
            f.write(resp.pem)

        # magnum ca-show --bay secure-k8sbay > ca.crt
        resp = cls.cs.certificates.get(cls.bay.uuid)
        with open(cls.ca_file, 'w') as f:
            f.write(resp.pem)


class BaseK8sTest(BayTest):
    coe = 'kubernetes'

    @classmethod
    def setUpClass(cls):
        super(BaseK8sTest, cls).setUpClass()
        cls.kube_api_url = cls.cs.bays.get(cls.bay.uuid).api_address
        k8s_client = api_client.ApiClient(cls.kube_api_url,
                                          key_file=cls.key_file,
                                          cert_file=cls.cert_file,
                                          ca_certs=cls.ca_file)
        cls.k8s_api = apiv_api.ApivApi(k8s_client)

    def setUp(self):
        super(BaseK8sTest, self).setUp()
        self.kube_api_url = self.cs.bays.get(self.bay.uuid).api_address
        k8s_client = api_client.ApiClient(self.kube_api_url,
                                          key_file=self.key_file,
                                          cert_file=self.cert_file,
                                          ca_certs=self.ca_file)
        self.k8s_api = apiv_api.ApivApi(k8s_client)
        # TODO(coreypobrien) https://bugs.launchpad.net/magnum/+bug/1551824
        utils.wait_for_condition(self._is_api_ready, 5, 600)

    def _is_api_ready(self):
        try:
            self.k8s_api.list_namespaced_node()
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

        resp = self.k8s_api.delete_namespaced_service(name='frontend',
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
