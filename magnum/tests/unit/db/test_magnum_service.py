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

"""Tests for manipulating MagnumService via the DB API"""

from magnum.common import context  # NOQA
from magnum.common import exception
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils


class DbMagnumServiceTestCase(base.DbTestCase):

    def test_create_magnum_service(self):
        utils.create_test_magnum_service()

    def test_create_magnum_service_failure_for_dup(self):
        ms = utils.create_test_magnum_service()
        res = self.dbapi.get_magnum_service_by_host_and_binary(
            ms['host'], ms['binary'])
        self.assertEqual(ms.id, res.id)

    def test_get_magnum_service_by_host_and_binary(self):
        ms = utils.create_test_magnum_service()
        res = self.dbapi.get_magnum_service_by_host_and_binary(
            ms['host'], ms['binary'])
        self.assertEqual(ms.id, res.id)

    def test_get_magnum_service_by_host_and_binary_failure(self):
        utils.create_test_magnum_service()
        res = self.dbapi.get_magnum_service_by_host_and_binary(
            'fakehost1', 'fake-bin1')
        self.assertIsNone(res)

    def test_update_magnum_service(self):
        ms = utils.create_test_magnum_service()
        d2 = True
        update = {'disabled': d2}
        ms1 = self.dbapi.update_magnum_service(ms['id'], update)
        self.assertEqual(ms['id'], ms1['id'])
        self.assertEqual(d2, ms1['disabled'])
        res = self.dbapi.get_magnum_service_by_host_and_binary(
            'fakehost', 'fake-bin')
        self.assertEqual(ms1['id'], res['id'])
        self.assertEqual(d2, res['disabled'])

    def test_update_magnum_service_failure(self):
        ms = utils.create_test_magnum_service()
        fake_update = {'fake_field': 'fake_value'}
        self.assertRaises(exception.MagnumServiceNotFound,
                          self.dbapi.update_magnum_service,
                          ms['id'] + 1, fake_update)

    def test_destroy_magnum_service(self):
        ms = utils.create_test_magnum_service()
        res = self.dbapi.get_magnum_service_by_host_and_binary(
            'fakehost', 'fake-bin')
        self.assertEqual(res['id'], ms['id'])
        self.dbapi.destroy_magnum_service(ms['id'])
        res = self.dbapi.get_magnum_service_by_host_and_binary(
            'fakehost', 'fake-bin')
        self.assertIsNone(res)

    def test_destroy_magnum_service_failure(self):
        ms = utils.create_test_magnum_service()
        self.assertRaises(exception.MagnumServiceNotFound,
                          self.dbapi.destroy_magnum_service,
                          ms['id'] + 1)

    def test_get_magnum_service_list(self):
        fake_ms_params = {
            'report_count': 1010,
            'host': 'FakeHost',
            'binary': 'FakeBin',
            'disabled': False,
            'disabled_reason': 'FakeReason'
        }
        utils.create_test_magnum_service(**fake_ms_params)
        res = self.dbapi.get_magnum_service_list()
        self.assertEqual(1, len(res))
        res = res[0]
        for k, v in fake_ms_params.items():
            self.assertEqual(res[k], v)

        fake_ms_params['binary'] = 'FakeBin1'
        fake_ms_params['disabled'] = True
        utils.create_test_magnum_service(**fake_ms_params)
        res = self.dbapi.get_magnum_service_list(disabled=True)
        self.assertEqual(1, len(res))
        res = res[0]
        for k, v in fake_ms_params.items():
            self.assertEqual(res[k], v)
