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
from webtest.app import AppError

from magnum.tests.unit.api import utils as apiutils
from magnum.tests.unit.common.policies import base
from magnum.tests.unit.objects import utils as obj_utils

READER_HEADERS = {
    'OpenStack-API-Version': 'container-infra latest',
    "X-Roles": "reader"
}
HEADERS = {
    'OpenStack-API-Version': 'container-infra latest',
    "X-Roles": "member"
}


class TestCertifiactePolicy(base.PolicyFunctionalTest):
    def setUp(self):
        super(TestCertifiactePolicy, self).setUp()
        self.cluster = obj_utils.create_test_cluster(self.context)

        conductor_api_patcher = mock.patch('magnum.conductor.api.API')
        self.conductor_api_class = conductor_api_patcher.start()
        self.conductor_api = mock.MagicMock()
        self.conductor_api_class.return_value = self.conductor_api
        self.addCleanup(conductor_api_patcher.stop)

        self.conductor_api.sign_certificate.side_effect = self._fake_sign

    @staticmethod
    def _fake_sign(cluster, cert):
        cert.pem = 'fake-pem'
        return cert

    def test_get_no_permission(self):
        exc = self.assertRaises(
            AppError,
            self.get_json,
            f"/certificates/{self.cluster.uuid}",
            headers=HEADERS)
        self.assertIn("403 Forbidden", str(exc))

    def test_create_no_permission(self):
        new_cert = apiutils.cert_post_data(cluster_uuid=self.cluster.uuid)
        del new_cert['pem']

        exc = self.assertRaises(
            AppError, self.post_json,
            '/certificates', new_cert,
            headers=READER_HEADERS)
        self.assertIn("403 Forbidden", str(exc))

    def test_update_no_permission(self):
        exc = self.assertRaises(
            AppError, self.patch_json,
            f"/certificates/{self.cluster.uuid}", {},
            headers=READER_HEADERS
        )
        self.assertIn("403 Forbidden", str(exc))
