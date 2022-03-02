# Copyright 2016 Yahoo! Inc.
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

"""Tests for manipulating Quota via the DB API"""

from magnum.common import exception
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils


class DbQuotaTestCase(base.DbTestCase):

    def test_create_quota(self):
        utils.create_test_quotas()

    def test_create_quota_already_exists(self):
        utils.create_test_quotas()
        self.assertRaises(exception.QuotaAlreadyExists,
                          utils.create_test_quotas)

    def test_get_quota_all(self):
        q = utils.create_test_quotas()
        res = self.dbapi.quota_get_all_by_project_id(
            project_id='fake_project')
        for r in res:
            self.assertEqual(q.id, r.id)
            self.assertEqual(q.hard_limit, r.hard_limit)
            self.assertEqual(q.project_id, r.project_id)
            self.assertEqual(q.resource, r.resource)

    def test_get_quota_by_project_id_resource(self):
        q = utils.create_test_quotas(project_id='123',
                                     resource='test-res',
                                     hard_limit=5)
        res = self.dbapi.get_quota_by_project_id_resource('123', 'test-res')
        self.assertEqual(q.hard_limit, res.hard_limit)
        self.assertEqual(q.project_id, res.project_id)
        self.assertEqual(q.resource, res.resource)

    def test_get_quota_by_project_id_resource_not_found(self):
        utils.create_test_quotas(project_id='123',
                                 resource='test-res',
                                 hard_limit=5)
        self.assertRaises(exception.QuotaNotFound,
                          self.dbapi.get_quota_by_project_id_resource,
                          project_id='123',
                          resource='bad-res')

    def test_get_quota_list(self):
        project_ids = []
        for i in range(1, 6):
            project_id = 'proj-'+str(i)
            utils.create_test_quotas(project_id=project_id)
            project_ids.append(project_id)
        res = self.dbapi.get_quota_list(self.context)
        res_proj_ids = [r.project_id for r in res]
        self.assertEqual(sorted(project_ids), sorted(res_proj_ids))

    def test_get_quota_list_sorted(self):
        project_ids = []
        for i in range(1, 6):
            project_id = 'proj-'+str(i)
            utils.create_test_quotas(project_id=project_id)
            project_ids.append(project_id)
        res = self.dbapi.get_quota_list(self.context, sort_key='project_id')
        res_proj_ids = [r.project_id for r in res]
        self.assertEqual(sorted(project_ids), res_proj_ids)

    def test_get_quota_list_invalid_sort_key(self):
        project_ids = []
        for i in range(1, 6):
            project_id = 'proj-'+str(i)
            utils.create_test_quotas(project_id=project_id)
            project_ids.append(project_id)

        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.get_quota_list,
                          self.context,
                          sort_key='invalid')

    def test_get_quota_list_with_filters(self):
        quota1 = utils.create_test_quotas(project_id='proj-1', resource='res1')
        quota2 = utils.create_test_quotas(project_id='proj-1', resource='res2')
        quota3 = utils.create_test_quotas(project_id='proj-2', resource='res1')

        res = self.dbapi.get_quota_list(
            self.context, filters={'resource': 'res2'})
        self.assertEqual(quota2.project_id, res[0].project_id)

        res = self.dbapi.get_quota_list(
            self.context, filters={'project_id': 'proj-2'})
        self.assertEqual(quota3.project_id, res[0].project_id)

        res = self.dbapi.get_quota_list(
            self.context, filters={'project_id': 'proj-1'})
        self.assertEqual(sorted([quota1.project_id, quota2.project_id]),
                         sorted([r.project_id for r in res]))

    def test_update_quota(self):
        q = utils.create_test_quotas(hard_limit=5,
                                     project_id='1234',
                                     resource='Cluster')

        res = self.dbapi.get_quota_by_project_id_resource('1234', 'Cluster')
        self.assertEqual(q.hard_limit, res.hard_limit)
        self.assertEqual(q.project_id, res.project_id)
        self.assertEqual(q.resource, res.resource)
        quota_dict = {'resource': 'Cluster', 'hard_limit': 15}
        self.dbapi.update_quota('1234', quota_dict)
        res = self.dbapi.get_quota_by_project_id_resource('1234', 'Cluster')
        self.assertEqual(quota_dict['hard_limit'], res.hard_limit)
        self.assertEqual(quota_dict['resource'], res.resource)

    def test_update_quota_not_found(self):
        utils.create_test_quotas(hard_limit=5,
                                 project_id='1234',
                                 resource='Cluster')
        quota_dict = {'resource': 'Cluster', 'hard_limit': 15}
        self.assertRaises(exception.QuotaNotFound,
                          self.dbapi.update_quota,
                          'invalid_proj',
                          quota_dict)

    def test_delete_quota(self):
        q = utils.create_test_quotas(project_id='123',
                                     resource='test-res',
                                     hard_limit=5)
        utils.create_test_quotas(project_id='123',
                                 resource='another-res',
                                 hard_limit=5)
        utils.create_test_quotas(project_id='456',
                                 resource='test-res',
                                 hard_limit=5)
        res = self.dbapi.get_quota_by_project_id_resource('123', 'test-res')
        self.assertEqual(q.hard_limit, res.hard_limit)
        self.assertEqual(q.project_id, res.project_id)
        self.assertEqual(q.resource, res.resource)
        res = self.dbapi.get_quota_list(self.context)
        self.assertEqual(3, len(res))
        self.dbapi.delete_quota(q.project_id, q.resource)
        self.assertRaises(exception.QuotaNotFound,
                          self.dbapi.get_quota_by_project_id_resource,
                          project_id='123',
                          resource='bad-res')
        # Check that we didn't delete any other quotas
        res = self.dbapi.get_quota_list(self.context)
        self.assertEqual(2, len(res))

    def test_delete_quota_that_does_not_exist(self):
        # Make sure that quota does not exist
        self.assertRaises(exception.QuotaNotFound,
                          self.dbapi.get_quota_by_project_id_resource,
                          project_id='123',
                          resource='bad-res')

        # Now try to delete non-existing quota
        self.assertRaises(exception.QuotaNotFound,
                          self.dbapi.delete_quota,
                          project_id='123',
                          resource='bad-res')
