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

import mock
from oslo_config import cfg

cfg.CONF.import_group('keystone_authtoken',
                      'keystonemiddleware.auth_token')

import keystoneclient.exceptions as kc_exception

from magnum.common import exception
from magnum.common import keystone
from magnum.tests import base
from magnum.tests import utils


@mock.patch('keystoneclient.v3.client.Client')
class KeystoneClientTest(base.BaseTestCase):

    def setUp(self):
        super(KeystoneClientTest, self).setUp()
        dummy_url = 'http://server.test:5000/v2.0'

        self.ctx = utils.dummy_context()
        self.ctx.auth_url = dummy_url
        self.ctx.auth_token = 'abcd1234'

        cfg.CONF.set_override('auth_uri', dummy_url,
                              group='keystone_authtoken')
        cfg.CONF.set_override('admin_user', 'magnum',
                              group='keystone_authtoken')
        cfg.CONF.set_override('admin_password', 'verybadpass',
                              group='keystone_authtoken')
        cfg.CONF.set_override('admin_tenant_name', 'service',
                              group='keystone_authtoken')

    def test_client_with_token(self, mock_ks):
        ks_client = keystone.KeystoneClientV3(self.ctx)
        ks_client.client
        self.assertIsNotNone(ks_client._client)
        mock_ks.assert_called_once_with(token='abcd1234',
                                        auth_url='http://server.test:5000/v3',
                                        endpoint='http://server.test:5000/v3')

    def test_client_with_no_credentials(self, mock_ks):
        self.ctx.auth_token = None
        ks_client = keystone.KeystoneClientV3(self.ctx)
        self.assertRaises(exception.AuthorizationFailure,
                          ks_client._get_ks_client)

    def test_client_with_v2_auth_token_info(self, mock_ks):
        self.ctx.auth_token_info = {'access': {}}

        ks_client = keystone.KeystoneClientV3(self.ctx)
        ks_client.client
        self.assertIsNotNone(ks_client._client)
        mock_ks.assert_called_once_with(auth_ref={'version': 'v2.0'},
                                        auth_url='http://server.test:5000/v3',
                                        endpoint='http://server.test:5000/v3',
                                        token='abcd1234')

    def test_client_with_v3_auth_token_info(self, mock_ks):
        self.ctx.auth_token_info = {'token': {}}

        ks_client = keystone.KeystoneClientV3(self.ctx)
        ks_client.client
        self.assertIsNotNone(ks_client._client)
        mock_ks.assert_called_once_with(auth_ref={'version': 'v3'},
                                        auth_url='http://server.test:5000/v3',
                                        endpoint='http://server.test:5000/v3',
                                        token='abcd1234')

    def test_client_with_invalid_auth_token_info(self, mock_ks):
        self.ctx.auth_token_info = {'not_this': 'urg'}

        ks_client = keystone.KeystoneClientV3(self.ctx)
        self.assertRaises(exception.AuthorizationFailure,
                          ks_client._get_ks_client)

    def test_client_with_is_admin(self, mock_ks):
        self.ctx.is_admin = True
        ks_client = keystone.KeystoneClientV3(self.ctx)
        ks_client.client

        self.assertIsNone(ks_client._client)
        self.assertIsNotNone(ks_client._admin_client)
        mock_ks.assert_called_once_with(auth_url='http://server.test:5000/v3',
                                        username='magnum',
                                        password='verybadpass',
                                        project_name='service')

    def test_delete_trust(self, mock_ks):
        mock_ks.return_value.trusts.delete.return_value = None
        ks_client = keystone.KeystoneClientV3(self.ctx)
        self.assertIsNone(ks_client.delete_trust(trust_id='atrust123'))
        mock_ks.return_value.trusts.delete.assert_called_once_with('atrust123')

    def test_delete_trust_not_found(self, mock_ks):
        mock_delete = mock_ks.return_value.trusts.delete
        mock_delete.side_effect = kc_exception.NotFound()
        ks_client = keystone.KeystoneClientV3(self.ctx)
        self.assertIsNone(ks_client.delete_trust(trust_id='atrust123'))

    def test_create_trust_with_all_roles(self, mock_ks):
        mock_ks.return_value.auth_ref.user_id = '123456'
        mock_ks.return_value.auth_ref.project_id = '654321'

        self.ctx.roles = ['role1', 'role2']
        ks_client = keystone.KeystoneClientV3(self.ctx)

        ks_client.create_trust(trustee_user='888888')

        mock_ks.return_value.trusts.create.assert_called_once_with(
            trustor_user='123456', project='654321',
            trustee_user='888888', role_names=['role1', 'role2'],
            impersonation=True)

    def test_create_trust_with_limit_roles(self, mock_ks):
        mock_ks.return_value.auth_ref.user_id = '123456'
        mock_ks.return_value.auth_ref.project_id = '654321'

        self.ctx.roles = ['role1', 'role2']
        ks_client = keystone.KeystoneClientV3(self.ctx)

        cfg.CONF.set_override('roles', ['role3'], group='trust')
        ks_client.create_trust(trustee_user='888888')

        mock_ks.return_value.trusts.create.assert_called_once_with(
            trustor_user='123456', project='654321',
            trustee_user='888888', role_names=['role3'],
            impersonation=True)

    def test_get_validate_region_name(self, mock_ks):
        key = 'region_name'
        val = 'RegionOne'
        cfg.CONF.set_override(key, val, 'cinder_client')
        mock_region = mock.MagicMock()
        mock_region.id = 'RegionOne'
        mock_ks.return_value.regions.list.return_value = [mock_region]
        ks_client = keystone.KeystoneClientV3(self.ctx)
        region_name = ks_client.get_validate_region_name(val)
        self.assertEqual('RegionOne', region_name)

    def test_get_validate_region_name_not_found(self, mock_ks):
        key = 'region_name'
        val = 'region123'
        cfg.CONF.set_override(key, val, 'cinder_client')
        ks_client = keystone.KeystoneClientV3(self.ctx)
        self.assertRaises(exception.InvalidParameterValue,
                          ks_client.get_validate_region_name, val)

    def test_get_validate_region_name_is_None(self, mock_ks):
        key = 'region_name'
        val = None
        cfg.CONF.set_override(key, val, 'cinder_client')
        ks_client = keystone.KeystoneClientV3(self.ctx)
        self.assertRaises(exception.InvalidParameterValue,
                          ks_client.get_validate_region_name, val)
