# -*- encoding: utf-8 -*-
#
# Copyright © 2012 New Dream Network, LLC (DreamHost)
#
# Author: Doug Hellmann <doug.hellmann@dreamhost.com>
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


from oslo.config import cfg
from oslo.utils import importutils
from pecan import hooks

from magnum.common import context
from magnum.conductor import api as conductor_api


class ContextHook(hooks.PecanHook):
    """Configures a request context and attaches it to the request.

    The following HTTP request headers are used:

    X-User-Id or X-User:
        Used for context.user_id.

    X-Tenant-Id or X-Tenant:
        Used for context.tenant.

    X-Auth-Token:
        Used for context.auth_token.

    """

    def before(self, state):
        headers = state.request.headers
        user_id = headers.get('X-User-Id')
        user_id = headers.get('X-User', user_id)
        tenant = state.request.headers.get('X-Tenant-Id')
        tenant = state.request.headers.get('X-Tenant', tenant)
        domain_id = state.request.headers.get('X-User-Domain-Id')
        domain_name = state.request.headers.get('X-User-Domain-Name')
        auth_token = state.request.headers.get('X-Storage-Token')
        auth_token = state.request.headers.get('X-Auth-Token', auth_token)
        auth_token_info = state.request.environ.get('keystone.token_info')

        auth_url = headers.get('X-Auth-Url')
        if auth_url is None:
            importutils.import_module('keystonemiddleware.auth_token')
            auth_url = cfg.CONF.keystone_authtoken.auth_uri

        state.request.context = context.RequestContext(
            auth_token=auth_token,
            auth_url=auth_url,
            auth_token_info=auth_token_info,
            user=user_id,
            tenant=tenant,
            domain_id=domain_id,
            domain_name=domain_name)


class RPCHook(hooks.PecanHook):
    """Attach the rpcapi object to the request so controllers can get to it."""

    def before(self, state):
        state.request.rpcapi = conductor_api.API(context=state.request.context)