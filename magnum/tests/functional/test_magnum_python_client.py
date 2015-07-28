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

from magnum.common.pythonk8sclient.client import ApivbetaApi
from magnum.common.pythonk8sclient.client import swagger
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

        cls.image_id = image_id
        cls.nic_id = nic_id
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
        # Check status every 5 seconds for a total of 120 minutes
        for i in range(100):
            status = cls.cs.bays.get(bay.uuid).status
            if status in wait_status:
                time.sleep(60)
            elif status in finish_status:
                break
            else:
                raise Exception("Unknown Status : %s" % status)

    @classmethod
    def _create_baymodel(cls, name):
        baymodel = cls.cs.baymodels.create(
            name=name,
            keypair_id='default',
            external_network_id=cls.nic_id,
            image_id=cls.image_id,
            flavor_id='m1.small',
            docker_volume_size=5,
            coe='kubernetes',
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
        baymodel = self._create_baymodel('testbaymodel')
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

        self.baymodel = self._create_baymodel('testbay')

        def delete_baymodel():
            try:
                self.cs.baymodels.delete(self.baymodel.uuid)
            except exceptions.BadRequest:
                pass

        self.addCleanup(delete_baymodel)

    def test_bay_create_and_delete(self):
        bay = self._create_bay('testbay', self.baymodel.uuid)
        list = [item.uuid for item in self.cs.bays.list()]
        self.assertTrue(bay.uuid in list)

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
                                 ["DELETE_FAILED", "CREATE_FAILED",
                                  "DELETE_COMPLETE"])
        except exceptions.NotFound:
            # if bay/get fails, the bay has been deleted already
            pass


class TestKubernetesAPIs(BaseMagnumClient):
    @classmethod
    def setUpClass(cls):
        super(TestKubernetesAPIs, cls).setUpClass()
        cls.baymodel = cls._create_baymodel('testk8sAPI')
        cls.bay = cls._create_bay('testk8sAPI', cls.baymodel.uuid)
        kube_api_address = cls.cs.bays.get(cls.bay.uuid).api_address
        kube_api_url = 'http://%s' % kube_api_address
        k8s_client = swagger.ApiClient(kube_api_url)
        cls.k8s_api = ApivbetaApi.ApivbetaApi(k8s_client)

    @classmethod
    def tearDownClass(cls):
        cls._delete_bay(cls.bay.uuid)
        try:
            cls._wait_on_status(cls.bay,
                                ["CREATE_COMPLETE",
                                 "DELETE_IN_PROGRESS"],
                                ["DELETE_FAILED", "CREATE_FAILED",
                                 "DELETE_COMPLETE"])
        except exceptions.NotFound:
            pass
        cls._delete_baymodel(cls.baymodel.uuid)

    def test_pod_apis(self):
        pod_manifest = {'apiVersion': 'v1beta3',
                        'kind': 'Pod',
                        'metadata': {'color': 'blue', 'name': 'test'},
                        'spec': {'containers': [{'image': 'dockerfile/redis',
                                 'name': 'redis'}]}}

        resp = self.k8s_api.createPod(body=pod_manifest, namespaces='default')
        self.assertEqual(resp.metadata['name'], 'test')
        self.assertTrue(resp.status.phase)

        resp = self.k8s_api.readPod(name='test', namespaces='default')
        self.assertEqual(resp.metadata['name'], 'test')
        self.assertTrue(resp.status.phase)

        resp = self.k8s_api.deletePod(name='test', namespaces='default')
        self.assertFalse(resp.phase)

    def test_service_apis(self):
        service_manifest = {'apiVersion': 'v1beta3',
                            'kind': 'Service',
                            'metadata': {'labels': {'name': 'frontend'},
                                         'name': 'frontend',
                                         'resourceversion': 'v1beta3'},
                            'spec': {'ports': [{'port': 80,
                                                'protocol': 'TCP',
                                                'targetPort': 80}],
                                     'selector': {'name': 'frontend'}}}

        resp = self.k8s_api.createService(body=service_manifest,
                                          namespaces='default')
        self.assertEqual(resp.metadata['name'], 'frontend')
        self.assertTrue(resp.status)

        resp = self.k8s_api.readService(name='frontend', namespaces='default')
        self.assertEqual(resp.metadata['name'], 'frontend')
        self.assertTrue(resp.status)

        resp = self.k8s_api.deleteService(name='frontend',
                                          namespaces='default')
        # TODO(madhuri) Currently the V1beta3_ServiceStatus
        # has no attribute defined. Uncomment this assertion
        # when the class is redefined to contain 'phase'.
        # self.assertTrue(resp.phase)

    def test_replication_controller_apis(self):
        rc_manifest = {
            'apiVersion': 'v1beta3',
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

        resp = self.k8s_api.createReplicationController(body=rc_manifest,
                                                        namespaces='default')
        self.assertEqual(resp.metadata['name'], 'frontend')
        self.assertEqual(resp.spec.replicas, 2)

        resp = self.k8s_api.readReplicationController(name='frontend',
                                                      namespaces='default')
        self.assertEqual(resp.metadata['name'], 'frontend')
        self.assertEqual(resp.spec.replicas, 2)

        resp = self.k8s_api.deleteReplicationController(name='frontend',
                                                        namespaces='default')
        self.assertFalse(resp.replicas)
