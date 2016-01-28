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
from magnum.tests import base
from magnumclient.openstack.common.apiclient import exceptions
from magnumclient.openstack.common import cliutils
from magnumclient.v1 import client as v1client


class BaseMagnumClient(base.TestCase):

    @classmethod
    def setUpClass(cls):
        # Collecting of credentials:
        #
        # Support the existence of a functional_creds.conf for
        # testing. This makes it possible to use a config file.
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
        keypair_id = cliutils.env('KEYPAIR_ID')
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
            keypair_id = keypair_id or config.get('magnum', 'keypair_id')
            try:
                copy_logs = copy_logs or config.get('magnum', 'copy_logs')
            except configparser.NoOptionError:
                pass

        cls.image_id = image_id
        cls.nic_id = nic_id
        cls.flavor_id = flavor_id
        cls.keypair_id = keypair_id
        cls.copy_logs = bool(copy_logs)
        cls.cs = v1client.Client(username=user,
                                 api_key=passwd,
                                 project_id=tenant_id,
                                 project_name=tenant,
                                 auth_url=auth_url,
                                 service_type='container',
                                 region_name=region_name,
                                 magnum_url=magnum_url)

    @classmethod
    def _wait_on_status(cls, bay, wait_status, finish_status):
        # Check status every 60 seconds for a total of 100 minutes
        for i in range(100):
            # sleep 1s to wait bay status changes, this will be useful for
            # the first time we wait for the status, to avoid another 59s
            time.sleep(1)
            status = cls.cs.bays.get(bay.uuid).status
            if status in wait_status:
                time.sleep(59)
            elif status in finish_status:
                break
            else:
                raise Exception("Unknown Status : %s" % status)

    @classmethod
    def _create_baymodel(cls, name, **kwargs):
        # TODO(eliqiao): We don't want these to be have default values,
        #                just leave them here to make things work.
        #                Plan is to support other kinds of baymodel creation.
        coe = kwargs.pop('coe', 'kubernetes')
        docker_volume_size = kwargs.pop('docker_volume_size', 3)
        network_driver = kwargs.pop('network_driver', 'flannel')
        labels = kwargs.pop('labels', {"K1": "V1", "K2": "V2"})
        tls_disabled = kwargs.pop('tls_disabled', False)

        baymodel = cls.cs.baymodels.create(
            name=name,
            keypair_id=cls.keypair_id,
            external_network_id=cls.nic_id,
            image_id=cls.image_id,
            flavor_id=cls.flavor_id,
            master_flavor_id=cls.flavor_id,
            docker_volume_size=docker_volume_size,
            network_driver=network_driver,
            coe=coe,
            labels=labels,
            tls_disabled=tls_disabled,
            **kwargs)
        return baymodel

    @classmethod
    def _create_bay(cls, name, baymodel_uuid, wait=True):
        bay = cls.cs.bays.create(
            name=name,
            baymodel_id=baymodel_uuid,
            node_count=None,
        )

        if wait:
            cls._wait_on_status(bay,
                                [None, "CREATE_IN_PROGRESS"],
                                ["CREATE_FAILED",
                                 "CREATE_COMPLETE"])

        if cls.cs.bays.get(bay.uuid).status == 'CREATE_FAILED':
            raise Exception("bay %s created failed" % bay.uuid)

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

    def _copy_logs(self, exec_info):
        if not self.copy_logs:
            return
        fn = exec_info[2].tb_frame.f_locals['fn']
        func_name = fn.im_self._get_test_method().__name__

        bay = self._show_bay(self.bay.uuid)
        for node_addr in bay.node_addresses:
            subprocess.call(["magnum/tests/contrib/copy_instance_logs.sh",
                             node_addr, self.baymodel.coe,
                             "worker-" + func_name])
        for node_addr in getattr(bay, 'master_addresses', []):
            subprocess.call(["magnum/tests/contrib/copy_instance_logs.sh",
                             node_addr, self.baymodel.coe,
                             "master-" + func_name])


class BayTest(BaseMagnumClient):

    # NOTE (eliqiao) coe should be specified in subclasses
    coe = None

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

    def _test_baymodel_create_and_delete(self, baymodel_name,
                                         delete=True, **kwargs):
        baymodel = self._create_baymodel(baymodel_name, coe=self.coe, **kwargs)
        list = [item.uuid for item in self.cs.baymodels.list()]
        self.assertIn(baymodel.uuid, list)

        if not delete:
            return baymodel
        else:
            self.cs.baymodels.delete(baymodel.uuid)
            list = [item.uuid for item in self.cs.baymodels.list()]
            self.assertNotIn(baymodel.uuid, list)

    def _test_bay_create_and_delete(self, bay_name, baymodel):
        # NOTE(eliqiao): baymodel will be deleted after this testing
        bay = self._create_bay(bay_name, baymodel.uuid)
        list = [item.uuid for item in self.cs.bays.list()]
        self.assertIn(bay.uuid, list)

        try:
            self.assertIn(self.cs.bays.get(bay.uuid).status,
                          ["CREATED", "CREATE_COMPLETE"])
        finally:
            # Ensure we delete whether the assert above is true or false
            self.cs.bays.delete(bay.uuid)

            try:
                self._wait_on_status(bay,
                                     ["CREATE_COMPLETE",
                                      "DELETE_IN_PROGRESS", "CREATE_FAILED"],
                                     ["DELETE_FAILED",
                                      "DELETE_COMPLETE"])
            except exceptions.NotFound:
                # if bay/get fails, the bay has been deleted already
                pass

            try:
                self.cs.baymodels.delete(baymodel.uuid)
            except exceptions.BadRequest:
                pass


class BayAPITLSTest(BaseMagnumClient):
    """Base class of TLS enabled test case."""

    def setUp(self):
        super(BayAPITLSTest, self).setUp()
        self.addOnException(self._copy_logs)

    @classmethod
    def tearDownClass(cls):

        if cls.ca_dir:
            rmtree_without_raise(cls.ca_dir)

        cls._delete_bay(cls.bay.uuid)
        try:
            cls._wait_on_status(cls.bay,
                                ["CREATE_COMPLETE",
                                 "DELETE_IN_PROGRESS", "CREATE_FAILED"],
                                ["DELETE_FAILED", "DELETE_COMPLETE"])
        except exceptions.NotFound:
            pass
        cls._delete_baymodel(cls.baymodel.uuid)

        super(BayAPITLSTest, cls).tearDownClass()

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
