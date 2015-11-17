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


from tempest_lib import exceptions
import testtools

from magnum.tests.functional.api.v1.clients import baymodel_client as cli
from magnum.tests.functional.common import base
from magnum.tests.functional.common import datagen


class BayModelTest(base.BaseMagnumTest):

    """Tests for baymodel CRUD."""

    def __init__(self, *args, **kwargs):
        super(BayModelTest, self).__init__(*args, **kwargs)
        self.baymodels = []

    def setUp(self):
        super(BayModelTest, self).setUp()

    def tearDown(self):
        super(BayModelTest, self).tearDown()
        for (baymodel_id, user) in self.baymodels:
            self._delete_baymodel(baymodel_id, user)
            self.baymodels.remove((baymodel_id, user))

    def _create_baymodel(self, baymodel_model, user='default'):
        resp, model = cli.BayModelClient.as_user(user).post_baymodel(
            baymodel_model)
        self.assertEqual(201, resp.status)
        self.baymodels.append((model.uuid, user))
        return resp, model

    def _delete_baymodel(self, baymodel_id, user='default'):
        resp, model = cli.BayModelClient.as_user(user).delete_baymodel(
            baymodel_id)
        self.assertEqual(204, resp.status)
        return resp, model

    @testtools.testcase.attr('positive')
    def test_list_baymodels(self):
        gen_model = datagen.random_baymodel_data_w_valid_keypair_and_image_id()
        _, temp_model = self._create_baymodel(gen_model, user='default')
        resp, model = cli.BayModelClient.as_user('default').list_baymodels()
        self.assertEqual(200, resp.status)
        self.assertGreater(len(model.baymodels), 0)
        self.assertIn(
            temp_model.uuid, list([x['uuid'] for x in model.baymodels]))

    @testtools.testcase.attr('positive')
    def test_create_baymodel(self):
        gen_model = datagen.random_baymodel_data_w_valid_keypair_and_image_id()
        resp, model = self._create_baymodel(gen_model, user='default')

    @testtools.testcase.attr('positive')
    def test_update_baymodel_by_uuid(self):
        gen_model = datagen.random_baymodel_data_w_valid_keypair_and_image_id()
        resp, old_model = self._create_baymodel(gen_model, user='default')

        patch_model = datagen.random_baymodel_name_patch_data()
        bay_model_client = cli.BayModelClient.as_user('default')
        resp, new_model = bay_model_client.patch_baymodel(
            old_model.uuid, patch_model)
        self.assertEqual(200, resp.status)

        resp, model = cli.BayModelClient.as_user('default').get_baymodel(
            new_model.uuid)
        self.assertEqual(200, resp.status)
        self.assertEqual(old_model.uuid, new_model.uuid)
        self.assertEqual(model.name, new_model.name)

    @testtools.testcase.attr('positive')
    def test_delete_baymodel_by_uuid(self):
        gen_model = datagen.random_baymodel_data_w_valid_keypair_and_image_id()
        resp, model = self._create_baymodel(gen_model, user='default')
        resp, _ = cli.BayModelClient.as_user('default').delete_baymodel(
            model.uuid)
        self.assertEqual(204, resp.status)
        self.baymodels.remove((model.uuid, 'default'))

    @testtools.testcase.attr('positive')
    def test_delete_baymodel_by_name(self):
        gen_model = datagen.random_baymodel_data_w_valid_keypair_and_image_id()
        resp, model = self._create_baymodel(gen_model, user='default')
        resp, _ = cli.BayModelClient.as_user('default').delete_baymodel(
            model.name)
        self.assertEqual(204, resp.status)
        self.baymodels.remove((model.uuid, 'default'))

    @testtools.testcase.attr('negative')
    def test_get_baymodel_by_uuid_404(self):
        bay_model_client = cli.BayModelClient.as_user('default')
        self.assertRaises(
            exceptions.NotFound,
            bay_model_client.get_baymodel, datagen.random_uuid())

    @testtools.testcase.attr('negative')
    def test_update_baymodel_404(self):
        patch_model = datagen.random_baymodel_name_patch_data()

        bay_model_client = cli.BayModelClient.as_user('default')
        self.assertRaises(
            exceptions.NotFound,
            bay_model_client.patch_baymodel,
            datagen.random_uuid(), patch_model)

    @testtools.testcase.attr('negative')
    def test_delete_baymodel_404(self):
        bay_model_client = cli.BayModelClient.as_user('default')
        self.assertRaises(
            exceptions.NotFound,
            bay_model_client.delete_baymodel, datagen.random_uuid())

    @testtools.testcase.attr('negative')
    def test_get_baymodel_by_name_404(self):
        bay_model_client = cli.BayModelClient.as_user('default')
        self.assertRaises(
            exceptions.NotFound,
            bay_model_client.get_baymodel, 'fooo')

    @testtools.testcase.attr('negative')
    def test_update_baymodel_name_not_found(self):
        patch_model = datagen.random_baymodel_name_patch_data()

        bay_model_client = cli.BayModelClient.as_user('default')
        self.assertRaises(
            exceptions.NotFound,
            bay_model_client.patch_baymodel, 'fooo', patch_model)

    @testtools.testcase.attr('negative')
    def test_delete_baymodel_by_name_404(self):
        bay_model_client = cli.BayModelClient.as_user('default')
        self.assertRaises(
            exceptions.NotFound,
            bay_model_client.get_baymodel, 'fooo')

    @testtools.testcase.attr('negative')
    def test_create_baymodel_missing_image(self):
        bay_model_client = cli.BayModelClient.as_user('default')
        gen_model = datagen.random_baymodel_data_w_valid_keypair()
        self.assertRaises(
            exceptions.NotFound,
            bay_model_client.post_baymodel, gen_model)

    @testtools.testcase.attr('negative')
    def test_create_baymodel_missing_keypair(self):
        bay_model_client = cli.BayModelClient.as_user('default')
        gen_model = datagen.random_baymodel_data_w_valid_image_id()
        self.assertRaises(
            exceptions.NotFound,
            bay_model_client.post_baymodel, gen_model)

    @testtools.testcase.attr('negative')
    def test_update_baymodel_invalid_patch(self):
        # get json object
        gen_model = datagen.random_baymodel_data_w_valid_keypair_and_image_id()
        resp, old_model = self._create_baymodel(gen_model)

        bay_model_client = cli.BayModelClient.as_user('default')
        self.assertRaises(
            exceptions.BadRequest,
            bay_model_client.patch_baymodel, datagen.random_uuid(), gen_model)

    @testtools.testcase.attr('negative')
    def test_create_baymodel_invalid_network_driver(self):
        bay_model_client = cli.BayModelClient.as_user('default')
        gen_model = datagen.random_baymodel_data_w_valid_keypair_and_image_id()
        gen_model.network_driver = 'invalid_network_driver'
        self.assertRaises(
            exceptions.BadRequest,
            bay_model_client.post_baymodel, gen_model)
