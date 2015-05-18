# -*- coding: utf-8 -*-

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

from magnumclient.openstack.common.apiclient import exceptions
from magnumclient.openstack.common import cliutils
from magnumclient.v1 import client

from magnum.tests import base


class BaseMagnumClient(base.TestCase):
    def setUp(self):
        super(BaseMagnumClient, self).setUp()
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

        self.image_id = image_id
        self.nic_id = nic_id
        self.cs = client.Client(username=user,
                                api_key=passwd,
                                project_id=tenant_id,
                                project_name=tenant,
                                auth_url=auth_url,
                                service_type='container',
                                region_name=region_name,
                                magnum_url=magnum_url)


class TestListResources(BaseMagnumClient):
    def test_bay_model_list(self):
        self.assertTrue(self.cs.baymodels.list() is not None)

    def test_bay_list(self):
        self.assertTrue(self.cs.bays.list() is not None)

    def test_containers_list(self):
        self.assertTrue(self.cs.containers.list() is not None)

    def test_nodes_list(self):
        self.assertTrue(self.cs.nodes.list() is not None)

    def test_pods_list(self):
        self.assertTrue(self.cs.pods.list() is not None)

    def test_rcs_list(self):
        self.assertTrue(self.cs.rcs.list() is not None)

    def test_services_list(self):
        self.assertTrue(self.cs.services.list() is not None)


class TestBayModelResource(BaseMagnumClient):
    def test_bay_model_create_and_delete(self):
        baymodel = self.cs.baymodels.create(
            name='default',
            keypair_id='default',
            external_network_id=self.nic_id,
            image_id=self.image_id,
            flavor_id='m1.small',
            docker_volume_size=5,
            coe='kubernetes',
        )
        list = [item.uuid for item in self.cs.baymodels.list()]
        self.assertTrue(baymodel.uuid in list)

        self.cs.baymodels.delete(baymodel.uuid)
        list = [item.uuid for item in self.cs.baymodels.list()]
        self.assertTrue(baymodel.uuid not in list)


class TestBayResource(BaseMagnumClient):
    def setUp(self):
        super(TestBayResource, self).setUp()

        test_timeout = os.environ.get('OS_TEST_TIMEOUT', 0)
        try:
            test_timeout = int(test_timeout)
        except ValueError:
            # If timeout value is invalid do not set a timeout.
            test_timeout = 0
        if test_timeout > 0:
            self.useFixture(fixtures.Timeout(test_timeout, gentle=True))

        self.baymodel = self.cs.baymodels.create(
            name='default',
            keypair_id='default',
            external_network_id=self.nic_id,
            image_id=self.image_id,
            flavor_id='m1.small',
            docker_volume_size=5,
            coe='kubernetes',
        )

    def tearDown(self):
        super(TestBayResource, self).tearDown()
        try:
            self.cs.baymodels.delete(self.baymodel.uuid)
        except exceptions.BadRequest:
            pass

    def _wait_on_status(self, bay, wait_status, finish_status):
        # Check status every 5 seconds for a total of 120 minutes
        for i in range(100):
            status = self.cs.bays.get(bay.uuid).status
            if status in wait_status:
                time.sleep(60)
            elif status in finish_status:
                break
            else:
                self.assertTrue(False, "Unknown Status : %s" % status)

    def test_bay_create_and_delete(self):
        bay = self.cs.bays.create(
            name='k8s',
            baymodel_id=self.baymodel.uuid,
            node_count=None,
        )
        list = [item.uuid for item in self.cs.bays.list()]
        self.assertTrue(bay.uuid in list)

        self._wait_on_status(bay,
                             [None, "CREATE_IN_PROGRESS"],
                             ["CREATE_FAILED",
                              "CREATED",
                              "CREATE_COMPLETE"])
        try:
            self.assertIn(self.cs.bays.get(bay.uuid).status,
                          ["CREATED", "CREATE_COMPLETE"])
        finally:
            # Ensure we delete whether the assert above is true or false
            self.cs.bays.delete(bay.uuid)

        try:
            self._wait_on_status(bay,
                                 ["CREATE_COMPLETE",
                                  "DELETE_IN_PROGRESS"],
                                 ["DELETE_FAILED",
                                  "DELETED"])
        except exceptions.NotFound:
            # if bay/get fails, the bay has been deleted already
            pass
