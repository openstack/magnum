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

from magnum.conductor import api as rpcapi
from magnum.objects import fields
from magnum.tests.unit.api import base as api_base
from magnum.tests.unit.objects import utils as obj_utils


class CredentialControllerTest(api_base.FunctionalTest):
    headers = {"Openstack-Api-Version": "container-infra latest"}

    def _add_headers(self, kwargs, roles=None):
        if 'headers' not in kwargs:
            kwargs['headers'] = self.headers
            if roles:
                kwargs['headers']['X-Roles'] = ",".join(roles)

    def patch_json(self, *args, **kwargs):
        self._add_headers(kwargs, roles=['member'])
        return super(CredentialControllerTest, self).patch_json(*args,
                                                                **kwargs)


class TestPatch(CredentialControllerTest):
    def setUp(self):
        super(TestPatch, self).setUp()
        self.cluster = obj_utils.create_test_cluster(self.context)
        p = mock.patch.object(rpcapi.API, 'credential_rotate')
        self.mock_rotate = p.start()
        self.mock_rotate.side_effect = self._simulate_credential_rotate
        self.addCleanup(p.stop)
        self.url = f"/credentials/{self.cluster.uuid}"

    def _simulate_credential_rotate(self, cluster):
        cluster.status = fields.ClusterStatus.UPDATE_IN_PROGRESS
        cluster.save()

        cluster.status = fields.ClusterStatus.UPDATE_COMPLETE
        cluster.save()

    def test_rotate(self):
        response = self.patch_json(self.url, params={})
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_code)


class TestCredentialPolicyEnforcement(api_base.FunctionalTest):

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules({rule: "project_id:non_fake"})
        response = func(*arg, **kwarg)
        self.assertEqual(403, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(
            "Policy doesn't allow %s to be performed." % rule,
            response.json['errors'][0]['detail'])

    def test_policy_disallow_rotate(self):
        cluster = obj_utils.create_test_cluster(self.context)
        self._common_policy_check(
            "credential:rotate", self.patch_json,
            '/credentials/%s' % cluster.uuid,
            params={},
            expect_errors=True,
            headers={
                'OpenStack-API-Version': 'container-infra latest',
                "X-Roles": "member"
            }
        )
