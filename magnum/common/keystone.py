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
from oslo_log import log as logging

from magnum.common import exception
import magnum.conf
from magnum.conf import keystone as ksconf
from magnum.i18n import _

CONF = magnum.conf.CONF
LOG = logging.getLogger(__name__)


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
        conf = CONF[ksconf.CFG_LEGACY_GROUP]
        auth_uri = (getattr(conf, 'www_authenticate_uri', None) or
                    getattr(conf, 'auth_uri', None))
        if auth_uri:
            auth_uri = auth_uri.replace('v2.0', 'v3')
        return auth_uri

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
            CONF, ksconf.CFG_GROUP, auth=auth)
        return session

    def _get_auth(self):
        if self.context.auth_token_info:
            access_info = ka_access.create(body=self.context.auth_token_info,
                                           auth_token=self.context.auth_token)
            auth = ka_access_plugin.AccessInfoPlugin(access_info)
        elif self.context.auth_token:
            auth = ka_v3.Token(auth_url=self.auth_url,
                               token=self.context.auth_token)
        elif self.context.trust_id:
            auth_info = {
                'auth_url': self.auth_url,
                'username': self.context.user_name,
                'password': self.context.password,
                'user_domain_id': self.context.user_domain_id,
                'user_domain_name': self.context.user_domain_name,
                'trust_id': self.context.trust_id
            }

            auth = ka_v3.Password(**auth_info)
        elif self.context.is_admin:
            try:
                auth = ka_loading.load_auth_from_conf_options(
                    CONF, ksconf.CFG_GROUP)
            except ka_exception.MissingRequiredOptions:
                auth = self._get_legacy_auth()
        else:
            msg = ('Keystone API connection failed: no password, '
                   'trust_id or token found.')
            LOG.error(msg)
            raise exception.AuthorizationFailure(client='keystone',
                                                 message='reason %s' % msg)

        return auth

    def _get_legacy_auth(self):
        LOG.warning('Auth plugin and its options for service user '
                    'must be provided in [%(new)s] section. '
                    'Using values from [%(old)s] section is '
                    'deprecated.', {'new': ksconf.CFG_GROUP,
                                    'old': ksconf.CFG_LEGACY_GROUP})

        conf = getattr(CONF, ksconf.CFG_LEGACY_GROUP)

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
                insecure=CONF[ksconf.CFG_LEGACY_GROUP].insecure,
                cacert=CONF[ksconf.CFG_LEGACY_GROUP].cafile,
                key=CONF[ksconf.CFG_LEGACY_GROUP].keyfile,
                cert=CONF[ksconf.CFG_LEGACY_GROUP].certfile)
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
                msg = "Keystone client authentication failed"
                LOG.error(msg)
                raise exception.AuthorizationFailure(client='keystone',
                                                     message='reason: %s' %
                                                             msg)

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
                delegation_depth=0,
                role_names=roles)
        except Exception:
            LOG.exception('Failed to create trust')
            raise exception.TrustCreateFailed(
                trustee_user_id=trustee_user)
        return trust

    def delete_trust(self, context, cluster):
        if cluster.trust_id is None:
            return

        # Trust can only be deleted by the user who creates it. So when
        # other users in the same project want to delete the cluster, we need
        # use the trustee which can impersonate the trustor to delete the
        # trust.
        if context.user_id == cluster.user_id:
            client = self.client
        else:
            auth = ka_v3.Password(auth_url=self.auth_url,
                                  user_id=cluster.trustee_user_id,
                                  password=cluster.trustee_password,
                                  trust_id=cluster.trust_id)

            sess = ka_loading.session.Session().load_from_options(
                auth=auth,
                insecure=CONF[ksconf.CFG_LEGACY_GROUP].insecure,
                cacert=CONF[ksconf.CFG_LEGACY_GROUP].cafile,
                key=CONF[ksconf.CFG_LEGACY_GROUP].keyfile,
                cert=CONF[ksconf.CFG_LEGACY_GROUP].certfile)
            client = kc_v3.Client(session=sess)
        try:
            client.trusts.delete(cluster.trust_id)
        except kc_exception.NotFound:
            pass
        except Exception:
            LOG.exception('Failed to delete trust')
            raise exception.TrustDeleteFailed(trust_id=cluster.trust_id)

    def create_trustee(self, username, password):
        domain_id = self.trustee_domain_id
        try:
            user = self.domain_admin_client.users.create(
                name=username,
                password=password,
                domain=domain_id)
        except Exception:
            LOG.exception('Failed to create trustee')
            raise exception.TrusteeCreateFailed(username=username,
                                                domain_id=domain_id)
        return user

    def delete_trustee(self, trustee_id):
        try:
            self.domain_admin_client.users.delete(trustee_id)
        except kc_exception.NotFound:
            pass
        except Exception:
            LOG.exception('Failed to delete trustee')
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
            LOG.exception('Failed to list regions')
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


def is_octavia_enabled():
    """Check if Octavia service is deployed in the cloud.

    Octavia is already an official LBaaS solution for Openstack
    (https://governance.openstack.org/tc/reference/projects/octavia.html) and
    will deprecate the neutron-lbaas extension starting from Queens release.

    We use Octavia instead of Neutron LBaaS API for load balancing
    functionality for k8s cluster if Octavia service is deployed and enabled
    in the cloud.
    """
    # Put the import here to avoid circular importing.
    from magnum.common import context
    admin_context = context.make_admin_context()
    keystone = KeystoneClientV3(admin_context)

    try:
        octavia_svc = keystone.client.services.list(type='load-balancer')
    except Exception:
        LOG.exception('Failed to list services')
        raise exception.ServicesListFailed()

    # Always assume there is only one load balancing service configured.
    if octavia_svc and octavia_svc[0].enabled:
        return True

    return False
