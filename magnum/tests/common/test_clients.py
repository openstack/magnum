# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from heatclient.v1 import client as heatclient
import mock
from oslo_config import cfg

from magnum.common import clients
from magnum.common import exception
from magnum.tests import base


class ClientsTest(base.BaseTestCase):

    @mock.patch.object(clients.OpenStackClients, 'keystone')
    def test_url_for(self, mock_keystone):
        obj = clients.OpenStackClients(None)
        obj.url_for(service_type='fake_service', endpoint_type='fake_endpoint')

        mock_cat = mock_keystone.return_value.client.service_catalog
        mock_cat.url_for.assert_called_once_with(service_type='fake_service',
                                                 endpoint_type='fake_endpoint')

    @mock.patch.object(heatclient, 'Client')
    @mock.patch.object(clients.OpenStackClients, 'url_for')
    @mock.patch.object(clients.OpenStackClients, 'auth_url')
    def _test_clients_heat(self, expected_region_name, mock_auth, mock_url,
                          mock_call):
        mock_auth.__get__ = mock.Mock(return_value="keystone_url")
        con = mock.MagicMock()
        con.auth_token = "3bcc3d3a03f44e3d8377f9247b0ad155"
        con.auth_url = "keystone_url"
        mock_url.return_value = "url_from_keystone"
        obj = clients.OpenStackClients(con)
        obj._heat = None
        obj.heat()
        mock_call.assert_called_once_with(
            endpoint='url_from_keystone', username=None,
            cert_file=None, token='3bcc3d3a03f44e3d8377f9247b0ad155',
            auth_url='keystone_url', ca_file=None, key_file=None,
            password=None, insecure=False)
        mock_url.assert_called_once_with(service_type='orchestration',
                                         endpoint_type='publicURL',
                                         region_name=expected_region_name)

    def test_clients_heat(self):
        self._test_clients_heat(None)

    def test_clients_heat_region(self):
        cfg.CONF.set_override('region_name', 'myregion', group='heat_client')
        self._test_clients_heat('myregion')

    def test_clients_heat_noauth(self):
        con = mock.MagicMock()
        con.auth_token = None
        con.auth_token_info = None
        auth_url = mock.PropertyMock(name="auth_url",
                                     return_value="keystone_url")
        type(con).auth_url = auth_url
        con.get_url_for = mock.Mock(name="get_url_for")
        con.get_url_for.return_value = "url_from_keystone"
        obj = clients.OpenStackClients(con)
        obj._heat = None
        self.assertRaises(exception.AuthorizationFailure, obj.heat)

    @mock.patch.object(clients.OpenStackClients, 'url_for')
    @mock.patch.object(clients.OpenStackClients, 'auth_url')
    def test_clients_heat_cached(self, mock_auth, mock_url):
        mock_auth.__get__ = mock.Mock(return_value="keystone_url")
        con = mock.MagicMock()
        con.auth_token = "3bcc3d3a03f44e3d8377f9247b0ad155"
        con.auth_url = "keystone_url"
        mock_url.return_value = "url_from_keystone"
        obj = clients.OpenStackClients(con)
        obj._heat = None
        heat = obj.heat()
        heat_cached = obj.heat()
        self.assertEqual(heat, heat_cached)
