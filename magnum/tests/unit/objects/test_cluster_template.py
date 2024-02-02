# Copyright 2015 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from unittest import mock

from oslo_utils import uuidutils
from testtools.matchers import HasLength

from magnum.common import exception
from magnum import objects
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils


class TestClusterTemplateObject(base.DbTestCase):

    def setUp(self):
        super(TestClusterTemplateObject, self).setUp()
        self.fake_cluster_template = utils.get_test_cluster_template()

    def test_get_by_id(self):
        cluster_template_id = self.fake_cluster_template['id']
        with mock.patch.object(self.dbapi, 'get_cluster_template_by_id',
                               autospec=True) as mock_get_cluster_template:
            mock_get_cluster_template.return_value = self.fake_cluster_template
            cluster_template = objects.ClusterTemplate.get(self.context,
                                                           cluster_template_id)
            mock_get_cluster_template.assert_called_once_with(
                self.context, cluster_template_id)
            self.assertEqual(self.context, cluster_template._context)

    def test_get_by_uuid(self):
        uuid = self.fake_cluster_template['uuid']
        with mock.patch.object(self.dbapi, 'get_cluster_template_by_uuid',
                               autospec=True) as mock_get_cluster_template:
            mock_get_cluster_template.return_value = self.fake_cluster_template
            cluster_template = objects.ClusterTemplate.get(self.context, uuid)
            mock_get_cluster_template.assert_called_once_with(self.context,
                                                              uuid)
            self.assertEqual(self.context, cluster_template._context)

    def test_get_bad_id_and_uuid(self):
        self.assertRaises(exception.ClusterTemplateNotFound,
                          objects.ClusterTemplate.get, self.context,
                          'not-a-uuid')

    def test_get_by_name(self):
        name = self.fake_cluster_template['name']
        with mock.patch.object(self.dbapi, 'get_cluster_template_by_name',
                               autospec=True) as mock_get_cluster_template:
            mock_get_cluster_template.return_value = self.fake_cluster_template
            cluster_template = objects.ClusterTemplate.get_by_name(
                self.context, name)
            mock_get_cluster_template.assert_called_once_with(self.context,
                                                              name)
            self.assertEqual(self.context, cluster_template._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'get_cluster_template_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_cluster_template]
            cluster_templates = objects.ClusterTemplate.list(self.context)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(cluster_templates, HasLength(1))
            self.assertIsInstance(cluster_templates[0],
                                  objects.ClusterTemplate)
            self.assertEqual(self.context, cluster_templates[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_cluster_template',
                               autospec=True) as mock_create_cluster_template:
            mock_create_cluster_template.return_value = \
                self.fake_cluster_template
            cluster_template = objects.ClusterTemplate(
                self.context, **self.fake_cluster_template)
            cluster_template.create()
            mock_create_cluster_template.assert_called_once_with(
                self.fake_cluster_template)
            self.assertEqual(self.context, cluster_template._context)

    def test_destroy(self):
        uuid = self.fake_cluster_template['uuid']
        with mock.patch.object(self.dbapi, 'get_cluster_template_by_uuid',
                               autospec=True) as mock_get_cluster_template:
            mock_get_cluster_template.return_value = self.fake_cluster_template
            with mock.patch.object(
                    self.dbapi, 'destroy_cluster_template', autospec=True)\
                    as mock_destroy_cluster_template:
                cluster_template = objects.ClusterTemplate.get_by_uuid(
                    self.context, uuid)
                cluster_template.destroy()
                mock_get_cluster_template.assert_called_once_with(self.context,
                                                                  uuid)
                mock_destroy_cluster_template.assert_called_once_with(uuid)
                self.assertEqual(self.context, cluster_template._context)

    def test_save(self):
        uuid = self.fake_cluster_template['uuid']
        with mock.patch.object(self.dbapi, 'get_cluster_template_by_uuid',
                               autospec=True) as mock_get_cluster_template:
            mock_get_cluster_template.return_value = self.fake_cluster_template
            with mock.patch.object(self.dbapi, 'update_cluster_template',
                                   autospec=True) \
                    as mock_update_cluster_template:
                cluster_template = objects.ClusterTemplate.get_by_uuid(
                    self.context, uuid)
                cluster_template.image_id = 'test-image'
                cluster_template.save()

                mock_get_cluster_template.assert_called_once_with(self.context,
                                                                  uuid)
                mock_update_cluster_template.assert_called_once_with(
                    uuid, {'image_id': 'test-image'})
                self.assertEqual(self.context, cluster_template._context)

    def test_refresh(self):
        uuid = self.fake_cluster_template['uuid']
        new_uuid = uuidutils.generate_uuid()
        returns = [dict(self.fake_cluster_template, uuid=uuid),
                   dict(self.fake_cluster_template, uuid=new_uuid)]
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        with mock.patch.object(self.dbapi, 'get_cluster_template_by_uuid',
                               side_effect=returns,
                               autospec=True) as mock_get_cluster_template:
            cluster_template = objects.ClusterTemplate.get_by_uuid(
                self.context, uuid)
            self.assertEqual(uuid, cluster_template.uuid)
            cluster_template.refresh()
            self.assertEqual(new_uuid, cluster_template.uuid)
            self.assertEqual(expected,
                             mock_get_cluster_template.call_args_list)
            self.assertEqual(self.context, cluster_template._context)
