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

import keystoneclient.exceptions as kc_exception
from keystoneclient.v3 import client as kc_v3
from oslo_config import cfg
from oslo_log import log as logging

from magnum.common import exception
from magnum.i18n import _LE

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

CONF.import_group('keystone_authtoken', 'keystonemiddleware.auth_token')


class KeystoneClientV3(object):
    """Keystone client wrapper so we can encapsulate logic in one place."""

    def __init__(self, context):
        self.context = context
        self._client = None
        self._admin_client = None

    @property
    def auth_url(self):
        v3_auth_url = CONF.keystone_authtoken.auth_uri.replace('v2.0', 'v3')
        return v3_auth_url

    @property
    def auth_token(self):
        return self.client.auth_token

    @property
    def session(self):
        return self.client.session

    @property
    def admin_session(self):
        return self.admin_client.session

    @property
    def client(self):
        if self.context.is_admin:
            return self.admin_client
        else:
            if not self._client:
                self._client = self._get_ks_client()
            return self._client

    def _get_admin_credentials(self):
        credentials = {
            'username': CONF.keystone_authtoken.admin_user,
            'password': CONF.keystone_authtoken.admin_password,
            'project_name': CONF.keystone_authtoken.admin_tenant_name
        }
        return credentials

    @property
    def admin_client(self):
        if not self._admin_client:
            admin_credentials = self._get_admin_credentials()
            self._admin_client = kc_v3.Client(auth_url=self.auth_url,
                                              **admin_credentials)
        return self._admin_client

    @staticmethod
    def _is_v2_valid(auth_token_info):
        return 'access' in auth_token_info

    @staticmethod
    def _is_v3_valid(auth_token_info):
        return 'token' in auth_token_info

    def _get_ks_client(self):
        kwargs = {'auth_url': self.auth_url,
                  'endpoint': self.auth_url}
        if self.context.trust_id:
            kwargs.update(self._get_admin_credentials())
            kwargs['trust_id'] = self.context.trust_id
            kwargs.pop('project_name')
        elif self.context.auth_token_info:
            kwargs['token'] = self.context.auth_token
            if self._is_v2_valid(self.context.auth_token_info):
                LOG.warning('Keystone v2 is deprecated.')
                kwargs['auth_ref'] = self.context.auth_token_info['access']
                kwargs['auth_ref']['version'] = 'v2.0'
            elif self._is_v3_valid(self.context.auth_token_info):
                kwargs['auth_ref'] = self.context.auth_token_info['token']
                kwargs['auth_ref']['version'] = 'v3'
            else:
                LOG.error(_LE('Unknown version in auth_token_info'))
                raise exception.AuthorizationFailure()
        elif self.context.auth_token:
            kwargs['token'] = self.context.auth_token
        else:
            LOG.error(_LE('Keystone v3 API conntection failed, no password '
                          'trust or auth_token'))
            raise exception.AuthorizationFailure()

        return kc_v3.Client(**kwargs)

    def create_trust(self, trustee_user, role_names, impersonation=True):
        trustor_user_id = self.client.auth_ref.user_id
        trustor_project_id = self.client.auth_ref.project_id
        try:
            trust = self.client.trusts.create(
                trustor_user=trustor_user_id,
                project=trustor_project_id,
                trustee_user=trustee_user,
                impersonation=impersonation,
                role_names=role_names)
        except Exception:
            LOG.exception(_LE('Failed to create trust'))
            raise exception.TrustCreateFailed(
                trustee_user_id=trustee_user)
        return trust

    def create_trust_to_admin(self, role_names, impersonation=True):
        trustee_user = self.admin_client.auth_ref.user_id
        return self.create_trust(trustee_user, role_names, impersonation)

    def delete_trust(self, trust_id):
        if trust_id is None:
            return
        try:
            self.client.trusts.delete(trust_id)
        except kc_exception.NotFound:
            pass
        except Exception:
            LOG.exception(_LE('Failed to delete trust'))
            raise exception.TrustDeleteFailed(trust_id=trust_id)
