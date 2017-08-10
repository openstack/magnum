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


class ClusterTemplateAdminTest(base.BaseTempestTest):

    """Tests for clustertemplate admin operations."""

    def __init__(self, *args, **kwargs):
        super(ClusterTemplateAdminTest, self).__init__(*args, **kwargs)
        self.cluster_templates = []
        self.cluster_template_client = None
        self.keypairs_client = None

    def setUp(self):
        try:
            super(ClusterTemplateAdminTest, self).setUp()
            (self.cluster_template_client,
             self.keypairs_client) = self.get_clients_with_new_creds(
                 type_of_creds='admin',
                 request_type='cluster_template')
        except Exception:
            self.tearDown()
            raise

    def tearDown(self):
        for cluster_template_id in self.cluster_templates:
            self._delete_cluster_template(cluster_template_id)
            self.cluster_templates.remove(cluster_template_id)
        super(ClusterTemplateAdminTest, self).tearDown()

    def _create_cluster_template(self, cmodel_model):
        resp, model = \
            self.cluster_template_client.post_cluster_template(cmodel_model)
        self.assertEqual(201, resp.status)
        self.cluster_templates.append(model.uuid)
        return resp, model

    def _delete_cluster_template(self, model_id):
        resp, model = \
            self.cluster_template_client.delete_cluster_template(model_id)
        self.assertEqual(204, resp.status)
        return resp, model

    @testtools.testcase.attr('positive')
    def test_create_get_public_cluster_template(self):
        gen_model = datagen.valid_swarm_mode_cluster_template(is_public=True)
        resp, model = self._create_cluster_template(gen_model)

        resp, model = \
            self.cluster_template_client.get_cluster_template(model.uuid)
        self.assertEqual(200, resp.status)
        self.assertTrue(model.public)

    @testtools.testcase.attr('positive')
    def test_update_cluster_template_public_by_uuid(self):
        path = "/public"
        gen_model = \
            datagen.cluster_template_data_with_valid_keypair_image_flavor()
        resp, old_model = self._create_cluster_template(gen_model)

        patch_model = datagen.cluster_template_replace_patch_data(path,
                                                                  value=True)
        resp, new_model = self.cluster_template_client.patch_cluster_template(
            old_model.uuid, patch_model)
        self.assertEqual(200, resp.status)

        resp, model = self.cluster_template_client.get_cluster_template(
            new_model.uuid)
        self.assertEqual(200, resp.status)
        self.assertTrue(model.public)
