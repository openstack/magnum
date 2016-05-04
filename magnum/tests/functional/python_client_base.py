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
                                 service_type='container',
                                 region_name=region_name,
                                 magnum_url=magnum_url)

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
                lambda: list([self.cs.bays.get(self.bay.uuid).master_addresses,
                             self.cs.bays.get(self.bay.uuid).node_addresses]),
                self.baymodel.coe,
                'default'))
        self._wait_for_bay_complete(self.bay)

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
