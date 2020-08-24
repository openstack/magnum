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

from oslo_utils import uuidutils

from magnum.api.controllers.v1 import certificate as api_cert
from magnum.tests import base
from magnum.tests.unit.api import base as api_base
from magnum.tests.unit.api import utils as api_utils
from magnum.tests.unit.objects import utils as obj_utils


HEADERS = {'OpenStack-API-Version': 'container-infra latest'}


class TestCertObject(base.TestCase):

    @mock.patch('magnum.api.utils.get_resource')
    def test_cert_init(self, mock_get_resource):
        cert_dict = api_utils.cert_post_data()
        mock_cluster = mock.MagicMock()
        mock_cluster.uuid = cert_dict['cluster_uuid']
        mock_get_resource.return_value = mock_cluster

        cert = api_cert.Certificate(**cert_dict)

        self.assertEqual(cert_dict['cluster_uuid'], cert.cluster_uuid)
        self.assertEqual(cert_dict['csr'], cert.csr)
        self.assertEqual(cert_dict['pem'], cert.pem)


class TestGetCaCertificate(api_base.FunctionalTest):

    def setUp(self):
        super(TestGetCaCertificate, self).setUp()
        self.cluster = obj_utils.create_test_cluster(self.context)

        conductor_api_patcher = mock.patch('magnum.conductor.api.API')
        self.conductor_api_class = conductor_api_patcher.start()
        self.conductor_api = mock.MagicMock()
        self.conductor_api_class.return_value = self.conductor_api
        self.addCleanup(conductor_api_patcher.stop)

    def test_get_one(self):
        fake_cert = api_utils.cert_post_data()
        mock_cert = mock.MagicMock()
        mock_cert.as_dict.return_value = fake_cert
        self.conductor_api.get_ca_certificate.return_value = mock_cert

        response = self.get_json('/certificates/%s' % self.cluster.uuid,
                                 headers=HEADERS)

        self.assertEqual(self.cluster.uuid, response['cluster_uuid'])
        # check that bay is still valid as well
        self.assertEqual(self.cluster.uuid, response['bay_uuid'])
        self.assertEqual(fake_cert['csr'], response['csr'])
        self.assertEqual(fake_cert['pem'], response['pem'])

    def test_get_one_by_name(self):
        fake_cert = api_utils.cert_post_data()
        mock_cert = mock.MagicMock()
        mock_cert.as_dict.return_value = fake_cert
        self.conductor_api.get_ca_certificate.return_value = mock_cert

        response = self.get_json('/certificates/%s' % self.cluster.name,
                                 headers=HEADERS)

        self.assertEqual(self.cluster.uuid, response['cluster_uuid'])
        # check that bay is still valid as well
        self.assertEqual(self.cluster.uuid, response['bay_uuid'])
        self.assertEqual(fake_cert['csr'], response['csr'])
        self.assertEqual(fake_cert['pem'], response['pem'])

    def test_get_one_by_name_not_found(self):
        response = self.get_json('/certificates/not_found',
                                 expect_errors=True, headers=HEADERS)

        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_get_one_by_name_multiple_cluster(self):
        obj_utils.create_test_cluster(self.context, name='test_cluster',
                                      uuid=uuidutils.generate_uuid())
        obj_utils.create_test_cluster(self.context, name='test_cluster',
                                      uuid=uuidutils.generate_uuid())

        response = self.get_json('/certificates/test_cluster',
                                 expect_errors=True, headers=HEADERS)

        self.assertEqual(409, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_links(self):
        fake_cert = api_utils.cert_post_data()
        mock_cert = mock.MagicMock()
        mock_cert.as_dict.return_value = fake_cert
        self.conductor_api.get_ca_certificate.return_value = mock_cert

        response = self.get_json('/certificates/%s' % self.cluster.uuid,
                                 headers=HEADERS)

        self.assertIn('links', response.keys())
        self.assertEqual(2, len(response['links']))
        self.assertIn(self.cluster.uuid, response['links'][0]['href'])
        for link in response['links']:
            bookmark = link['rel'] == 'bookmark'
            self.assertTrue(self.validate_link(link['href'],
                                               bookmark=bookmark))


class TestPost(api_base.FunctionalTest):

    def setUp(self):
        super(TestPost, self).setUp()
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

    def test_create_cert(self, ):
        new_cert = api_utils.cert_post_data(cluster_uuid=self.cluster.uuid)
        del new_cert['pem']

        response = self.post_json('/certificates', new_cert, headers=HEADERS)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(new_cert['cluster_uuid'],
                         response.json['cluster_uuid'])
        # verify bay_uuid is still valid as well
        self.assertEqual(new_cert['cluster_uuid'], response.json['bay_uuid'])
        self.assertEqual('fake-pem', response.json['pem'])

    # Test that bay_uuid is still backward compatible
    def test_create_cert_by_bay_name(self, ):
        new_cert = api_utils.cert_post_data(cluster_uuid=self.cluster.uuid)
        del new_cert['pem']
        new_cert['bay_uuid'] = new_cert['cluster_uuid']
        del new_cert['cluster_uuid']

        response = self.post_json('/certificates', new_cert, headers=HEADERS)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(self.cluster.uuid, response.json['cluster_uuid'])
        # verify bay_uuid is still valid as well
        self.assertEqual(self.cluster.uuid, response.json['bay_uuid'])
        self.assertEqual('fake-pem', response.json['pem'])

    def test_create_cert_by_cluster_name(self, ):
        new_cert = api_utils.cert_post_data(cluster_uuid=self.cluster.name)
        del new_cert['pem']

        response = self.post_json('/certificates', new_cert, headers=HEADERS)

        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(self.cluster.uuid, response.json['cluster_uuid'])
        self.assertEqual('fake-pem', response.json['pem'])

    def test_create_cert_cluster_not_found(self, ):
        new_cert = api_utils.cert_post_data(cluster_uuid='not_found')
        del new_cert['pem']

        response = self.post_json('/certificates', new_cert,
                                  expect_errors=True, headers=HEADERS)

        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])


