# Copyright 2014 - Rackspace Hosting.
#
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
from oslo.config import cfg

cfg.CONF.import_group('keystone_authtoken',
                      'keystonemiddleware.auth_token')

import keystoneclient.exceptions as kc_exception  # noqa

from magnum.common import exception
from magnum.common import magnum_keystoneclient
from magnum.tests import base
from magnum.tests import utils


@mock.patch('keystoneclient.v3.client.Client')
class KeystoneClientTest(base.BaseTestCase):
    """Test cases for magnum.common.magnum_keystoneclient."""

    def setUp(self):
        super(KeystoneClientTest, self).setUp()
        dummy_url = 'http://server.test:5000/v2.0'

        self.ctx = utils.dummy_context()
        self.ctx.auth_url = dummy_url
        self.ctx.auth_token = 'abcd1234'
        self.ctx.auth_token_info = None

        cfg.CONF.set_override('auth_uri', dummy_url,
                              group='keystone_authtoken')
        cfg.CONF.set_override('admin_user', 'magnum',
                              group='keystone_authtoken')
        cfg.CONF.set_override('admin_password', 'verybadpass',
                              group='keystone_authtoken')
        cfg.CONF.set_override('admin_tenant_name', 'service',
                              group='keystone_authtoken')

    def test_init_v3_token(self, mock_ks):
        """Test creating the client, token auth."""
        self.ctx.tenant = None
        self.ctx.trust_id = None
        magnum_ks_client = magnum_keystoneclient.KeystoneClientV3(self.ctx)
        magnum_ks_client.client
        self.assertIsNotNone(magnum_ks_client._client)
        mock_ks.assert_called_once_with(token='abcd1234', project_id=None,
                                        auth_url='http://server.test:5000/v3',
                                        endpoint='http://server.test:5000/v3')
        mock_ks.return_value.authenticate.assert_called_once_with()

    def test_init_v3_bad_nocreds(self, mock_ks):
        """Test creating the client, no credentials."""
        self.ctx.auth_token = None
        self.ctx.trust_id = None
        self.ctx.username = None
        magnum_ks_client = magnum_keystoneclient.KeystoneClientV3(self.ctx)
        self.assertRaises(exception.AuthorizationFailure,
                          magnum_ks_client._v3_client_init)

    def test_init_trust_token_access(self, mock_ks):
        """Test creating the client, token auth."""
        self.ctx.tenant = 'abcd1234'
        self.ctx.trust_id = None
        self.ctx.auth_token_info = {'access': {'token': {'id': 'placeholder'}}}

        magnum_ks_client = magnum_keystoneclient.KeystoneClientV3(self.ctx)
        magnum_ks_client.client
        self.assertIsNotNone(magnum_ks_client._client)
        mock_ks.assert_called_once_with(auth_ref={'version': 'v2.0',
                                                  'token': {
                                                      'id': 'abcd1234'}},
                                        endpoint='http://server.test:5000/v3',
                                        auth_url='http://server.test:5000/v3')

    def test_init_trust_token_token(self, mock_ks):
        self.ctx.tenant = None
        self.ctx.trust_id = None
        self.ctx.auth_token_info = {'token': {}}

        magnum_ks_client = magnum_keystoneclient.KeystoneClientV3(self.ctx)
        magnum_ks_client.client
        self.assertIsNotNone(magnum_ks_client._client)
        mock_ks.assert_called_once_with(auth_ref={'auth_token': 'abcd1234',
                                                  'version': 'v3'},
                                        endpoint='http://server.test:5000/v3',
                                        auth_url='http://server.test:5000/v3')

    def test_init_trust_token_none(self, mock_ks):
        self.ctx.tenant = None
        self.ctx.trust_id = None
        self.ctx.auth_token_info = {'not_this': 'urg'}

        magnum_ks_client = magnum_keystoneclient.KeystoneClientV3(self.ctx)
        self.assertRaises(exception.AuthorizationFailure,
                          magnum_ks_client._v3_client_init)

    def test_create_trust_context_trust_id(self, mock_ks):
        """Test create_trust_context with existing trust_id."""
        self.ctx.trust_id = 'atrust123'

        magnum_ks_client = magnum_keystoneclient.KeystoneClientV3(self.ctx)
        trust_context = magnum_ks_client.create_trust_context()
        self.assertEqual(self.ctx.to_dict(), trust_context.to_dict())
        mock_ks.assert_called_once_with(username='magnum',
                                        auth_url='http://server.test:5000/v3',
                                        password='verybadpass',
                                        endpoint='http://server.test:5000/v3',
                                        trust_id='atrust123')
        mock_ks.return_value.authenticate.assert_called_once_with()

    def test_create_trust_context_trust_create(self, mock_ks):
        """Test create_trust_context when creating a trust."""
        class FakeTrust(object):
            id = 'atrust123'

        cfg.CONF.set_override('trusts_delegated_roles',
                              ['magnum_assembly_update'])

        getter_mock = mock.PropertyMock(side_effect=['1234', '5678'])
        type(mock_ks.return_value.auth_ref).user_id = getter_mock

        mock_ks.return_value.auth_ref.project_id = '42'
        mock_ks.return_value.trusts.create.return_value = FakeTrust()
        self.ctx.trust_id = None

        magnum_ks_client = magnum_keystoneclient.KeystoneClientV3(self.ctx)
        trust_context = magnum_ks_client.create_trust_context()

        # admin_client and user client
        expected = [mock.call(username='magnum',
                              project_name='service',
                              password='verybadpass',
                              auth_url='http://server.test:5000/v3',
                              endpoint='http://server.test:5000/v3'),
                    mock.call(token='abcd1234',
                              project_id='test_tenant_id',
                              auth_url='http://server.test:5000/v3',
                              endpoint='http://server.test:5000/v3')]

        self.assertEqual(expected, mock_ks.call_args_list)
        self.assertEqual([mock.call(), mock.call()],
                         mock_ks.return_value.authenticate.call_args_list)

        # trust creation
        self.assertEqual('atrust123', trust_context.trust_id)
        mock_ks.return_value.trusts.create.assert_called_once_with(
            trustor_user='5678',
            trustee_user='1234',
            project='42',
            impersonation=True,
            role_names=['magnum_assembly_update'])

    def test_init_admin_client_denied(self, mock_ks):
        """Test the admin_client property, auth failure path."""
        self.ctx.username = None
        self.ctx.password = None
        self.ctx.trust_id = None
        mock_ks.return_value.authenticate.return_value = False

        magnum_ks_client = magnum_keystoneclient.KeystoneClientV3(self.ctx)

        # Define wrapper for property or the property raises the exception
        # outside of the assertRaises which fails the test
        def get_admin_client():
            magnum_ks_client.admin_client

        self.assertRaises(exception.AuthorizationFailure,
                          get_admin_client)

    def test_trust_init_fail(self, mock_ks):
        """Test consuming a trust when initializing, error scoping."""
        self.ctx.username = None
        self.ctx.auth_token = None
        self.ctx.trust_id = 'atrust123'
        mock_ks.return_value.auth_ref.trust_scoped = False

        self.assertRaises(exception.AuthorizationFailure,
                          magnum_keystoneclient.KeystoneClientV3, self.ctx)

    def test_trust_init_token(self, mock_ks):
        """Test trust_id takes precedence when token specified."""
        self.ctx.username = None
        self.ctx.trust_id = 'atrust123'
        magnum_ks_client = magnum_keystoneclient.KeystoneClientV3(self.ctx)
        self.assertIsNotNone(magnum_ks_client._client)
        mock_ks.assert_called_once_with(username='magnum',
                                        auth_url='http://server.test:5000/v3',
                                        password='verybadpass',
                                        endpoint='http://server.test:5000/v3',
                                        trust_id='atrust123')
        mock_ks.return_value.authenticate.assert_called_once_with()

    def test_delete_trust(self, mock_ks):
        """Test delete_trust when deleting trust."""
        mock_ks.return_value.trusts.delete.return_value = None
        magnum_ks_client = magnum_keystoneclient.KeystoneClientV3(self.ctx)
        self.assertIsNone(magnum_ks_client.delete_trust(trust_id='atrust123'))
        mock_ks.return_value.trusts.delete.assert_called_once_with('atrust123')

    def test_delete_trust_not_found(self, mock_ks):
        """Test delete_trust when trust already deleted."""
        mock_delete = mock_ks.return_value.trusts.delete
        mock_delete.side_effect = kc_exception.NotFound()
        magnum_ks_client = magnum_keystoneclient.KeystoneClientV3(self.ctx)
        self.assertIsNone(magnum_ks_client.delete_trust(trust_id='atrust123'))
