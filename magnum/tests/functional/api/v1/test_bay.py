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
from tempest_lib.common.utils import data_utils
from tempest_lib import exceptions
import testtools

from magnum.tests.functional.common import base
from magnum.tests.functional.common import datagen


class BayTest(base.BaseMagnumTest):

    """Tests for bay CRUD."""

    LOG = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        super(BayTest, self).__init__(*args, **kwargs)
        self.bays = []
        self.credentials = None
        self.baymodel = None
        self.baymodel_client = None
        self.keypairs_client = None
        self.bay_client = None

    def setUp(self):
        super(BayTest, self).setUp()
        self.credentials = self.get_credentials(type_of_creds='default')
        (self.baymodel_client,
         self.keypairs_client) = self.get_clients_with_existing_creds(
             creds=self.credentials,
             type_of_creds='default',
             request_type='baymodel')
        (self.bay_client, _) = self.get_clients_with_existing_creds(
            creds=self.credentials,
            type_of_creds='default',
            request_type='bay')
        model = datagen.valid_swarm_baymodel()
        _, self.baymodel = self._create_baymodel(model)

        # NOTE (dimtruck) by default tempest sets timeout to 20 mins.
        # We need more time.
        test_timeout = 3600
        self.useFixture(fixtures.Timeout(test_timeout, gentle=True))

    def tearDown(self):
        bay_list = self.bays[:]
        for bay_id in bay_list:
            self._delete_bay(bay_id)
            self.bays.remove(bay_id)
        self._delete_baymodel(self.baymodel.uuid)
        super(BayTest, self).tearDown()

    def _create_baymodel(self, baymodel_model):
        self.keypairs_client.create_keypair(name='default')
        resp, model = self.baymodel_client.post_baymodel(baymodel_model)
        return resp, model

    def _delete_baymodel(self, baymodel_id):
        resp, model = self.baymodel_client.delete_baymodel(baymodel_id)
        return resp, model

    def _create_bay(self, bay_model):
        resp, model = self.bay_client.post_bay(bay_model)
        self.LOG.info('Response: %s' % resp)
        self.LOG.info('Model: %s ' % model)
        self.assertEqual(resp.status, 201)
        self.assertIsNotNone(model.uuid)
        self.assertIsNone(model.status)
        self.assertIsNone(model.status_reason)
        self.assertEqual(model.baymodel_id, self.baymodel.uuid)
        self.bay_client.wait_for_created_bay(model.uuid)
        self.bays.append(model.uuid)
        return resp, model

    def _delete_bay(self, bay_id):
        resp, model = self.bay_client.delete_bay(bay_id)
        self.assertEqual(resp.status, 204)
        self.bay_client.wait_for_bay_to_delete(bay_id)
        return resp, model

    def _get_bay_by_id(self, bay_id):
        resp, model = self.bay_client.get_bay(bay_id)
        self.assertEqual(resp.status, 404)
        return resp, model

    # (dimtruck) Combining all these tests in one because
    # they time out on the gate (2 hours not enough)
    @testtools.testcase.attr('positive')
    def test_create_list_and_delete_bays(self):
        gen_model = datagen.valid_bay_data(baymodel_id=self.baymodel.uuid)
        _, temp_model = self._create_bay(gen_model)
        resp, model = self.bay_client.list_bays()
        self.assertEqual(resp.status, 200)
        self.assertGreater(len(model.bays), 0)
        self.assertIn(
            temp_model.uuid, list([x['uuid'] for x in model.bays]))
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
    def test_create_bay_with_missing_name(self):
        self.skipTest('This is currently an error! '
                      'Should throw a 400 instead of a 500')
        gen_model = datagen.valid_bay_data(baymodel_id=self.baymodel.uuid,
                                           name=None)
        self.assertRaises(
            exceptions.BadRequest,
            self.bay_client.post_bay, gen_model)

    @testtools.testcase.attr('negative')
    def test_update_bay_name_for_existing_bay(self):
        first_model = datagen.valid_bay_data(baymodel_id=self.baymodel.uuid,
                                             name='test')
        _, old_model = self._create_bay(first_model)

        patch_model = datagen.bay_name_patch_data()
        self.assertRaises(
            exceptions.BadRequest,
            self.bay_client.patch_bay,
            old_model.uuid, patch_model)

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
