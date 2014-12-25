# Copyright 2014 - Rackspace Hosting.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy

import keystoneclient.exceptions as kc_exception
from keystoneclient.v3 import client as kc_v3
from oslo.config import cfg
from oslo.utils import importutils

from magnum.common import context
from magnum.common import exception
from magnum.openstack.common._i18n import _
from magnum.openstack.common import log as logging

LOG = logging.getLogger(__name__)

trust_opts = [
    cfg.ListOpt('trusts_delegated_roles',
                default=['magnum_assembly_update'],
                help=_('Subset of trustor roles to be delegated to magnum.')),
]
cfg.CONF.register_opts(trust_opts)
cfg.CONF.import_opt('auth_uri', 'keystonemiddleware.auth_token',
                    group='keystone_authtoken')


class KeystoneClientV3(object):
    """Keystone client wrapper so we can encapsulate logic in one place."""

    def __init__(self, context):
        # If a trust_id is specified in the context, we immediately
        # authenticate so we can populate the context with a trust token
        # otherwise, we delay client authentication until needed to avoid
        # unnecessary calls to keystone.
        #
        # Note that when you obtain a token using a trust, it cannot be
        # used to reauthenticate and get another token, so we have to
        # get a new trust-token even if context.auth_token is set.
        #
        # - context.auth_url is expected to contain a versioned keystone
        #   path, we will work with either a v2.0 or v3 path
        self.context = context
        self._client = None
        self._admin_client = None

        if self.context.auth_url:
            self.v3_endpoint = self.context.auth_url.replace('v2.0', 'v3')
        else:
            # Import auth_token to have keystone_authtoken settings setup.
            importutils.import_module('keystonemiddleware.auth_token')
            self.v3_endpoint = cfg.CONF.keystone_authtoken.auth_uri.replace(
                'v2.0', 'v3')

        if self.context.trust_id:
            # Create a client with the specified trust_id, this
            # populates self.context.auth_token with a trust-scoped token
            self._client = self._v3_client_init()

    @property
    def client(self):
        if not self._client:
            # Create connection to v3 API
            self._client = self._v3_client_init()
        return self._client

    @property
    def admin_client(self):
        if not self._admin_client:
            # Create admin client connection to v3 API
            admin_creds = self._service_admin_creds()
            c = kc_v3.Client(**admin_creds)
            if c.authenticate():
                self._admin_client = c
            else:
                LOG.error("Admin client authentication failed")
                raise exception.AuthorizationFailure()
        return self._admin_client

    def _v3_client_init(self):
        kwargs = {
            'auth_url': self.v3_endpoint,
            'endpoint': self.v3_endpoint
        }
        # Note try trust_id first, as we can't reuse auth_token in that case
        if self.context.trust_id is not None:
            # We got a trust_id, so we use the admin credentials
            # to authenticate with the trust_id so we can use the
            # trust impersonating the trustor user.
            kwargs.update(self._service_admin_creds())
            kwargs['trust_id'] = self.context.trust_id
            kwargs.pop('project_name')
        elif self.context.auth_token_info is not None:
            # The auth_ref version must be set according to the token version
            if 'access' in self.context.auth_token_info:
                kwargs['auth_ref'] = copy.deepcopy(
                    self.context.auth_token_info['access'])
                kwargs['auth_ref']['version'] = 'v2.0'
                kwargs['auth_ref']['token']['id'] = self.context.auth_token
            elif 'token' in self.context.auth_token_info:
                kwargs['auth_ref'] = copy.deepcopy(
                    self.context.auth_token_info['token'])
                kwargs['auth_ref']['version'] = 'v3'
                kwargs['auth_ref']['auth_token'] = self.context.auth_token
            else:
                LOG.error("Unknown version in auth_token_info")
                raise exception.AuthorizationFailure()
        elif self.context.auth_token is not None:
            kwargs['token'] = self.context.auth_token
            kwargs['project_id'] = self.context.tenant
        else:
            LOG.error(_("Keystone v3 API connection failed, no password "
                        "trust or auth_token!"))
            raise exception.AuthorizationFailure()
        client = kc_v3.Client(**kwargs)
        if 'auth_ref' not in kwargs:
            client.authenticate()
        # If we are authenticating with a trust set the context auth_token
        # with the trust scoped token
        if 'trust_id' in kwargs:
            # Sanity check
            if not client.auth_ref.trust_scoped:
                LOG.error(_("trust token re-scoping failed!"))
                raise exception.AuthorizationFailure()
            # All OK so update the context with the token
            self.context.auth_token = client.auth_ref.auth_token
            self.context.auth_url = self.v3_endpoint
            self.context.user = client.auth_ref.user_id
            self.context.tenant = client.auth_ref.project_id
            self.context.user_name = client.auth_ref.username

        return client

    def _service_admin_creds(self):
        # Import auth_token to have keystone_authtoken settings setup.
        importutils.import_module('keystonemiddleware.auth_token')
        creds = {
            'username': cfg.CONF.keystone_authtoken.admin_user,
            'password': cfg.CONF.keystone_authtoken.admin_password,
            'auth_url': self.v3_endpoint,
            'endpoint': self.v3_endpoint,
            'project_name': cfg.CONF.keystone_authtoken.admin_tenant_name}
        LOG.info('admin creds %s' % creds)
        return creds

    def create_trust_context(self):
        """Create a trust using the trustor identity in the current context.

        Use the trustee as the magnum service user and return a context
        containing the new trust_id.

        If the current context already contains a trust_id, we do nothing
        and return the current context.
        """
        if self.context.trust_id:
            return self.context

        # We need the service admin user ID (not name), as the trustor user
        # can't lookup the ID in keystoneclient unless they're admin
        # workaround this by getting the user_id from admin_client
        trustee_user_id = self.admin_client.auth_ref.user_id
        trustor_user_id = self.client.auth_ref.user_id
        trustor_project_id = self.client.auth_ref.project_id
        roles = cfg.CONF.trusts_delegated_roles
        trust = self.client.trusts.create(trustor_user=trustor_user_id,
                                          trustee_user=trustee_user_id,
                                          project=trustor_project_id,
                                          impersonation=True,
                                          role_names=roles)

        trust_context = context.RequestContext.from_dict(
            self.context.to_dict())
        trust_context.trust_id = trust.id
        return trust_context

    def delete_trust(self, trust_id):
        """Delete the specified trust."""
        try:
            self.client.trusts.delete(trust_id)
        except kc_exception.NotFound:
            pass

    @property
    def auth_token(self):
        return self.client.auth_token
