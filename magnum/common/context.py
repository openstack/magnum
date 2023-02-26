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

from eventlet.green import threading
from oslo_context import context

from magnum.common import policy

import magnum.conf

CONF = magnum.conf.CONF


class RequestContext(context.RequestContext):
    """Extends security contexts from the OpenStack common library."""

    def __init__(self, auth_token=None, auth_url=None, domain_id=None,
                 domain_name=None, user_name=None, user_id=None,
                 user_domain_name=None, user_domain_id=None,
                 project_name=None, project_id=None, roles=None,
                 is_admin=None, read_only=False, show_deleted=False,
                 request_id=None, trust_id=None, auth_token_info=None,
                 all_tenants=False, password=None, **kwargs):
        """Stores several additional request parameters:

        :param domain_id: The ID of the domain.
        :param domain_name: The name of the domain.
        :param user_domain_id: The ID of the domain to
                               authenticate a user against.
        :param user_domain_name: The name of the domain to
                                 authenticate a user against.

        """
        super(RequestContext, self).__init__(auth_token=auth_token,
                                             user_id=user_name,
                                             project_id=project_id,
                                             is_admin=is_admin,
                                             read_only=read_only,
                                             show_deleted=show_deleted,
                                             request_id=request_id,
                                             roles=roles)

        self.user_name = user_name
        self.user_id = user_id
        self.project_name = project_name
        self.project_id = project_id
        self.user_domain_id = user_domain_id
        self.user_domain_name = user_domain_name
        self.auth_url = auth_url
        self.auth_token_info = auth_token_info
        self.trust_id = trust_id
        self.all_tenants = all_tenants
        self.password = password
        if is_admin is None:
            self.is_admin = policy.check_is_admin(self)
        else:
            self.is_admin = is_admin

    def to_dict(self):
        value = super(RequestContext, self).to_dict()
        value.update({'auth_token': self.auth_token,
                      'auth_url': self.auth_url,
                      'user_domain_id': self.user_domain_id,
                      'user_domain_name': self.user_domain_name,
                      'user_name': self.user_name,
                      'user_id': self.user_id,
                      'project_name': self.project_name,
                      'project_id': self.project_id,
                      'is_admin': self.is_admin,
                      'read_only': self.read_only,
                      'roles': self.roles,
                      'show_deleted': self.show_deleted,
                      'request_id': self.request_id,
                      'trust_id': self.trust_id,
                      'auth_token_info': self.auth_token_info,
                      'password': self.password,
                      'all_tenants': self.all_tenants})
        return value

    @classmethod
    def from_dict(cls, values):
        return cls(**values)


def make_context(*args, **kwargs):
    return RequestContext(*args, **kwargs)


def make_admin_context(show_deleted=False, all_tenants=False):
    """Create an administrator context.

    :param show_deleted: if True, will show deleted items when query db
    """
    context = RequestContext(user_id=None,
                             project=None,
                             is_admin=True,
                             show_deleted=show_deleted,
                             all_tenants=all_tenants)
    return context


def make_cluster_context(cluster, show_deleted=False):
    """Create a user context based on a cluster's stored Keystone trust.

    :param cluster: the cluster supplying the Keystone trust to use
    :param show_deleted: if True, will show deleted items when query db
    """
    context = RequestContext(user_name=cluster.trustee_username,
                             password=cluster.trustee_password,
                             trust_id=cluster.trust_id,
                             show_deleted=show_deleted,
                             user_domain_id=CONF.trust.trustee_domain_id,
                             user_domain_name=CONF.trust.trustee_domain_name)
    return context


_CTX_STORE = threading.local()
_CTX_KEY = 'current_ctx'


def has_ctx():
    return hasattr(_CTX_STORE, _CTX_KEY)


def ctx():
    return getattr(_CTX_STORE, _CTX_KEY)


def set_ctx(new_ctx):
    if not new_ctx and has_ctx():
        delattr(_CTX_STORE, _CTX_KEY)
        if hasattr(context._request_store, 'context'):
            delattr(context._request_store, 'context')

    if new_ctx:
        setattr(_CTX_STORE, _CTX_KEY, new_ctx)
        setattr(context._request_store, 'context', new_ctx)


def get_admin_context(read_deleted="no"):
    # NOTE(tovin07): This method should only be used when an admin context is
    # necessary for the entirety of the context lifetime.
    return RequestContext(user_id=None,
                          project_id=None,
                          is_admin=True,
                          read_deleted=read_deleted,
                          overwrite=False)
