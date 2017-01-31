# Copyright 2017 OpenStack Foundation
# All Rights Reserved.
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

from oslo_policy import policy as oslo_policy

from magnum.common import context as magnum_context
from magnum.common import policy

from magnum.tests import base


class TestPolicy(base.TestCase):

    def setUp(self):
        super(TestPolicy, self).setUp()
        rules_dict = {"context_is_admin": "role:admin"}
        self.rules = oslo_policy.Rules.from_dict(rules_dict)

    def test_check_is_admin_with_admin_context_succeeds(self):
        ctx = magnum_context.RequestContext(user='test-user',
                                            project_id='test-project-id',
                                            is_admin=True)
        # explicitly set admin role as this test checks for admin role
        # with the policy engine
        ctx.roles = ['admin']
        self.assertTrue(policy.check_is_admin(ctx))

    def test_check_is_admin_with_user_context_fails(self):
        ctx = magnum_context.RequestContext(user='test-user',
                                            project_id='test-project-id')
        # there is no admin role set in the context, so check_is_admin
        # should return False
        self.assertFalse(policy.check_is_admin(ctx))
