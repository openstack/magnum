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
from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions
import testtools

from magnum.objects.fields import BayStatus
from magnum.tests.functional.common import base
from magnum.tests.functional.common import datagen


class BayTest(base.BaseMagnumTest):

    """Tests for bay CRUD."""

    LOG = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        super(BayTest, self).__init__(*args, **kwargs)
        self.bays = []
        self.creds = None
        self.keypair = None
        self.baymodel = None
        self.baymodel_client = None
        self.keypairs_client = None
        self.bay_client = None
        self.cert_client = None

    def setUp(self):
        try:
            super(BayTest, self).setUp()
            (self.creds, self.keypair) = self.get_credentials_with_keypair(
                type_of_creds='default')
            (self.baymodel_client,
                self.keypairs_client) = self.get_clients_with_existing_creds(
                    creds=self.creds,
                    type_of_creds='default',
                    request_type='baymodel')
            (self.bay_client, _) = self.get_clients_with_existing_creds(
                creds=self.creds,
                type_of_creds='default',
                request_type='bay')
            (self.cert_client, _) = self.get_clients_with_existing_creds(
                creds=self.creds,
                type_of_creds='default',
                request_type='cert')
            model = datagen.valid_swarm_baymodel()
            _, self.baymodel = self._create_baymodel(model)

            # NOTE (dimtruck) by default tempest sets timeout to 20 mins.
            # We need more time.
            test_timeout = 1800
            self.useFixture(fixtures.Timeout(test_timeout, gentle=True))
        except Exception:
            self.tearDown()
            raise

    def tearDown(self):
        try:
            bay_list = self.bays[:]
            for bay_id in bay_list:
                self._delete_bay(bay_id)
                self.bays.remove(bay_id)
            self._delete_baymodel(self.baymodel.uuid)
        finally:
            super(BayTest, self).tearDown()

    def _create_baymodel(self, baymodel_model):
        self.LOG.debug('We will create a baymodel for %s' % baymodel_model)
        resp, model = self.baymodel_client.post_baymodel(baymodel_model)
        return resp, model

    def _delete_baymodel(self, baymodel_id):
        self.LOG.debug('We will delete a baymodel for %s' % baymodel_id)
        resp, model = self.baymodel_client.delete_baymodel(baymodel_id)
        return resp, model

    def _create_bay(self, bay_model):
        self.LOG.debug('We will create bay for %s' % bay_model)
        resp, model = self.bay_client.post_bay(bay_model)
        self.LOG.debug('Response: %s' % resp)
        self.assertEqual(201, resp.status)
        self.assertIsNotNone(model.uuid)
        self.bays.append(model.uuid)
        self.assertEqual(BayStatus.CREATE_IN_PROGRESS, model.status)
        self.assertIsNone(model.status_reason)
        self.assertEqual(model.baymodel_id, self.baymodel.uuid)
        self.bay_uuid = model.uuid
        self.addOnException(self.copy_logs_handler(
            lambda: list(
                [self._get_bay_by_id(self.bay_uuid)[1].master_addresses,
                 self._get_bay_by_id(self.bay_uuid)[1].node_addresses]),
            self.baymodel.coe,
            self.keypair))
        self.bay_client.wait_for_created_bay(model.uuid, delete_on_error=False)
        return resp, model

    def _delete_bay(self, bay_id):
        self.LOG.debug('We will delete a bay for %s' % bay_id)
        resp, model = self.bay_client.delete_bay(bay_id)
        self.assertEqual(204, resp.status)
        self.bay_client.wait_for_bay_to_delete(bay_id)
        return resp, model

    def _get_bay_by_id(self, bay_id):
        resp, model = self.bay_client.get_bay(bay_id)
        return resp, model

    # (dimtruck) Combining all these tests in one because
    # they time out on the gate (2 hours not enough)
    @testtools.testcase.attr('positive')
    def test_create_list_and_delete_bays(self):
        gen_model = datagen.valid_bay_data(
            baymodel_id=self.baymodel.uuid, node_count=1)

        # test bay create
        _, temp_model = self._create_bay(gen_model)

        # test bay list
        resp, model = self.bay_client.list_bays()
        self.assertEqual(200, resp.status)
        self.assertGreater(len(model.bays), 0)
        self.assertIn(
            temp_model.uuid, list([x['uuid'] for x in model.bays]))

        # test invalid bay update
        patch_model = datagen.bay_name_patch_data()
        self.assertRaises(
            exceptions.BadRequest,
            self.bay_client.patch_bay,
            temp_model.uuid, patch_model)

        # test bay delete
        self._delete_bay(temp_model.uuid)
        self.bays.remove(temp_model.uuid)

    @testtools.testcase.attr('negative')
    def test_create_bay_for_nonexisting_baymodel(self):
        gen_model = datagen.valid_bay_data(baymodel_id='this-does-not-exist')
        self.assertRaises(
            exceptions.BadRequest,
            self.bay_client.post_bay, gen_model)

    @testtools.testcase.attr('negative')
    def test_create_bay_with_node_count_0(self):
        gen_model = datagen.valid_bay_data(
            baymodel_id=self.baymodel.uuid, node_count=0)
        self.assertRaises(
            exceptions.BadRequest,
            self.bay_client.post_bay, gen_model)

    @testtools.testcase.attr('negative')
    def test_create_bay_with_zero_masters(self):
        gen_model = datagen.valid_bay_data(baymodel_id=self.baymodel.uuid,
                                           master_count=0)
        self.assertRaises(
            exceptions.BadRequest,
            self.bay_client.post_bay, gen_model)

    @testtools.testcase.attr('negative')
    def test_create_bay_with_nonexisting_flavor(self):
        gen_model = datagen.baymodel_data_with_valid_keypair_image_flavor()
        resp, baymodel = self._create_baymodel(gen_model)
        self.assertEqual(201, resp.status)
        self.assertIsNotNone(baymodel.uuid)

        gen_model = datagen.valid_bay_data(baymodel_id=baymodel.uuid)
        gen_model.flavor_id = 'aaa'
        self.assertRaises(
            exceptions.BadRequest,
            self.bay_client.post_bay, gen_model)

        resp, _ = self._delete_baymodel(baymodel.uuid)
        self.assertEqual(204, resp.status)

    @testtools.testcase.attr('negative')
    def test_update_bay_for_nonexisting_bay(self):
        patch_model = datagen.bay_name_patch_data()

        self.assertRaises(
            exceptions.NotFound,
            self.bay_client.patch_bay, 'fooo', patch_model)

    @testtools.testcase.attr('negative')
    def test_delete_bay_for_nonexisting_bay(self):
        self.assertRaises(
            exceptions.NotFound,
            self.bay_client.delete_bay, data_utils.rand_uuid())

    @testtools.testcase.attr('positive')
    def test_certificate_sign_and_show(self):
        first_model = datagen.valid_bay_data(baymodel_id=self.baymodel.uuid,
                                             name='test')
        _, bay_model = self._create_bay(first_model)

        # test ca show
        resp, model = self.cert_client.get_cert(
            bay_model.uuid)
        self.LOG.debug("cert resp: %s" % resp)
        self.assertEqual(200, resp.status)
        self.assertEqual(model.bay_uuid, bay_model.uuid)
        self.assertIsNotNone(model.pem)
        self.assertIn('-----BEGIN CERTIFICATE-----', model.pem)
        self.assertIn('-----END CERTIFICATE-----', model.pem)

        # test ca sign
        model = datagen.cert_data(bay_uuid=bay_model.uuid)
        resp, model = self.cert_client.post_cert(model)
        self.LOG.debug("cert resp: %s" % resp)
        self.assertEqual(201, resp.status)
        self.assertEqual(model.bay_uuid, bay_model.uuid)
        self.assertIsNotNone(model.pem)
        self.assertIn('-----BEGIN CERTIFICATE-----', model.pem)
        self.assertIn('-----END CERTIFICATE-----', model.pem)

        # test ca sign invalid
        model = datagen.cert_data(bay_uuid=bay_model.uuid,
                                  csr_data="invalid_csr")
        self.assertRaises(
            exceptions.BadRequest,
            self.cert_client.post_cert,
            model)
