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

from unittest import mock

from oslo_config import fixture

from keystoneauth1 import exceptions as ka_exception
from keystoneauth1 import identity as ka_identity

from magnum.common import exception
from magnum.common import keystone
import magnum.conf
from magnum.conf import keystone as ksconf
from magnum.tests import base
from magnum.tests import utils

CONF = magnum.conf.CONF


@mock.patch('magnum.common.keystone.sdk_connection.Connection')
class KeystoneClientTest(base.TestCase):

    def setUp(self):
        super(KeystoneClientTest, self).setUp()
        dummy_url = 'http://server.test:5000/v3'

        self.ctx = utils.dummy_context()
        self.ctx.auth_url = dummy_url
        self.ctx.auth_token = 'abcd1234'

        plugin = keystone.ka_loading.get_plugin_loader('password')
        opts = keystone.ka_loading.get_auth_plugin_conf_options(plugin)
        cfg_fixture = self.useFixture(fixture.Config())
        cfg_fixture.register_opts(opts, group=ksconf.CFG_GROUP)
        self.config(auth_type='password',
                    auth_url=dummy_url,
                    username='fake_user',
                    password='fake_pass',
                    project_name='fake_project',
                    group=ksconf.CFG_GROUP)

        self.config(auth_uri=dummy_url,
                    admin_user='magnum',
                    admin_password='varybadpass',
                    admin_tenant_name='service',
                    group=ksconf.CFG_LEGACY_GROUP)

    def test_client_with_password(self, mock_conn):
        self.ctx.is_admin = True
        self.ctx.auth_token_info = None
        self.ctx.auth_token = None
        ks_client = keystone.KeystoneClientV3(self.ctx)
        ks_client.client
        session = ks_client.session
        auth_plugin = session.auth
        mock_conn.assert_called_once_with(session=session)
        self.assertIsInstance(auth_plugin, ka_identity.Password)

    @mock.patch('magnum.common.keystone.ka_loading')
    @mock.patch('magnum.common.keystone.ka_v3')
    def test_client_with_password_legacy(self,
                                         mock_v3,
                                         mock_loading,
                                         mock_conn):
        self.ctx.is_admin = True
        self.ctx.auth_token_info = None
        self.ctx.auth_token = None
        mock_loading.load_auth_from_conf_options.side_effect = \
            ka_exception.MissingRequiredOptions(mock.MagicMock())
        ks_client = keystone.KeystoneClientV3(self.ctx)
        ks_client.client
        session = ks_client.session
        self.assertWarnsRegex(Warning,
                              '[keystone_authtoken] section is deprecated')
        mock_v3.Password.assert_called_once_with(
            auth_url='http://server.test:5000/v3', password='varybadpass',
            project_domain_id='default', project_name='service',
            user_domain_id='default', username='magnum')
        mock_conn.assert_called_once_with(session=session)

    @mock.patch('magnum.common.keystone.ka_access')
    def test_client_with_access_info(self, mock_access, mock_conn):
        self.ctx.auth_token_info = mock.MagicMock()
        ks_client = keystone.KeystoneClientV3(self.ctx)
        ks_client.client
        session = ks_client.session
        auth_plugin = session.auth
        mock_access.create.assert_called_once_with(body=mock.ANY,
                                                   auth_token='abcd1234')
        mock_conn.assert_called_once_with(session=session)
        self.assertIsInstance(auth_plugin, ka_identity.access.AccessInfoPlugin)

    @mock.patch('magnum.common.keystone.ka_v3')
    def test_client_with_token(self, mock_v3, mock_conn):
        ks_client = keystone.KeystoneClientV3(self.ctx)
        ks_client.client
        session = ks_client.session
        mock_v3.Token.assert_called_once_with(
            auth_url='http://server.test:5000/v3', token='abcd1234')
        mock_conn.assert_called_once_with(session=session)

    def test_client_with_no_credentials(self, mock_conn):
        self.ctx.auth_token = None
        ks_client = keystone.KeystoneClientV3(self.ctx)
        self.assertRaises(exception.AuthorizationFailure,
                          ks_client._get_auth)
        mock_conn.assert_not_called()

    def test_get_validate_region_name(self, mock_conn):
        key = 'region_name'
        val = 'RegionOne'
        CONF.set_override(key, val, 'cinder_client')
        mock_region = mock.MagicMock()
        mock_region.id = 'RegionOne'
        mock_conn.return_value.identity.regions.return_value = [mock_region]
        ks_client = keystone.KeystoneClientV3(self.ctx)
        region_name = ks_client.get_validate_region_name(val)
        self.assertEqual('RegionOne', region_name)

    def test_get_validate_region_name_not_found(self, mock_conn):
        key = 'region_name'
        val = 'region123'
        CONF.set_override(key, val, 'cinder_client')
        ks_client = keystone.KeystoneClientV3(self.ctx)
        self.assertRaises(exception.InvalidParameterValue,
                          ks_client.get_validate_region_name, val)

    def test_get_validate_region_name_is_None(self, mock_conn):
        key = 'region_name'
        val = None
        CONF.set_override(key, val, 'cinder_client')
        ks_client = keystone.KeystoneClientV3(self.ctx)
        self.assertRaises(exception.InvalidParameterValue,
                          ks_client.get_validate_region_name, val)
