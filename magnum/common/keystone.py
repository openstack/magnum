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
from keystoneauth1.identity import access as ka_access_plugin
from keystoneauth1.identity import v3 as ka_v3
from keystoneauth1 import loading as ka_loading
from openstack import connection as sdk_connection
from openstack import exceptions as sdk_exceptions
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
        self._session = None

    @property
    def auth_url(self):
        auth_url = getattr(CONF[ksconf.CFG_GROUP], 'auth_url', None)
        if not auth_url:
            auth_url = getattr(CONF[ksconf.CFG_LEGACY_GROUP],
                               'www_authenticate_uri', None)
        return auth_url

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
        elif self.context.is_admin:
            auth = ka_loading.load_auth_from_conf_options(
                CONF, ksconf.CFG_GROUP)
        else:
            msg = ('Keystone API connection failed: no password or token '
                   'found.')
            LOG.error(msg)
            raise exception.AuthorizationFailure(client='keystone',
                                                 message='reason %s' % msg)

        return auth

    @property
    def client(self):
        if self._client:
            return self._client
        conn = sdk_connection.Connection(session=self.session)
        self._client = conn.identity
        return self._client

    def get_validate_region_name(self, region_name):
        if region_name is None:
            message = _("region_name needs to be configured in magnum.conf")
            raise exception.InvalidParameterValue(message)
        """matches the region of a public endpoint for the Keystone
        service."""
        regions = []
        try:
            regions = list(self.client.regions())
        except sdk_exceptions.NotFoundException:
            pass
        except Exception:
            LOG.exception('Failed to list regions')
            raise exception.RegionsListFailed()
        region_list = [r.id for r in regions]
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
        octavia_svc = list(keystone.client.services(type='load-balancer'))
    except Exception:
        LOG.exception('Failed to list services')
        raise exception.ServicesListFailed()

    # Always assume there is only one load balancing service configured.
    if octavia_svc and octavia_svc[0].is_enabled:
        return True

    return False
