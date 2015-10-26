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

import ConfigParser
import os
import time

import fixtures

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

        config = ConfigParser.RawConfigParser()
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

        cls.image_id = image_id
        cls.nic_id = nic_id
        cls.flavor_id = flavor_id
        cls.keypair_id = keypair_id
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
            # sleep 1s to wait bay status changes, this will be usefull for
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
    def _create_baymodel(cls, name, coe='kubernetes'):
        baymodel = cls.cs.baymodels.create(
            name=name,
            keypair_id=cls.keypair_id,
            external_network_id=cls.nic_id,
            image_id=cls.image_id,
            flavor_id=cls.flavor_id,
            docker_volume_size=1,
            network_driver='flannel',
            coe=coe,
            labels={"K1": "V1", "K2": "V2"},
            # TODO(yuanying): Change to `tls_disabled=False`
            #                 if k8sclient supports TLS.
            tls_disabled=True,
        )
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
        return bay

    @classmethod
    def _delete_baymodel(cls, baymodel_uuid):
        cls.cs.baymodels.delete(baymodel_uuid)

    @classmethod
    def _delete_bay(cls, bay_uuid):
        cls.cs.bays.delete(bay_uuid)


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

    def _test_baymodel_create_and_delete(self, delete=True):
        baymodel = self._create_baymodel('testbay', coe=self.coe)
        list = [item.uuid for item in self.cs.baymodels.list()]
        self.assertIn(baymodel.uuid, list)

        if not delete:
            return baymodel
        else:
            self.cs.baymodels.delete(baymodel.uuid)
            list = [item.uuid for item in self.cs.baymodels.list()]
            self.assertNotIn(baymodel.uuid, list)

    def _test_bay_create_and_delete(self):
        baymodel = self._test_baymodel_create_and_delete(delete=False)
        bay = self._create_bay('testbay', baymodel.uuid)
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
