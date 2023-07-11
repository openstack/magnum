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

from oslo_config import cfg

from magnum.tests.unit.api import base as api_base


CONF = cfg.CONF


class PolicyFunctionalTest(api_base.FunctionalTest):
    def setUp(self):
        super(PolicyFunctionalTest, self).setUp()
        CONF.set_override('enforce_scope', True, group='oslo_policy')
        CONF.set_override('enforce_new_defaults', True, group='oslo_policy')
        self.reader_headers = {
            "X-Roles": "reader",
        }
        self.member_headers = {
            "X-Roles": "member",
        }
        self.admin_headers = {
            "X-Roles": "admin",
        }
        self.foo_headers = {
            "X-Roles": "foo",
        }
