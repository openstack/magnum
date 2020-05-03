# Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

from unittest import mock

from magnum.api.controllers.v1 import magnum_services as mservice
from magnum.api import servicegroup
from magnum import objects
from magnum.tests import base
from magnum.tests.unit.api import base as api_base
from magnum.tests.unit.api import utils as apiutils


class TestMagnumServiceObject(base.TestCase):

    def setUp(self):
        super(TestMagnumServiceObject, self).setUp()
        self.rpc_dict = apiutils.mservice_get_data()

    def test_msvc_obj_fields_filtering(self):
        """Test that it does filtering fields """
        self.rpc_dict['fake-key'] = 'fake-value'
        msvco = mservice.MagnumService("up", **self.rpc_dict)
        self.assertNotIn('fake-key', msvco.fields)


class db_rec(object):

    def __init__(self, d):
        self.rec_as_dict = d

    def as_dict(self):
        return self.rec_as_dict


class TestMagnumServiceController(api_base.FunctionalTest):

    @mock.patch("magnum.common.policy.enforce")
    def test_empty(self, mock_policy):
        mock_policy.return_value = True
        response = self.get_json('/mservices')
        self.assertEqual([], response['mservices'])

    def _rpc_api_reply(self, count=1):
        reclist = []
        for i in range(count):
            elem = apiutils.mservice_get_data()
            elem['id'] = i + 1
            rec = db_rec(elem)
            reclist.append(rec)
        return reclist

    @mock.patch("magnum.common.policy.enforce")
    @mock.patch.object(objects.MagnumService, 'list')
    @mock.patch.object(servicegroup.ServiceGroup, 'service_is_up')
    def test_get_one(self, svc_up, rpc_patcher, mock_policy):
        mock_policy.return_value = True
        rpc_patcher.return_value = self._rpc_api_reply()
        svc_up.return_value = "up"

        response = self.get_json('/mservices')
        self.assertEqual(1, len(response['mservices']))
        self.assertEqual(1, response['mservices'][0]['id'])

    @mock.patch("magnum.common.policy.enforce")
    @mock.patch.object(objects.MagnumService, 'list')
    @mock.patch.object(servicegroup.ServiceGroup, 'service_is_up')
    def test_get_many(self, svc_up, rpc_patcher, mock_policy):
        mock_policy.return_value = True
        svc_num = 5
        rpc_patcher.return_value = self._rpc_api_reply(svc_num)
        svc_up.return_value = "up"

        response = self.get_json('/mservices')
        self.assertEqual(svc_num, len(response['mservices']))
        for i in range(svc_num):
            elem = response['mservices'][i]
            self.assertEqual(i + 1, elem['id'])


class TestMagnumServiceEnforcement(api_base.FunctionalTest):

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules({rule: 'project:non_fake'})
        response = func(*arg, **kwarg)
        self.assertEqual(403, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(
            "Policy doesn't allow %s to be performed." % rule,
            response.json['errors'][0]['detail'])

    def test_policy_disallow_get_all(self):
        self._common_policy_check(
            'magnum-service:get_all', self.get_json,
            '/mservices', expect_errors=True)
