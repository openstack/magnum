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

import fixtures

from oslo_log import log as logging
from oslo_utils import uuidutils
from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions
import testtools

from magnum.tests.functional.api import base
from magnum.tests.functional.common import config
from magnum.tests.functional.common import datagen


HEADERS = {'OpenStack-API-Version': 'container-infra latest',
           'Accept': 'application/json',
           'Content-Type': 'application/json'}


class ClusterTest(base.BaseTempestTest):

    """Tests for cluster CRUD."""

    LOG = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        super(ClusterTest, self).__init__(*args, **kwargs)
        self.clusters = []
        self.creds = None
        self.keypair = None
        self.cluster_template = None
        self.cluster_template_client = None
        self.keypairs_client = None
        self.cluster_client = None
        self.cert_client = None

    def setUp(self):
        try:
            super(ClusterTest, self).setUp()
            (self.creds, self.keypair) = self.get_credentials_with_keypair(
                type_of_creds='default')
            (self.cluster_template_client,
                self.keypairs_client) = self.get_clients_with_existing_creds(
                    creds=self.creds,
                    type_of_creds='default',
                    request_type='cluster_template')
            (self.cluster_client, _) = self.get_clients_with_existing_creds(
                creds=self.creds,
                type_of_creds='default',
                request_type='cluster')
            (self.cert_client, _) = self.get_clients_with_existing_creds(
                creds=self.creds,
                type_of_creds='default',
                request_type='cert')
            model = datagen.valid_swarm_mode_cluster_template()
            _, self.cluster_template = self._create_cluster_template(model)

            # NOTE (dimtruck) by default tempest sets timeout to 20 mins.
            # We need more time.
            test_timeout = 1800
            self.useFixture(fixtures.Timeout(test_timeout, gentle=True))
        except Exception:
            self.tearDown()
            raise

    def tearDown(self):
        try:
            cluster_list = self.clusters[:]
            for cluster_id in cluster_list:
                self._delete_cluster(cluster_id)
                self.clusters.remove(cluster_id)
            if self.cluster_template:
                self._delete_cluster_template(self.cluster_template.uuid)
        finally:
            super(ClusterTest, self).tearDown()

    def _create_cluster_template(self, cm_model):
        self.LOG.debug('We will create a clustertemplate for %s', cm_model)
        resp, model = self.cluster_template_client.post_cluster_template(
            cm_model)
        return resp, model

    def _delete_cluster_template(self, cm_id):
        self.LOG.debug('We will delete a clustertemplate for %s', cm_id)
        resp, model = self.cluster_template_client.delete_cluster_template(
            cm_id)
        return resp, model

    def _create_cluster(self, cluster_model):
        self.LOG.debug('We will create cluster for %s', cluster_model)
        resp, model = self.cluster_client.post_cluster(cluster_model)
        self.LOG.debug('Response: %s', resp)
        self.assertEqual(202, resp.status)
        self.assertIsNotNone(model.uuid)
        self.assertTrue(uuidutils.is_uuid_like(model.uuid))
        self.clusters.append(model.uuid)
        self.cluster_uuid = model.uuid
        if config.Config.copy_logs:
            self.addCleanup(self.copy_logs_handler(
                lambda: list(
                    [self._get_cluster_by_id(model.uuid)[1].master_addresses,
                     self._get_cluster_by_id(model.uuid)[1].node_addresses]),
                self.cluster_template.coe,
                self.keypair))
        self.cluster_client.wait_for_created_cluster(model.uuid,
                                                     delete_on_error=False)
        return resp, model

    def _delete_cluster(self, cluster_id):
        self.LOG.debug('We will delete a cluster for %s', cluster_id)
        resp, model = self.cluster_client.delete_cluster(cluster_id)
        self.assertEqual(204, resp.status)
        self.cluster_client.wait_for_cluster_to_delete(cluster_id)
        self.assertRaises(exceptions.NotFound, self.cert_client.get_cert,
                          cluster_id, headers=HEADERS)
        return resp, model

    def _get_cluster_by_id(self, cluster_id):
        resp, model = self.cluster_client.get_cluster(cluster_id)
        return resp, model

    # (dimtruck) Combining all these tests in one because
    # they time out on the gate (2 hours not enough)
    @testtools.testcase.attr('positive')
    def test_create_list_sign_delete_clusters(self):
        gen_model = datagen.valid_cluster_data(
            cluster_template_id=self.cluster_template.uuid, node_count=1)

        # test cluster create
        _, cluster_model = self._create_cluster(gen_model)
        self.assertNotIn('status', cluster_model)

        # test cluster list
        resp, cluster_list_model = self.cluster_client.list_clusters()
        self.assertEqual(200, resp.status)
        self.assertGreater(len(cluster_list_model.clusters), 0)
        self.assertIn(
            cluster_model.uuid, list([x['uuid']
                                      for x in cluster_list_model.clusters]))

        # test invalid cluster update
        patch_model = datagen.cluster_name_patch_data()
        self.assertRaises(
            exceptions.BadRequest,
            self.cluster_client.patch_cluster,
            cluster_model.uuid, patch_model)

        # test ca show
        resp, cert_model = self.cert_client.get_cert(
            cluster_model.uuid, headers=HEADERS)
        self.LOG.debug("cert resp: %s", resp)
        self.assertEqual(200, resp.status)
        self.assertEqual(cert_model.cluster_uuid, cluster_model.uuid)
        self.assertIsNotNone(cert_model.pem)
        self.assertIn('-----BEGIN CERTIFICATE-----', cert_model.pem)
        self.assertIn('-----END CERTIFICATE-----', cert_model.pem)

        # test ca sign

        csr_sample = """-----BEGIN CERTIFICATE REQUEST-----
MIIByjCCATMCAQAwgYkxCzAJBgNVBAYTAlVTMRMwEQYDVQQIEwpDYWxpZm9ybmlh
MRYwFAYDVQQHEw1Nb3VudGFpbiBWaWV3MRMwEQYDVQQKEwpHb29nbGUgSW5jMR8w
HQYDVQQLExZJbmZvcm1hdGlvbiBUZWNobm9sb2d5MRcwFQYDVQQDEw53d3cuZ29v
Z2xlLmNvbTCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEApZtYJCHJ4VpVXHfV
IlstQTlO4qC03hjX+ZkPyvdYd1Q4+qbAeTwXmCUKYHThVRd5aXSqlPzyIBwieMZr
WFlRQddZ1IzXAlVRDWwAo60KecqeAXnnUK+5fXoTI/UgWshre8tJ+x/TMHaQKR/J
cIWPhqaQhsJuzZbvAdGA80BLxdMCAwEAAaAAMA0GCSqGSIb3DQEBBQUAA4GBAIhl
4PvFq+e7ipARgI5ZM+GZx6mpCz44DTo0JkwfRDf+BtrsaC0q68eTf2XhYOsq4fkH
Q0uA0aVog3f5iJxCa3Hp5gxbJQ6zV6kJ0TEsuaaOhEko9sdpCoPOnRBm2i/XRD2D
6iNh8f8z0ShGsFqjDgFHyF3o+lUyj+UC6H1QW7bn
-----END CERTIFICATE REQUEST-----
"""

        cert_data_model = datagen.cert_data(cluster_model.uuid,
                                            csr_data=csr_sample)
        resp, cert_model = self.cert_client.post_cert(cert_data_model,
                                                      headers=HEADERS)
        self.LOG.debug("cert resp: %s", resp)
        self.assertEqual(201, resp.status)
        self.assertEqual(cert_model.cluster_uuid, cluster_model.uuid)
        self.assertIsNotNone(cert_model.pem)
        self.assertIn('-----BEGIN CERTIFICATE-----', cert_model.pem)
        self.assertIn('-----END CERTIFICATE-----', cert_model.pem)

        # test ca sign invalid
        cert_data_model = datagen.cert_data(cluster_model.uuid,
                                            csr_data="invalid_csr")
        self.assertRaises(
            exceptions.BadRequest,
            self.cert_client.post_cert,
            cert_data_model, headers=HEADERS)

        # test cluster delete
        self._delete_cluster(cluster_model.uuid)
        self.clusters.remove(cluster_model.uuid)

    @testtools.testcase.attr('negative')
    def test_create_cluster_for_nonexisting_cluster_template(self):
        cm_id = 'this-does-not-exist'
        gen_model = datagen.valid_cluster_data(cluster_template_id=cm_id)
        self.assertRaises(
            exceptions.BadRequest,
            self.cluster_client.post_cluster, gen_model)

    @testtools.testcase.attr('negative')
    def test_create_cluster_with_node_count_0(self):
        gen_model = datagen.valid_cluster_data(
            cluster_template_id=self.cluster_template.uuid, node_count=0)
        self.assertRaises(
            exceptions.BadRequest,
            self.cluster_client.post_cluster, gen_model)

    @testtools.testcase.attr('negative')
    def test_create_cluster_with_zero_masters(self):
        uuid = self.cluster_template.uuid
        gen_model = datagen.valid_cluster_data(cluster_template_id=uuid,
                                               master_count=0)
        self.assertRaises(
            exceptions.BadRequest,
            self.cluster_client.post_cluster, gen_model)

    @testtools.testcase.attr('negative')
    def test_create_cluster_with_nonexisting_flavor(self):
        gen_model = \
            datagen.cluster_template_data_with_valid_keypair_image_flavor()
        resp, cluster_template = self._create_cluster_template(gen_model)
        self.assertEqual(201, resp.status)
        self.assertIsNotNone(cluster_template.uuid)

        uuid = cluster_template.uuid
        gen_model = datagen.valid_cluster_data(cluster_template_id=uuid)
        gen_model.flavor_id = 'aaa'
        self.assertRaises(exceptions.BadRequest,
                          self.cluster_client.post_cluster, gen_model)

        resp, _ = self._delete_cluster_template(cluster_template.uuid)
        self.assertEqual(204, resp.status)

    @testtools.testcase.attr('negative')
    def test_update_cluster_for_nonexisting_cluster(self):
        patch_model = datagen.cluster_name_patch_data()

        self.assertRaises(
            exceptions.NotFound,
            self.cluster_client.patch_cluster, 'fooo', patch_model)

    @testtools.testcase.attr('negative')
    def test_delete_cluster_for_nonexisting_cluster(self):
        self.assertRaises(
            exceptions.NotFound,
            self.cluster_client.delete_cluster, data_utils.rand_uuid())
