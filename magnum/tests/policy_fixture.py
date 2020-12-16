# Copyright 2012 Hewlett-Packard Development Company, L.P.
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

import fixtures
from oslo_policy import _parser

from magnum.common import policy as magnum_policy
import magnum.conf

CONF = magnum.conf.CONF


class PolicyFixture(fixtures.Fixture):

    def _setUp(self):
        CONF(args=[], project='magnum')
        magnum_policy._ENFORCER = None
        self.addCleanup(magnum_policy.init().clear)

    def set_rules(self, rules):
        policy = magnum_policy._ENFORCER
        policy.set_rules({k: _parser.parse_rule(v)
                          for k, v in rules.items()})
