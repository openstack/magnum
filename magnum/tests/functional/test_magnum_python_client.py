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
        self.cs = client.Client(username=cliutils.env('OS_USERNAME'),
                                api_key=cliutils.env('OS_PASSWORD'),
                                project_id=cliutils.env('OS_TENANT_ID'),
                                project_name=cliutils.env('OS_TENANT_NAME'),
                                auth_url=cliutils.env('OS_AUTH_URL'),
                                service_type='container',
                                region_name=cliutils.env('OS_REGION_NAME'),
                                magnum_url=cliutils.env('BYPASS_URL'))


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
            external_network_id=cliutils.env('NIC_ID'),
            image_id=cliutils.env('IMAGE_ID'),
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
            external_network_id=cliutils.env('NIC_ID'),
            image_id=cliutils.env('IMAGE_ID'),
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
