# -*- encoding: utf-8 -*-
#
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

import re

from keystonemiddleware import auth_token
from oslo.config import cfg
from pecan import hooks

from magnum.common import context
from magnum.openstack.common._i18n import _
from magnum.openstack.common import log as logging


LOG = logging.getLogger(__name__)

OPT_GROUP_NAME = 'keystone_authtoken'

AUTH_OPTS = [
    cfg.BoolOpt('enable_authentication',
                default=True,
                help='This option enables or disables user authentication '
                'via keystone. Default value is True.'),
]

CONF = cfg.CONF
CONF.register_opts(AUTH_OPTS)

PUBLIC_ENDPOINTS = [
    "^/$"
]


def install(app, conf):
    if conf.get('enable_authentication'):
        return AuthProtocolWrapper(app, conf=dict(conf.get(OPT_GROUP_NAME)))
    else:
        LOG.warning(_('Keystone authentication is disabled by Magnum '
                      'configuration parameter enable_authentication. '
                      'Magnum will not authenticate incoming request. '
                      'In order to enable authentication set '
                      'enable_authentication option to True.'))

    return app


class AuthHelper(object):
    """Helper methods for Auth."""

    def __init__(self):
        endpoints_pattern = '|'.join(pe for pe in PUBLIC_ENDPOINTS)
        self._public_endpoints_regexp = re.compile(endpoints_pattern)

    def is_endpoint_public(self, path):
        return self._public_endpoints_regexp.match(path)


class AuthProtocolWrapper(auth_token.AuthProtocol):
    """A wrapper on Keystone auth_token AuthProtocol.

    Does not perform verification of authentication tokens for pub routes in
    the API. Public routes are those defined by PUBLIC_ENDPOINTS

    """

    def __call__(self, env, start_response):
        path = env.get('PATH_INFO')
        if AUTH.is_endpoint_public(path):
            return self._app(env, start_response)
        return super(AuthProtocolWrapper, self).__call__(env, start_response)


class AuthInformationHook(hooks.PecanHook):

    def before(self, state):
        if not CONF.get('enable_authentication'):
            return
        # Skip authentication for public endpoints
        if AUTH.is_endpoint_public(state.request.path):
            return

        headers = state.request.headers
        user_id = headers.get('X-User-Id')
        user_id = headers.get('X-User', user_id)
        if user_id is None:
            LOG.debug("X-User-Id header was not found in the request")
            raise Exception('Not authorized')

        tenant = state.request.headers.get('X-Tenant-Id')
        tenant = state.request.headers.get('X-Tenant', tenant)
        domain_id = state.request.headers.get('X-User-Domain-Id')
        domain_name = state.request.headers.get('X-User-Domain-Name')

        # Get the auth token
        try:
            recv_auth_token = headers.get('X-Auth-Token',
                                          headers.get(
                                              'X-Storage-Token'))
        except ValueError:
            LOG.debug("No auth token found in the request.")
            raise Exception('Not authorized')
        # auth_url = headers.get('X-Auth-Url')
        # if auth_url is None:
        #     importutils.import_module('keystonemiddleware.auth_token')
        #     auth_url = cfg.CONF.keystone_authtoken.auth_uri

        identity_status = headers.get('X-Identity-Status')
        if identity_status == 'Confirmed':
            ctx = context.RequestContext(auth_token=recv_auth_token,
                                         user=user_id,
                                         tenant=tenant,
                                         domain_id=domain_id,
                                         domain_name=domain_name)
            state.request.security_context = ctx
        else:
            LOG.debug("The provided identity is not confirmed.")
            raise Exception('Not authorized. Identity not confirmed.')
        return


AUTH = AuthHelper()
