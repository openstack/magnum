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


from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions
import testtools

from magnum.tests.functional.api import base
from magnum.tests.functional.common import datagen


class ClusterTemplateTest(base.BaseTempestTest):

    """Tests for clustertemplate CRUD."""

    def __init__(self, *args, **kwargs):
        super(ClusterTemplateTest, self).__init__(*args, **kwargs)
        self.cluster_templates = []
        self.cluster_template_client = None
        self.keypairs_client = None

    def setUp(self):
        try:
            super(ClusterTemplateTest, self).setUp()
            (self.cluster_template_client,
             self.keypairs_client) = self.get_clients_with_new_creds(
                 type_of_creds='default',
                 request_type='cluster_template')
        except Exception:
            self.tearDown()
            raise

    def tearDown(self):
        for cluster_template_id in self.cluster_templates:
            self._delete_cluster_template(cluster_template_id)
            self.cluster_templates.remove(cluster_template_id)
        super(ClusterTemplateTest, self).tearDown()

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
    def test_list_cluster_templates(self):
        gen_model = \
            datagen.cluster_template_data_with_valid_keypair_image_flavor()
        _, temp_model = self._create_cluster_template(gen_model)
        resp, model = self.cluster_template_client.list_cluster_templates()
        self.assertEqual(200, resp.status)
        self.assertGreater(len(model.clustertemplates), 0)
        self.assertIn(
            temp_model.uuid,
            list([x['uuid'] for x in model.clustertemplates]))

    @testtools.testcase.attr('positive')
    def test_create_cluster_template(self):
        gen_model = \
            datagen.cluster_template_data_with_valid_keypair_image_flavor()
        resp, model = self._create_cluster_template(gen_model)

    @testtools.testcase.attr('positive')
    def test_create_get_public_cluster_template(self):
        gen_model = datagen.valid_swarm_cluster_template(is_public=True)
        self.assertRaises(
            exceptions.Forbidden,
            self.cluster_template_client.post_cluster_template, gen_model)

    @testtools.testcase.attr('positive')
    def test_update_cluster_template_public_by_uuid(self):
        path = "/public"
        gen_model = \
            datagen.cluster_template_data_with_valid_keypair_image_flavor()
        resp, old_model = self._create_cluster_template(gen_model)

        patch_model = datagen.cluster_template_replace_patch_data(path,
                                                                  value=True)
        self.assertRaises(
            exceptions.Forbidden,
            self.cluster_template_client.patch_cluster_template,
            old_model.uuid, patch_model)

    @testtools.testcase.attr('positive')
    def test_update_cluster_template_by_uuid(self):
        gen_model = \
            datagen.cluster_template_data_with_valid_keypair_image_flavor()
        resp, old_model = self._create_cluster_template(gen_model)

        patch_model = datagen.cluster_template_name_patch_data()
        resp, new_model = self.cluster_template_client.patch_cluster_template(
            old_model.uuid, patch_model)
        self.assertEqual(200, resp.status)

        resp, model = \
            self.cluster_template_client.get_cluster_template(new_model.uuid)
        self.assertEqual(200, resp.status)
        self.assertEqual(old_model.uuid, new_model.uuid)
        self.assertEqual(model.name, new_model.name)

    @testtools.testcase.attr('positive')
    def test_delete_cluster_template_by_uuid(self):
        gen_model = \
            datagen.cluster_template_data_with_valid_keypair_image_flavor()
        resp, model = self._create_cluster_template(gen_model)
        resp, _ = self.cluster_template_client.delete_cluster_template(
            model.uuid)
        self.assertEqual(204, resp.status)
        self.cluster_templates.remove(model.uuid)

    @testtools.testcase.attr('positive')
    def test_delete_cluster_template_by_name(self):
        gen_model = \
            datagen.cluster_template_data_with_valid_keypair_image_flavor()
        resp, model = self._create_cluster_template(gen_model)
        resp, _ = self.cluster_template_client.delete_cluster_template(
            model.name)
        self.assertEqual(204, resp.status)
        self.cluster_templates.remove(model.uuid)

    @testtools.testcase.attr('negative')
    def test_get_cluster_template_by_uuid_404(self):
        self.assertRaises(
            exceptions.NotFound,
            self.cluster_template_client.get_cluster_template,
            data_utils.rand_uuid())

    @testtools.testcase.attr('negative')
    def test_update_cluster_template_404(self):
        patch_model = datagen.cluster_template_name_patch_data()

        self.assertRaises(
            exceptions.NotFound,
            self.cluster_template_client.patch_cluster_template,
            data_utils.rand_uuid(), patch_model)

    @testtools.testcase.attr('negative')
    def test_delete_cluster_template_404(self):
        self.assertRaises(
            exceptions.NotFound,
            self.cluster_template_client.delete_cluster_template,
            data_utils.rand_uuid())

    @testtools.testcase.attr('negative')
    def test_get_cluster_template_by_name_404(self):
        self.assertRaises(
            exceptions.NotFound,
            self.cluster_template_client.get_cluster_template, 'fooo')

    @testtools.testcase.attr('negative')
    def test_update_cluster_template_name_not_found(self):
        patch_model = datagen.cluster_template_name_patch_data()

        self.assertRaises(
            exceptions.NotFound,
            self.cluster_template_client.patch_cluster_template,
            'fooo', patch_model)

    @testtools.testcase.attr('negative')
    def test_delete_cluster_template_by_name_404(self):
        self.assertRaises(
            exceptions.NotFound,
            self.cluster_template_client.get_cluster_template, 'fooo')

    @testtools.testcase.attr('negative')
    def test_create_cluster_template_missing_image(self):
        gen_model = datagen.cluster_template_data_with_missing_image()
        self.assertRaises(
            exceptions.BadRequest,
            self.cluster_template_client.post_cluster_template, gen_model)

    @testtools.testcase.attr('negative')
    def test_create_cluster_template_missing_flavor(self):
        gen_model = datagen.cluster_template_data_with_missing_flavor()
        self.assertRaises(
            exceptions.BadRequest,
            self.cluster_template_client.post_cluster_template, gen_model)

    @testtools.testcase.attr('positive')
    def test_create_cluster_template_missing_keypair(self):
        gen_model = \
            datagen.cluster_template_data_with_missing_keypair()
        resp, model = self._create_cluster_template(gen_model)

    @testtools.testcase.attr('negative')
    def test_update_cluster_template_invalid_patch(self):
        # get json object
        gen_model = \
            datagen.cluster_template_data_with_valid_keypair_image_flavor()
        resp, old_model = self._create_cluster_template(gen_model)

        self.assertRaises(
            exceptions.BadRequest,
            self.cluster_template_client.patch_cluster_template,
            data_utils.rand_uuid(), gen_model)

    @testtools.testcase.attr('negative')
    def test_create_cluster_template_invalid_network_driver(self):
        gen_model = \
            datagen.cluster_template_data_with_valid_keypair_image_flavor()
        gen_model.network_driver = 'invalid_network_driver'
        self.assertRaises(
            exceptions.BadRequest,
            self.cluster_template_client.post_cluster_template, gen_model)

    @testtools.testcase.attr('negative')
    def test_create_cluster_template_invalid_volume_driver(self):
        gen_model = \
            datagen.cluster_template_data_with_valid_keypair_image_flavor()
        gen_model.volume_driver = 'invalid_volume_driver'
        self.assertRaises(
            exceptions.BadRequest,
            self.cluster_template_client.post_cluster_template, gen_model)