class TestRotateCaCertificate(api_base.FunctionalTest):

    def setUp(self):
        super(TestRotateCaCertificate, self).setUp()
        self.cluster_template = obj_utils.create_test_cluster_template(
            self.context, cluster_distro='fedora-coreos')
        self.cluster = obj_utils.create_test_cluster(self.context)

        conductor_api_patcher = mock.patch('magnum.conductor.api.API')
        self.conductor_api_class = conductor_api_patcher.start()
        self.conductor_api = mock.MagicMock()
        self.conductor_api_class.return_value = self.conductor_api
        self.addCleanup(conductor_api_patcher.stop)

    @mock.patch("magnum.common.policy.enforce")
    def test_rotate_ca_cert(self, mock_policy):
        mock_policy.return_value = True
        fake_cert = api_utils.cert_post_data()
        mock_cert = mock.MagicMock()
        mock_cert.as_dict.return_value = fake_cert
        self.conductor_api.rotate_ca_certificate.return_value = mock_cert

        response = self.patch_json('/certificates/%s' % self.cluster.uuid,
                                   params={}, headers=HEADERS)

        self.assertEqual(202, response.status_code)


class TestRotateCaCertificateNonTls(api_base.FunctionalTest):

    def setUp(self):
        super(TestRotateCaCertificateNonTls, self).setUp()
        self.cluster_template = obj_utils.create_test_cluster_template(
            self.context, tls_disabled=True)
        self.cluster = obj_utils.create_test_cluster(self.context)

        conductor_api_patcher = mock.patch('magnum.conductor.api.API')
        self.conductor_api_class = conductor_api_patcher.start()
        self.conductor_api = mock.MagicMock()
        self.conductor_api_class.return_value = self.conductor_api
        self.addCleanup(conductor_api_patcher.stop)

    @mock.patch("magnum.common.policy.enforce")
    def test_rotate_ca_cert_non_tls(self, mock_policy):
        mock_policy.return_value = True
        fake_cert = api_utils.cert_post_data()
        mock_cert = mock.MagicMock()
        mock_cert.as_dict.return_value = fake_cert
        self.conductor_api.rotate_ca_certificate.return_value = mock_cert

        response = self.patch_json('/certificates/%s' % self.cluster.uuid,
                                   params={}, headers=HEADERS,
                                   expect_errors=True)
        self.assertEqual(400, response.status_code)
        self.assertIn("Rotating the CA certificate on a non-TLS cluster",
                      response.json['errors'][0]['detail'])


class TestCertPolicyEnforcement(api_base.FunctionalTest):

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules({rule: "project_id:non_fake"})
        response = func(*arg, **kwarg)
        self.assertEqual(403, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(
            "Policy doesn't allow %s to be performed." % rule,
            response.json['errors'][0]['detail'])

    def test_policy_disallow_get_one(self):
        cluster = obj_utils.create_test_cluster(self.context)
        self._common_policy_check(
            "certificate:get", self.get_json,
            '/certificates/%s' % cluster.uuid,
            expect_errors=True, headers=HEADERS)

    def test_policy_disallow_create(self):
        cluster = obj_utils.create_test_cluster(self.context)
        cert = api_utils.cert_post_data(cluster_uuid=cluster.uuid)
        self._common_policy_check(
            "certificate:create", self.post_json, '/certificates', cert,
            expect_errors=True, headers=HEADERS)

    def test_policy_disallow_rotate(self):
        cluster = obj_utils.create_test_cluster(self.context)
        self._common_policy_check(
            "certificate:rotate_ca", self.patch_json,
            '/certificates/%s' % cluster.uuid, params={}, expect_errors=True,
            headers=HEADERS)
