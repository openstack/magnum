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
import keystoneclient.exceptions as kc_exception

from magnum.common import exception
from magnum.common import keystone
import magnum.conf
from magnum.conf import keystone as ksconf
from magnum.tests import base
from magnum.tests import utils

CONF = magnum.conf.CONF


@mock.patch('keystoneclient.v3.client.Client')
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

        # Disable global mocking for trustee_domain_id
        self.stop_global(
            'magnum.common.keystone.KeystoneClientV3.trustee_domain_id')

    def tearDown(self):
        # Re-enable global mocking for trustee_domain_id. We need this because
        # mock blows up when trying to stop an already stopped patch (which it
        # will do due to the addCleanup() in base.TestCase).
        self.start_global(
            'magnum.common.keystone.KeystoneClientV3.trustee_domain_id')

        super(KeystoneClientTest, self).tearDown()

    def test_client_with_password(self, mock_ks):
        self.ctx.is_admin = True
        self.ctx.auth_token_info = None
        self.ctx.auth_token = None
        self.ctx.trust_id = None
        ks_client = keystone.KeystoneClientV3(self.ctx)
        ks_client.client
        session = ks_client.session
        auth_plugin = session.auth
        mock_ks.assert_called_once_with(session=session, trust_id=None)
        self.assertIsInstance(auth_plugin, ka_identity.Password)

    @mock.patch('magnum.common.keystone.ka_loading')
    @mock.patch('magnum.common.keystone.ka_v3')
    def test_client_with_password_legacy(self, mock_v3, mock_loading, mock_ks):
        self.ctx.is_admin = True
        self.ctx.auth_token_info = None
        self.ctx.auth_token = None
        self.ctx.trust_id = None
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
        mock_ks.assert_called_once_with(session=session, trust_id=None)

    @mock.patch('magnum.common.keystone.ka_access')
    def test_client_with_access_info(self, mock_access, mock_ks):
        self.ctx.auth_token_info = mock.MagicMock()
        ks_client = keystone.KeystoneClientV3(self.ctx)
        ks_client.client
        session = ks_client.session
        auth_plugin = session.auth
        mock_access.create.assert_called_once_with(body=mock.ANY,
                                                   auth_token='abcd1234')
        mock_ks.assert_called_once_with(session=session, trust_id=None)
        self.assertIsInstance(auth_plugin, ka_identity.access.AccessInfoPlugin)

    @mock.patch('magnum.common.keystone.ka_v3')
    def test_client_with_token(self, mock_v3, mock_ks):
        ks_client = keystone.KeystoneClientV3(self.ctx)
        ks_client.client
        session = ks_client.session
        mock_v3.Token.assert_called_once_with(
            auth_url='http://server.test:5000/v3', token='abcd1234')
        mock_ks.assert_called_once_with(session=session, trust_id=None)

    def test_client_with_no_credentials(self, mock_ks):
        self.ctx.auth_token = None
        ks_client = keystone.KeystoneClientV3(self.ctx)
        self.assertRaises(exception.AuthorizationFailure,
                          ks_client._get_auth)
        mock_ks.assert_not_called()

    def test_delete_trust(self, mock_ks):
        mock_ks.return_value.trusts.delete.return_value = None
        ks_client = keystone.KeystoneClientV3(self.ctx)
        cluster = mock.MagicMock()
        cluster.trust_id = 'atrust123'
        self.assertIsNone(ks_client.delete_trust(self.ctx, cluster))
        mock_ks.return_value.trusts.delete.assert_called_once_with('atrust123')

    def test_delete_trust_not_found(self, mock_ks):
        mock_delete = mock_ks.return_value.trusts.delete
        mock_delete.side_effect = kc_exception.NotFound()
        ks_client = keystone.KeystoneClientV3(self.ctx)
        cluster = mock.MagicMock()
        cluster.trust_id = 'atrust123'
        self.assertIsNone(ks_client.delete_trust(self.ctx, cluster))

    @mock.patch('keystoneauth1.session.Session')
    def test_create_trust_with_all_roles(self, mock_session, mock_ks):
        mock_session.return_value.get_user_id.return_value = '123456'
        mock_session.return_value.get_project_id.return_value = '654321'

        self.ctx.roles = ['role1', 'role2']
        ks_client = keystone.KeystoneClientV3(self.ctx)

        ks_client.create_trust(trustee_user='888888')

        mock_ks.return_value.trusts.create.assert_called_once_with(
            delegation_depth=0,
            trustor_user='123456', project='654321',
            trustee_user='888888', role_names=['role1', 'role2'],
            impersonation=True)

    @mock.patch('keystoneauth1.session.Session')
    def test_create_trust_with_limit_roles(self, mock_session, mock_ks):
        mock_session.return_value.get_user_id.return_value = '123456'
        mock_session.return_value.get_project_id.return_value = '654321'

        self.ctx.roles = ['role1', 'role2']
        ks_client = keystone.KeystoneClientV3(self.ctx)

        CONF.set_override('roles', ['role3'], group='trust')
        ks_client.create_trust(trustee_user='888888')

        mock_ks.return_value.trusts.create.assert_called_once_with(
            delegation_depth=0,
            trustor_user='123456', project='654321',
            trustee_user='888888', role_names=['role3'],
            impersonation=True)

    @mock.patch('magnum.common.keystone.KeystoneClientV3.trustee_domain_id')
    def test_create_trustee(self, mock_tdi, mock_ks):
        expected_username = '_username'
        expected_password = '_password'
        expected_domain = '_expected_trustee_domain_id'
        mock_tdi.__get__ = mock.MagicMock(return_value=expected_domain)

        ks_client = keystone.KeystoneClientV3(self.ctx)
        ks_client.create_trustee(
            username=expected_username,
            password=expected_password,
        )
        mock_ks.return_value.users.create.assert_called_once_with(
            name=expected_username,
            password=expected_password,
            domain=expected_domain,
        )

    @mock.patch('magnum.common.keystone.KeystoneClientV3.domain_admin_auth')
    @mock.patch('magnum.common.keystone.KeystoneClientV3.domain_admin_session')
    def test_trustee_domain_id(self, mock_session, mock_auth, mock_ks):
        expected_domain_id = '_expected_domain_id'
        _mock_session = mock.MagicMock()
        mock_session.__get__ = mock.MagicMock(return_value=_mock_session)
        _mock_auth = mock.MagicMock()
        mock_auth.__get__ = mock.MagicMock(return_value=_mock_auth)
        mock_access = mock.MagicMock()
        mock_access.domain_id = expected_domain_id
        _mock_auth.get_access.return_value = mock_access

        ks_client = keystone.KeystoneClientV3(self.ctx)
        self.assertEqual(expected_domain_id, ks_client.trustee_domain_id)

        _mock_auth.get_access.assert_called_once_with(
            _mock_session
        )

    def test_get_validate_region_name(self, mock_ks):
        key = 'region_name'
        val = 'RegionOne'
        CONF.set_override(key, val, 'cinder_client')
        mock_region = mock.MagicMock()
        mock_region.id = 'RegionOne'
        mock_ks.return_value.regions.list.return_value = [mock_region]
        ks_client = keystone.KeystoneClientV3(self.ctx)
        region_name = ks_client.get_validate_region_name(val)
        self.assertEqual('RegionOne', region_name)

    def test_get_validate_region_name_not_found(self, mock_ks):
        key = 'region_name'
        val = 'region123'
        CONF.set_override(key, val, 'cinder_client')
        ks_client = keystone.KeystoneClientV3(self.ctx)
        self.assertRaises(exception.InvalidParameterValue,
                          ks_client.get_validate_region_name, val)

    def test_get_validate_region_name_is_None(self, mock_ks):
        key = 'region_name'
        val = None
        CONF.set_override(key, val, 'cinder_client')
        ks_client = keystone.KeystoneClientV3(self.ctx)
        self.assertRaises(exception.InvalidParameterValue,
                          ks_client.get_validate_region_name, val)
