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
