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


import testtools

from magnum.tests.functional.api import base
from magnum.tests.functional.common import datagen


class BayModelAdminTest(base.BaseTempestTest):

    """Tests for baymodel admin operations."""

    def __init__(self, *args, **kwargs):
        super(BayModelAdminTest, self).__init__(*args, **kwargs)
        self.baymodels = []
        self.baymodel_client = None
        self.keypairs_client = None

    def setUp(self):
        try:
            super(BayModelAdminTest, self).setUp()
            (self.baymodel_client,
             self.keypairs_client) = self.get_clients_with_new_creds(
                 type_of_creds='admin',
                 request_type='baymodel')
        except Exception:
            self.tearDown()
            raise

    def tearDown(self):
        for baymodel_id in self.baymodels:
            self._delete_baymodel(baymodel_id)
            self.baymodels.remove(baymodel_id)
        super(BayModelAdminTest, self).tearDown()

    def _create_baymodel(self, baymodel_model):
        resp, model = self.baymodel_client.post_baymodel(baymodel_model)
        self.assertEqual(201, resp.status)
        self.baymodels.append(model.uuid)
        return resp, model

    def _delete_baymodel(self, baymodel_id):
        resp, model = self.baymodel_client.delete_baymodel(baymodel_id)
        self.assertEqual(204, resp.status)
        return resp, model

    @testtools.testcase.attr('positive')
    def test_create_get_public_baymodel(self):
        gen_model = datagen.valid_swarm_baymodel(is_public=True)
        resp, model = self._create_baymodel(gen_model)

        resp, model = self.baymodel_client.get_baymodel(model.uuid)
        self.assertEqual(200, resp.status)
        self.assertTrue(model.public)

    @testtools.testcase.attr('positive')
    def test_update_baymodel_public_by_uuid(self):
        path = "/public"
        gen_model = datagen.baymodel_data_with_valid_keypair_image_flavor()
        resp, old_model = self._create_baymodel(gen_model)

        patch_model = datagen.baymodel_replace_patch_data(path, value=True)
        resp, new_model = self.baymodel_client.patch_baymodel(
            old_model.uuid, patch_model)
        self.assertEqual(200, resp.status)

        resp, model = self.baymodel_client.get_baymodel(new_model.uuid)
        self.assertEqual(200, resp.status)
        self.assertTrue(model.public)
