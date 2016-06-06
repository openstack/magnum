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

from keystoneauth1.access import access as ka_access
from keystoneauth1 import exceptions as ka_exception
from keystoneauth1.identity import access as ka_access_plugin
from keystoneauth1.identity import v3 as ka_v3
from keystoneauth1 import loading as ka_loading
import keystoneclient.exceptions as kc_exception
from keystoneclient.v3 import client as kc_v3
from oslo_config import cfg
from oslo_log import log as logging

from magnum.common import exception
from magnum.i18n import _
from magnum.i18n import _LE
from magnum.i18n import _LW

CONF = cfg.CONF
CFG_GROUP = 'keystone_auth'
CFG_LEGACY_GROUP = 'keystone_authtoken'
LOG = logging.getLogger(__name__)

trust_opts = [
    cfg.StrOpt('trustee_domain_id',
               help=_('Id of the domain to create trustee for bays')),
    cfg.StrOpt('trustee_domain_name',
               help=_('Name of the domain to create trustee for bays')),
    cfg.StrOpt('trustee_domain_admin_id',
               help=_('Id of the admin with roles sufficient to manage users'
                      ' in the trustee_domain')),
    cfg.StrOpt('trustee_domain_admin_name',
               help=_('Name of the admin with roles sufficient to manage users'
                      ' in the trustee_domain')),
    cfg.StrOpt('trustee_domain_admin_domain_id',
               help=_('Id of the domain admin user\'s domain.'
                      ' trustee_domain_id is used by default')),
    cfg.StrOpt('trustee_domain_admin_domain_name',
               help=_('Name of the domain admin user\'s domain.'
                      ' trustee_domain_name is used by default')),
    cfg.StrOpt('trustee_domain_admin_password', secret=True,
               help=_('Password of trustee_domain_admin')),
    cfg.ListOpt('roles',
                default=[],
                help=_('The roles which are delegated to the trustee '
                       'by the trustor'))
]

legacy_session_opts = {
    'certfile': [cfg.DeprecatedOpt('certfile', CFG_LEGACY_GROUP)],
    'keyfile': [cfg.DeprecatedOpt('keyfile', CFG_LEGACY_GROUP)],
    'cafile': [cfg.DeprecatedOpt('cafile', CFG_LEGACY_GROUP)],
    'insecure': [cfg.DeprecatedOpt('insecure', CFG_LEGACY_GROUP)],
    'timeout': [cfg.DeprecatedOpt('timeout', CFG_LEGACY_GROUP)],
}

keystone_auth_opts = (ka_loading.get_auth_common_conf_options() +
                      ka_loading.get_auth_plugin_conf_options('password'))

CONF.register_opts(trust_opts, group='trust')
# FIXME(pauloewerton): remove import of authtoken group and legacy options
# after deprecation period
CONF.import_group('keystone_authtoken', 'keystonemiddleware.auth_token')
ka_loading.register_auth_conf_options(CONF, CFG_GROUP)
ka_loading.register_session_conf_options(CONF, CFG_GROUP,
                                         deprecated_opts=legacy_session_opts)
CONF.set_default('auth_type', default='password', group=CFG_GROUP)


