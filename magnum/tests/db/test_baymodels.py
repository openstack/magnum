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

"""Tests for manipulating Baymodel via the DB API"""

import six

from magnum.common import exception
from magnum.common import utils as magnum_utils
from magnum.tests.db import base
from magnum.tests.db import utils


class DbBaymodelTestCase(base.DbTestCase):

    def _create_test_baymodel(self, **kwargs):
        bm = utils.get_test_baymodel(**kwargs)
        self.dbapi.create_baymodel(bm)
        return bm

    def test_get_baymodel_list(self):
        uuids = []
        for i in range(1, 6):
            bm = utils.get_test_baymodel(id=i,
                                         uuid=magnum_utils.generate_uuid())
            self.dbapi.create_baymodel(bm)
            uuids.append(six.text_type(bm['uuid']))
        res = self.dbapi.get_baymodel_list()
        res_uuids = [r.uuid for r in res]
        self.assertEqual(uuids.sort(), res_uuids.sort())

    def test_get_baymodel_by_id(self):
        bm = self._create_test_baymodel()
        baymodel = self.dbapi.get_baymodel_by_id(bm['id'])
        self.assertEqual(bm['uuid'], baymodel.uuid)

    def test_get_baymodel_by_uuid(self):
        bm = self._create_test_baymodel()
        baymodel = self.dbapi.get_baymodel_by_uuid(bm['uuid'])
        self.assertEqual(bm['id'], baymodel.id)

    def test_get_baymodel_that_does_not_exist(self):
        self.assertRaises(exception.BayModelNotFound,
                          self.dbapi.get_baymodel_by_id, 666)

    def test_update_baymodel(self):
        bm = self._create_test_baymodel()
        res = self.dbapi.update_baymodel(bm['id'], {'name': 'updated-model'})
        self.assertEqual('updated-model', res.name)

    def test_update_baymodel_that_does_not_exist(self):
        self.assertRaises(exception.BayModelNotFound,
                          self.dbapi.update_baymodel, 666, {'name': ''})

    def test_update_baymodel_uuid(self):
        bm = self._create_test_baymodel()
        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.update_baymodel, bm['id'],
                          {'uuid': 'hello'})

    def test_destroy_baymodel(self):
        bm = self._create_test_baymodel()
        self.dbapi.destroy_baymodel(bm['id'])
        self.assertRaises(exception.BayModelNotFound,
                          self.dbapi.get_baymodel_by_id, bm['id'])

    def test_destroy_baymodel_that_does_not_exist(self):
        self.assertRaises(exception.BayModelNotFound,
                          self.dbapi.destroy_baymodel, 666)

    def test_create_baymodel_already_exists(self):
        uuid = magnum_utils.generate_uuid()
        self._create_test_baymodel(id=1, uuid=uuid)
        self.assertRaises(exception.BayModelAlreadyExists,
                          self._create_test_baymodel,
                          id=2, uuid=uuid)