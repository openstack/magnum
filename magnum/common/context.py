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


class RequestContext(context.RequestContext):
    """Extends security contexts from the OpenStack common library."""

    def __init__(self, auth_token=None, auth_url=None, domain_id=None,
                 domain_name=None, user_name=None, user_id=None,
                 project_name=None, project_id=None, is_admin=False,
                 is_public_api=False, read_only=False, show_deleted=False,
                 request_id=None, trust_id=None, auth_token_info=None,
                 **kwargs):
        """Stores several additional request parameters:

        :param domain_id: The ID of the domain.
        :param domain_name: The name of the domain.
        :param is_public_api: Specifies whether the request should be processed
                              without authentication.

        """
        self.is_public_api = is_public_api
        self.user_name = user_name
        self.user_id = user_id
        self.project_name = project_name
        self.project_id = project_id
        self.domain_id = domain_id
        self.domain_name = domain_name
        self.auth_url = auth_url
        self.auth_token_info = auth_token_info
        self.trust_id = trust_id

        super(RequestContext, self).__init__(auth_token=auth_token,
                                             user=user_name,
                                             tenant=project_name,
                                             is_admin=is_admin,
                                             read_only=read_only,
                                             show_deleted=show_deleted,
                                             request_id=request_id)

    def to_dict(self):
        value = super(RequestContext, self).to_dict()
        value.update({'auth_token': self.auth_token,
                      'auth_url': self.auth_url,
                      'domain_id': self.domain_id,
                      'domain_name': self.domain_name,
                      'user_name': self.user_name,
                      'user_id': self.user_id,
                      'project_name': self.project_name,
                      'project_id': self.project_id,
                      'is_admin': self.is_admin,
                      'is_public_api': self.is_public_api,
                      'read_only': self.read_only,
                      'show_deleted': self.show_deleted,
                      'request_id': self.request_id,
                      'trust_id': self.trust_id,
                      'auth_token_info': self.auth_token_info})
        return value

    @classmethod
    def from_dict(cls, values):
        return cls(**values)


def make_context(*args, **kwargs):
    return RequestContext(*args, **kwargs)


def make_admin_context(show_deleted=False):
    """Create an administrator context.

    :param show_deleted: if True, will show deleted items when query db
    """
    context = RequestContext(user_id=None,
                             project=None,
                             is_admin=True,
                             show_deleted=show_deleted)
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
