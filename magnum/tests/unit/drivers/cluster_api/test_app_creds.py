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
import collections
from unittest import mock

from magnum.common import clients
from magnum.common import utils
from magnum.drivers.cluster_api import app_creds
from magnum.tests.unit.db import base
from magnum.tests.unit.objects import utils as obj_utils


class TestAppCreds(base.DbTestCase):
    def setUp(self):
        super().setUp()
        self.cluster_obj = obj_utils.create_test_cluster(
            self.context,
            name="cluster_example_$A",
            master_flavor_id="flavor_small",
            flavor_id="flavor_medium",
        )

    @mock.patch.object(utils, "get_openstack_ca")
    def test_get_openstack_ca_certificate(self, mock_ca):
        mock_ca.return_value = "cert"

        cert = app_creds.get_openstack_ca_certificate()

        self.assertEqual("cert", cert)

    @mock.patch.object(utils, "get_openstack_ca")
    def test_get_openstack_ca_certificate_get_certify(self, mock_ca):
        mock_ca.return_value = None

        cert = app_creds.get_openstack_ca_certificate()

        self.assertIsNotNone(cert)

    @mock.patch.object(clients, "OpenStackClients")
    def test_create_app_cred(self, mock_client):
        mock_client().cinder_region_name.return_value = "cinder"
        mock_client().url_for.return_value = "http://keystone"
        mock_app_cred = mock_client().keystone().client.application_credentials
        app_cred = collections.namedtuple("appcred", ["id", "secret"])
        mock_app_cred.create.return_value = app_cred("id", "pass")

        app_cred = app_creds._create_app_cred("context", self.cluster_obj)

        expected = {
            "clouds": {
                "openstack": {
                    "auth": {
                        "application_credential_id": "id",
                        "application_credential_secret": "pass",
                        "auth_url": "http://keystone",
                    },
                    "identity_api_version": 3,
                    "interface": "public",
                    "region_name": "cinder",
                    "verify": True,
                }
            }
        }
        self.assertEqual(expected, app_cred)
        mock_client().url_for.assert_called_once_with(
            service_type="identity", interface="public"
        )
        mock_app_cred.create.assert_called_once_with(
            user="fake_user",
            name=f"magnum-{self.cluster_obj.uuid}",
            description=f"Magnum cluster ({self.cluster_obj.uuid})",
        )

    @mock.patch.object(app_creds, "_create_app_cred")
    def test_get_app_cred_yaml(self, mock_create):
        mock_create.return_value = {
            "clouds": {
                "openstack": {"auth": {"application_credential_id": "id"}}
            }
        }

        app_cred = app_creds.get_app_cred_yaml("context", "cluster")

        expected = """\
clouds:
  openstack:
    auth:
      application_credential_id: id
"""
        self.assertEqual(expected, app_cred)