class KeystoneClientV3(object):
    """Keystone client wrapper so we can encapsulate logic in one place."""

    def __init__(self, context):
        self.context = context
        self._client = None
        self._domain_admin_auth = None
        self._domain_admin_session = None
        self._domain_admin_client = None
        self._trustee_domain_id = None
        self._session = None

    @property
    def auth_url(self):
        # FIXME(pauloewerton): auth_url should be retrieved from keystone_auth
        # section by default
        return CONF[CFG_LEGACY_GROUP].auth_uri.replace('v2.0', 'v3')

    @property
    def auth_token(self):
        return self.session.get_token()

    @property
    def session(self):
        if self._session:
            return self._session
        auth = self._get_auth()
        session = self._get_session(auth)
        self._session = session
        return session

    def _get_session(self, auth):
        session = ka_loading.load_session_from_conf_options(
            CONF, CFG_GROUP, auth=auth)
        return session

    def _get_auth(self):
        if self.context.is_admin or self.context.trust_id:
            try:
                auth = ka_loading.load_auth_from_conf_options(CONF, CFG_GROUP)
            except ka_exception.MissingRequiredOptions:
                auth = self._get_legacy_auth()
        elif self.context.auth_token_info:
            access_info = ka_access.create(body=self.context.auth_token_info,
                                           auth_token=self.context.auth_token)
            auth = ka_access_plugin.AccessInfoPlugin(access_info)
        elif self.context.auth_token:
            auth = ka_v3.Token(auth_url=self.auth_url,
                               token=self.context.auth_token)
        else:
            LOG.error(_LE('Keystone API connection failed: no password, '
                          'trust_id or token found.'))
            raise exception.AuthorizationFailure()

        return auth

    def _get_legacy_auth(self):
        LOG.warning(_LW('Auth plugin and its options for service user '
                        'must be provided in [%(new)s] section. '
                        'Using values from [%(old)s] section is '
                        'deprecated.') % {'new': CFG_GROUP,
                                          'old': CFG_LEGACY_GROUP})

        conf = getattr(CONF, CFG_LEGACY_GROUP)

        # FIXME(htruta, pauloewerton): Conductor layer does not have
        # new v3 variables, such as project_name and project_domain_id.
        # The use of admin_* variables is related to Identity API v2.0,
        # which is now deprecated. We should also stop using hard-coded
        # domain info, as well as variables that refer to `tenant`,
        # as they are also v2 related.
        auth = ka_v3.Password(auth_url=self.auth_url,
                              username=conf.admin_user,
                              password=conf.admin_password,
                              project_name=conf.admin_tenant_name,
                              project_domain_id='default',
                              user_domain_id='default')
        return auth

    @property
    def client(self):
        if self._client:
            return self._client
        client = kc_v3.Client(session=self.session,
                              trust_id=self.context.trust_id)
        self._client = client
        return client

    @property
    def domain_admin_auth(self):
        user_domain_id = (
            CONF.trust.trustee_domain_admin_domain_id or
            CONF.trust.trustee_domain_id
        )
        user_domain_name = (
            CONF.trust.trustee_domain_admin_domain_name or
            CONF.trust.trustee_domain_name
        )
        if not self._domain_admin_auth:
            self._domain_admin_auth = ka_v3.Password(
                auth_url=self.auth_url,
                user_id=CONF.trust.trustee_domain_admin_id,
                username=CONF.trust.trustee_domain_admin_name,
                user_domain_id=user_domain_id,
                user_domain_name=user_domain_name,
                domain_id=CONF.trust.trustee_domain_id,
                domain_name=CONF.trust.trustee_domain_name,
                password=CONF.trust.trustee_domain_admin_password)
        return self._domain_admin_auth

    @property
    def domain_admin_session(self):
        if not self._domain_admin_session:
            session = ka_loading.session.Session().load_from_options(
                auth=self.domain_admin_auth,
                insecure=CONF[CFG_LEGACY_GROUP].insecure,
                cacert=CONF[CFG_LEGACY_GROUP].cafile,
                key=CONF[CFG_LEGACY_GROUP].keyfile,
                cert=CONF[CFG_LEGACY_GROUP].certfile)
            self._domain_admin_session = session
        return self._domain_admin_session

    @property
    def domain_admin_client(self):
        if not self._domain_admin_client:
            self._domain_admin_client = kc_v3.Client(
                session=self.domain_admin_session
            )
        return self._domain_admin_client

    @property
    def trustee_domain_id(self):
        if not self._trustee_domain_id:
            try:
                access = self.domain_admin_auth.get_access(
                    self.domain_admin_session
                )
            except kc_exception.Unauthorized:
                LOG.error(_LE("Keystone client authentication failed"))
                raise exception.AuthorizationFailure()

            self._trustee_domain_id = access.domain_id

        return self._trustee_domain_id

    def create_trust(self, trustee_user):
        trustor_user_id = self.session.get_user_id()
        trustor_project_id = self.session.get_project_id()

        # inherit the role of the trustor, unless set CONF.trust.roles
        if CONF.trust.roles:
            roles = CONF.trust.roles
        else:
            roles = self.context.roles

        try:
            trust = self.client.trusts.create(
                trustor_user=trustor_user_id,
                project=trustor_project_id,
                trustee_user=trustee_user,
                impersonation=True,
                role_names=roles)
        except Exception:
            LOG.exception(_LE('Failed to create trust'))
            raise exception.TrustCreateFailed(
                trustee_user_id=trustee_user)
        return trust

    def delete_trust(self, context, bay):
        if bay.trust_id is None:
            return

        # Trust can only be deleted by the user who creates it. So when
        # other users in the same project want to delete the bay, we need
        # use the trustee which can impersonate the trustor to delete the
        # trust.
        if context.user_id == bay.user_id:
            client = self.client
        else:
            auth = ka_v3.Password(auth_url=self.auth_url,
                                  user_id=bay.trustee_user_id,
                                  password=bay.trustee_password,
                                  trust_id=bay.trust_id)

            sess = ka_loading.session.Session().load_from_options(
                auth=auth,
                insecure=CONF[CFG_LEGACY_GROUP].insecure,
                cacert=CONF[CFG_LEGACY_GROUP].cafile,
                key=CONF[CFG_LEGACY_GROUP].keyfile,
                cert=CONF[CFG_LEGACY_GROUP].certfile)
            client = kc_v3.Client(session=sess)
        try:
            client.trusts.delete(bay.trust_id)
        except kc_exception.NotFound:
            pass
        except Exception:
            LOG.exception(_LE('Failed to delete trust'))
            raise exception.TrustDeleteFailed(trust_id=bay.trust_id)

    def create_trustee(self, username, password):
        domain_id = self.trustee_domain_id
        try:
            user = self.domain_admin_client.users.create(
                name=username,
                password=password,
                domain=domain_id)
        except Exception:
            LOG.exception(_LE('Failed to create trustee'))
            raise exception.TrusteeCreateFailed(username=username,
                                                domain_id=domain_id)
        return user

    def delete_trustee(self, trustee_id):
        try:
            self.domain_admin_client.users.delete(trustee_id)
        except kc_exception.NotFound:
            pass
        except Exception:
            LOG.exception(_LE('Failed to delete trustee'))
            raise exception.TrusteeDeleteFailed(trustee_id=trustee_id)

    def get_validate_region_name(self, region_name):
        if region_name is None:
            message = _("region_name needs to be configured in magnum.conf")
            raise exception.InvalidParameterValue(message)
        """matches the region of a public endpoint for the Keystone
        service."""
        try:
            regions = self.client.regions.list()
        except kc_exception.NotFound:
            pass
        except Exception:
            LOG.exception(_LE('Failed to list regions'))
            raise exception.RegionsListFailed()
        region_list = []
        for region in regions:
            region_list.append(region.id)
        if region_name not in region_list:
            raise exception.InvalidParameterValue(_(
                'region_name %(region_name)s is invalid, '
                'expecting a region_name in %(region_name_list)s.') % {
                    'region_name': region_name,
                    'region_name_list': '/'.join(
                        region_list + ['unspecified'])})
        return region_name
