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

"""Tests for manipulating ClusterTemplate via the DB API"""
from oslo_utils import uuidutils

from magnum.common import exception
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils


class DbClusterTemplateTestCase(base.DbTestCase):

    def test_create_cluster_template(self):
        utils.create_test_cluster_template()

    def test_get_cluster_template_list(self):
        uuids = []
        for i in range(1, 6):
            ct = utils.create_test_cluster_template(
                id=i, uuid=uuidutils.generate_uuid())
            uuids.append(str(ct['uuid']))
        res = self.dbapi.get_cluster_template_list(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    def test_get_cluster_template_list_sorted(self):
        uuids = []
        for _ in range(5):
            ct = utils.create_test_cluster_template(
                uuid=uuidutils.generate_uuid())
            uuids.append(str(ct['uuid']))
        res = self.dbapi.get_cluster_template_list(self.context,
                                                   sort_key='uuid')
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), res_uuids)

        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.get_cluster_template_list,
                          self.context,
                          sort_key='foo')

    def test_get_cluster_template_list_with_filters(self):
        ct1 = utils.create_test_cluster_template(
            id=1,
            name='ct-one',
            uuid=uuidutils.generate_uuid(),
            image_id='image1')
        ct2 = utils.create_test_cluster_template(
            id=2,
            name='ct-two',
            uuid=uuidutils.generate_uuid(),
            image_id='image2')

        res = self.dbapi.get_cluster_template_list(self.context,
                                                   filters={'name': 'ct-one'})
        self.assertEqual([ct1['id']], [r.id for r in res])

        res = self.dbapi.get_cluster_template_list(
            self.context, filters={'name': 'bad-name'})
        self.assertEqual([], [r.id for r in res])

        res = self.dbapi.get_cluster_template_list(
            self.context, filters={'image_id': 'image1'})
        self.assertEqual([ct1['id']], [r.id for r in res])

        res = self.dbapi.get_cluster_template_list(
            self.context, filters={'image_id': 'image2'})
        self.assertEqual([ct2['id']], [r.id for r in res])

    def test_get_cluster_template_by_id(self):
        ct = utils.create_test_cluster_template()
        cluster_template = self.dbapi.get_cluster_template_by_id(
            self.context, ct['id'])
        self.assertEqual(ct['uuid'], cluster_template.uuid)

    def test_get_cluster_template_by_id_public(self):
        ct = utils.create_test_cluster_template(user_id='not_me', public=True)
        cluster_template = self.dbapi.get_cluster_template_by_id(
            self.context, ct['id'])
        self.assertEqual(ct['uuid'], cluster_template.uuid)

    def test_get_cluster_template_by_id_hidden(self):
        ct = utils.create_test_cluster_template(user_id='not_me', hidden=True)
        cluster_template = self.dbapi.get_cluster_template_by_id(
            self.context, ct['id'])
        self.assertEqual(ct['uuid'], cluster_template.uuid)

    def test_get_cluster_template_by_uuid(self):
        ct = utils.create_test_cluster_template()
        cluster_template = self.dbapi.get_cluster_template_by_uuid(
            self.context, ct['uuid'])
        self.assertEqual(ct['id'], cluster_template.id)

    def test_get_cluster_template_by_uuid_public(self):
        ct = utils.create_test_cluster_template(user_id='not_me', public=True)
        cluster_template = self.dbapi.get_cluster_template_by_uuid(
            self.context, ct['uuid'])
        self.assertEqual(ct['id'], cluster_template.id)

    def test_get_cluster_template_by_uuid_hidden(self):
        ct = utils.create_test_cluster_template(user_id='not_me', hidden=True)
        cluster_template = self.dbapi.get_cluster_template_by_uuid(
            self.context, ct['uuid'])
        self.assertEqual(ct['id'], cluster_template.id)

    def test_get_cluster_template_that_does_not_exist(self):
        self.assertRaises(exception.ClusterTemplateNotFound,
                          self.dbapi.get_cluster_template_by_id,
                          self.context, 666)

    def test_get_cluster_template_by_name(self):
        ct = utils.create_test_cluster_template()
        res = self.dbapi.get_cluster_template_by_name(self.context, ct['name'])
        self.assertEqual(ct['id'], res.id)
        self.assertEqual(ct['uuid'], res.uuid)

    def test_get_cluster_template_by_name_public(self):
        ct = utils.create_test_cluster_template(user_id='not_me', public=True)
        res = self.dbapi.get_cluster_template_by_name(self.context, ct['name'])
        self.assertEqual(ct['id'], res.id)
        self.assertEqual(ct['uuid'], res.uuid)

    def test_get_cluster_template_by_name_hidden(self):
        ct = utils.create_test_cluster_template(user_id='not_me', hidden=True)
        res = self.dbapi.get_cluster_template_by_name(self.context, ct['name'])
        self.assertEqual(ct['id'], res.id)
        self.assertEqual(ct['uuid'], res.uuid)

    def test_get_cluster_template_by_name_multiple_cluster_template(self):
        utils.create_test_cluster_template(
            id=1, name='ct',
            uuid=uuidutils.generate_uuid(),
            image_id='image1')
        utils.create_test_cluster_template(
            id=2, name='ct',
            uuid=uuidutils.generate_uuid(),
            image_id='image2')
        self.assertRaises(exception.Conflict,
                          self.dbapi.get_cluster_template_by_name,
                          self.context, 'ct')

    def test_get_cluster_template_by_name_not_found(self):
        self.assertRaises(exception.ClusterTemplateNotFound,
                          self.dbapi.get_cluster_template_by_name,
                          self.context, 'not_found')

    def test_get_cluster_template_by_uuid_that_does_not_exist(self):
        self.assertRaises(exception.ClusterTemplateNotFound,
                          self.dbapi.get_cluster_template_by_uuid,
                          self.context,
                          '12345678-9999-0000-aaaa-123456789012')

    def test_update_cluster_template(self):
        ct = utils.create_test_cluster_template()
        res = self.dbapi.update_cluster_template(ct['id'],
                                                 {'name': 'updated-model'})
        self.assertEqual('updated-model', res.name)

    def test_update_cluster_template_that_does_not_exist(self):
        self.assertRaises(exception.ClusterTemplateNotFound,
                          self.dbapi.update_cluster_template, 666,
                          {'name': ''})

    def test_update_cluster_template_uuid(self):
        ct = utils.create_test_cluster_template()
        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.update_cluster_template, ct['id'],
                          {'uuid': 'hello'})

    def test_destroy_cluster_template(self):
        ct = utils.create_test_cluster_template()
        self.dbapi.destroy_cluster_template(ct['id'])
        self.assertRaises(exception.ClusterTemplateNotFound,
                          self.dbapi.get_cluster_template_by_id,
                          self.context, ct['id'])

    def test_destroy_cluster_template_by_uuid(self):
        uuid = uuidutils.generate_uuid()
        utils.create_test_cluster_template(uuid=uuid)
        self.assertIsNotNone(self.dbapi.get_cluster_template_by_uuid(
            self.context, uuid))
        self.dbapi.destroy_cluster_template(uuid)
        self.assertRaises(exception.ClusterTemplateNotFound,
                          self.dbapi.get_cluster_template_by_uuid,
                          self.context, uuid)

    def test_destroy_cluster_template_that_does_not_exist(self):
        self.assertRaises(exception.ClusterTemplateNotFound,
                          self.dbapi.destroy_cluster_template, 666)

    def test_destroy_cluster_template_that_referenced_by_clusters(self):
        ct = utils.create_test_cluster_template()
        cluster = utils.create_test_cluster(cluster_template_id=ct['uuid'])
        self.assertEqual(ct['uuid'], cluster.cluster_template_id)
        self.assertRaises(exception.ClusterTemplateReferenced,
                          self.dbapi.destroy_cluster_template, ct['id'])

    def test_create_cluster_template_already_exists(self):
        uuid = uuidutils.generate_uuid()
        utils.create_test_cluster_template(id=1, uuid=uuid)
        self.assertRaises(exception.ClusterTemplateAlreadyExists,
                          utils.create_test_cluster_template,
                          id=2, uuid=uuid)
