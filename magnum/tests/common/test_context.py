#    Copyright 2015 OpenStack Foundation
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from magnum.common import context
from magnum.tests import base


class ContextTestCase(base.TestCase):

    def test_context(self):
        ctx = context.RequestContext(auth_token='auth_token1',
                                     auth_url='auth_url1',
                                     domain_id='domain_id1',
                                     domain_name='domain_name1',
                                     user='user1', tenant='tenant1',
                                     is_admin=True, is_public_api=True,
                                     read_only=True, show_deleted=True,
                                     request_id='request_id1',
                                     trust_id='trust_id1',
                                     auth_token_info='auth_token_info1')
        self.assertEqual("auth_token1", ctx.auth_token)
        self.assertEqual("auth_url1", ctx.auth_url)
        self.assertEqual("domain_id1", ctx.domain_id)
        self.assertEqual("domain_name1", ctx.domain_name)
        self.assertEqual("user1", ctx.user)
        self.assertEqual("tenant1", ctx.tenant)
        self.assertTrue(ctx.is_admin)
        self.assertTrue(ctx.is_public_api)
        self.assertTrue(ctx.read_only)
        self.assertTrue(ctx.show_deleted)
        self.assertEqual("request_id1", ctx.request_id)
        self.assertEqual("trust_id1", ctx.trust_id)
        self.assertEqual("auth_token_info1", ctx.auth_token_info)

    def test_to_dict_from_dict(self):
        ctx = context.RequestContext(is_admin=True, user='foo',
                                     tenant='foo')
        self.assertTrue(ctx.is_admin)
        self.assertIsNotNone(ctx.user)
        self.assertIsNotNone(ctx.tenant)
        ctx2 = context.RequestContext.from_dict(ctx.to_dict())
        self.assertTrue(ctx2.is_admin)
        self.assertIsNone(ctx2.user)
        self.assertIsNone(ctx2.tenant)