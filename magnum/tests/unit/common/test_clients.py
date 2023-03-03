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

from barbicanclient import client as barbicanclient
from glanceclient import client as glanceclient
from heatclient import client as heatclient
from neutronclient.v2_0 import client as neutronclient
from novaclient import client as novaclient
from unittest import mock

from magnum.common import clients
from magnum.common import exception
import magnum.conf
from magnum.tests import base

CONF = magnum.conf.CONF


class ClientsTest(base.BaseTestCase):

    def setUp(self):
        super(ClientsTest, self).setUp()

        CONF.set_override('auth_uri', 'http://server.test:5000/v2.0',
                          group='keystone_authtoken')

    @mock.patch.object(clients.OpenStackClients, 'keystone')
    def test_url_for(self, mock_keystone):
        obj = clients.OpenStackClients(None)
        obj.url_for(service_type='fake_service', interface='fake_endpoint')

        mock_endpoint = mock_keystone.return_value.session.get_endpoint
        mock_endpoint.assert_called_once_with(service_type='fake_service',
                                              interface='fake_endpoint')

    @mock.patch.object(clients.OpenStackClients, 'keystone')
    def test_magnum_url(self, mock_keystone):
        fake_region = 'fake_region'
        fake_endpoint = 'fake_endpoint'
        CONF.set_override('region_name', fake_region,
                          group='magnum_client')
        CONF.set_override('endpoint_type', fake_endpoint,
                          group='magnum_client')
        obj = clients.OpenStackClients(None)
        obj.magnum_url()

        mock_endpoint = mock_keystone.return_value.session.get_endpoint
        mock_endpoint.assert_called_once_with(region_name=fake_region,
                                              service_type='container-infra',
                                              interface=fake_endpoint)

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
            CONF.heat_client.api_version,
            endpoint='url_from_keystone', username=None,
            cert_file=None, token='3bcc3d3a03f44e3d8377f9247b0ad155',
            auth_url='keystone_url', ca_file=None, key_file=None,
            password=None, insecure=False)
        mock_url.assert_called_once_with(service_type='orchestration',
                                         interface='publicURL',
                                         region_name=expected_region_name)

    def test_clients_heat(self):
        self._test_clients_heat(None)

    def test_clients_heat_region(self):
        CONF.set_override('region_name', 'myregion', group='heat_client')
        self._test_clients_heat('myregion')

    def test_clients_heat_noauth(self):
        con = mock.MagicMock()
        con.auth_token = None
        con.auth_token_info = None
        con.trust_id = None
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

    @mock.patch.object(glanceclient, 'Client')
    @mock.patch.object(clients.OpenStackClients, 'url_for')
    @mock.patch.object(clients.OpenStackClients, 'auth_url')
    def _test_clients_glance(self, expected_region_name, mock_auth, mock_url,
                             mock_call):
        mock_auth.__get__ = mock.Mock(return_value="keystone_url")
        con = mock.MagicMock()
        con.auth_token = "3bcc3d3a03f44e3d8377f9247b0ad155"
        con.auth_url = "keystone_url"
        mock_url.return_value = "url_from_keystone"
        obj = clients.OpenStackClients(con)
        obj._glance = None
        obj.glance()
        mock_call.assert_called_once_with(
            CONF.glance_client.api_version,
            endpoint='url_from_keystone', username=None,
            token='3bcc3d3a03f44e3d8377f9247b0ad155',
            auth_url='keystone_url',
            password=None, cacert=None, cert=None, key=None, insecure=False)
        mock_url.assert_called_once_with(service_type='image',
                                         interface='publicURL',
                                         region_name=expected_region_name)

    def test_clients_glance(self):
        self._test_clients_glance(None)

    def test_clients_glance_region(self):
        CONF.set_override('region_name', 'myregion', group='glance_client')
        self._test_clients_glance('myregion')

    def test_clients_glance_noauth(self):
        con = mock.MagicMock()
        con.auth_token = None
        con.auth_token_info = None
        con.trust_id = None
        auth_url = mock.PropertyMock(name="auth_url",
                                     return_value="keystone_url")
        type(con).auth_url = auth_url
        con.get_url_for = mock.Mock(name="get_url_for")
        con.get_url_for.return_value = "url_from_keystone"
        obj = clients.OpenStackClients(con)
        obj._glance = None
        self.assertRaises(exception.AuthorizationFailure, obj.glance)

    @mock.patch.object(clients.OpenStackClients, 'url_for')
    @mock.patch.object(clients.OpenStackClients, 'auth_url')
    def test_clients_glance_cached(self, mock_auth, mock_url):
        mock_auth.__get__ = mock.Mock(return_value="keystone_url")
        con = mock.MagicMock()
        con.auth_token = "3bcc3d3a03f44e3d8377f9247b0ad155"
        con.auth_url = "keystone_url"
        mock_url.return_value = "url_from_keystone"
        obj = clients.OpenStackClients(con)
        obj._glance = None
        glance = obj.glance()
        glance_cached = obj.glance()
        self.assertEqual(glance, glance_cached)

    @mock.patch.object(clients.OpenStackClients, 'keystone')
    @mock.patch.object(barbicanclient, 'Client')
    @mock.patch.object(clients.OpenStackClients, 'url_for')
    def _test_clients_barbican(self, expected_region_name, mock_url,
                               mock_call, mock_keystone):
        con = mock.MagicMock()
        con.auth_url = "keystone_url"
        mock_url.return_value = "url_from_keystone"
        keystone = mock.MagicMock()
        keystone.session = mock.MagicMock()
        mock_keystone.return_value = keystone
        obj = clients.OpenStackClients(con)
        obj._barbican = None
        obj.barbican()
        mock_call.assert_called_once_with(
            endpoint='url_from_keystone',
            session=keystone.session)

        mock_keystone.assert_called_once_with()
        mock_url.assert_called_once_with(service_type='key-manager',
                                         interface='publicURL',
                                         region_name=expected_region_name)

    def test_clients_barbican(self):
        self._test_clients_barbican(None)

    def test_clients_barbican_region(self):
        CONF.set_override('region_name', 'myregion',
                          group='barbican_client')
        self._test_clients_barbican('myregion')

    def test_clients_barbican_noauth(self):
        con = mock.MagicMock()
        con.auth_token = None
        con.auth_token_info = None
        con.trust_id = None
        auth_url = mock.PropertyMock(name="auth_url",
                                     return_value="keystone_url")
        type(con).auth_url = auth_url
        con.get_url_for = mock.Mock(name="get_url_for")
        con.get_url_for.return_value = "url_from_keystone"
        obj = clients.OpenStackClients(con)
        obj._barbican = None
        self.assertRaises(exception.AuthorizationFailure, obj.barbican)

    @mock.patch.object(clients.OpenStackClients, 'keystone')
    @mock.patch.object(barbicanclient, 'Client')
    @mock.patch.object(clients.OpenStackClients, 'url_for')
    def test_clients_barbican_cached(self, mock_url, mock_call, mock_keystone):
        con = mock.MagicMock()
        con.auth_url = "keystone_url"
        mock_url.return_value = "url_from_keystone"
        keystone = mock.MagicMock()
        keystone.session = mock.MagicMock()
        mock_keystone.return_value = keystone
        obj = clients.OpenStackClients(con)
        obj._barbican = None
        barbican = obj.barbican()
        barbican_cached = obj.barbican()
        self.assertEqual(barbican, barbican_cached)
        mock_call.assert_called_once_with(
            endpoint='url_from_keystone',
            session=keystone.session)

    @mock.patch.object(novaclient, 'Client')
    @mock.patch.object(clients.OpenStackClients, 'keystone')
    @mock.patch.object(clients.OpenStackClients, 'url_for')
    @mock.patch.object(clients.OpenStackClients, 'auth_url')
    def _test_clients_nova(self, expected_region_name, mock_auth, mock_url,
                           mock_keystone, mock_call):
        mock_auth.__get__ = mock.Mock(return_value="keystone_url")
        con = mock.MagicMock()
        keystone = mock.MagicMock()
        keystone.session = mock.MagicMock()
        mock_keystone.return_value = keystone
        con.auth_url = "keystone_url"
        mock_url.return_value = "url_from_keystone"
        obj = clients.OpenStackClients(con)
        obj._nova = None
        obj.nova()
        expected_kwargs = {'session': keystone.session,
                           'endpoint_override': mock_url.return_value,
                           'cacert': None,
                           'insecure': False}
        mock_call.assert_called_once_with(CONF.nova_client.api_version,
                                          **expected_kwargs)
        mock_url.assert_called_once_with(service_type='compute',
                                         interface='publicURL',
                                         region_name=expected_region_name)

    def test_clients_nova(self):
        self._test_clients_nova(None)

    def test_clients_nova_region(self):
        CONF.set_override('region_name', 'myregion', group='nova_client')
        self._test_clients_nova('myregion')

    def test_clients_nova_noauth(self):
        con = mock.MagicMock()
        con.auth_token = None
        con.auth_token_info = None
        con.trust_id = None
        auth_url = mock.PropertyMock(name="auth_url",
                                     return_value="keystone_url")
        type(con).auth_url = auth_url
        con.get_url_for = mock.Mock(name="get_url_for")
        con.get_url_for.return_value = "url_from_keystone"
        obj = clients.OpenStackClients(con)
        obj._nova = None
        self.assertRaises(exception.AuthorizationFailure, obj.nova)

    @mock.patch.object(clients.OpenStackClients, 'url_for')
    @mock.patch.object(clients.OpenStackClients, 'auth_url')
    def test_clients_nova_cached(self, mock_auth, mock_url):
        mock_auth.__get__ = mock.Mock(return_value="keystone_url")
        con = mock.MagicMock()
        con.auth_token = "3bcc3d3a03f44e3d8377f9247b0ad155"
        con.auth_token_info = "auth-token-info"
        con.auth_url = "keystone_url"
        mock_url.return_value = "url_from_keystone"
        obj = clients.OpenStackClients(con)
        obj._nova = None
        nova = obj.nova()
        nova_cached = obj.nova()
        self.assertEqual(nova, nova_cached)

    @mock.patch.object(neutronclient, 'Client')
    @mock.patch.object(clients.OpenStackClients, 'url_for')
    @mock.patch.object(clients.OpenStackClients, 'auth_url')
    def _test_clients_neutron(self, expected_region_name, mock_auth, mock_url,
                              mock_call):
        fake_endpoint_type = 'fake_endpoint_type'
        CONF.set_override('endpoint_type', fake_endpoint_type,
                          group='neutron_client')
        mock_auth.__get__ = mock.Mock(return_value="keystone_url")
        con = mock.MagicMock()
        con.auth_token = "3bcc3d3a03f44e3d8377f9247b0ad155"
        con.auth_url = "keystone_url"
        mock_url.return_value = "url_from_keystone"
        obj = clients.OpenStackClients(con)
        obj._neutron = None
        obj.neutron()
        mock_call.assert_called_once_with(
            endpoint_url='url_from_keystone',
            endpoint_type=fake_endpoint_type,
            auth_url='keystone_url',
            token='3bcc3d3a03f44e3d8377f9247b0ad155',
            ca_cert=None, insecure=False)
        mock_url.assert_called_once_with(service_type='network',
                                         interface=fake_endpoint_type,
                                         region_name=expected_region_name)

    def test_clients_neutron(self):
        self._test_clients_neutron(None)

    def test_clients_neutron_region(self):
        CONF.set_override('region_name', 'myregion',
                          group='neutron_client')
        self._test_clients_neutron('myregion')

    def test_clients_neutron_noauth(self):
        con = mock.MagicMock()
        con.auth_token = None
        con.auth_token_info = None
        con.trust_id = None
        auth_url = mock.PropertyMock(name="auth_url",
                                     return_value="keystone_url")
        type(con).auth_url = auth_url
        con.get_url_for = mock.Mock(name="get_url_for")
        con.get_url_for.return_value = "url_from_keystone"
        obj = clients.OpenStackClients(con)
        obj._neutron = None
        self.assertRaises(exception.AuthorizationFailure, obj.neutron)

    @mock.patch.object(clients.OpenStackClients, 'url_for')
    @mock.patch.object(clients.OpenStackClients, 'auth_url')
    def test_clients_neutron_cached(self, mock_auth, mock_url):
        mock_auth.__get__ = mock.Mock(return_value="keystone_url")
        con = mock.MagicMock()
        con.auth_token = "3bcc3d3a03f44e3d8377f9247b0ad155"
        con.auth_url = "keystone_url"
        mock_url.return_value = "url_from_keystone"
        obj = clients.OpenStackClients(con)
        obj._neutron = None
        neutron = obj.neutron()
        neutron_cached = obj.neutron()
        self.assertEqual(neutron, neutron_cached)
