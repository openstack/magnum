# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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

import fixtures

from magnum.common import config
import magnum.conf

CONF = magnum.conf.CONF


class ConfFixture(fixtures.Fixture):
    """Fixture to manage global conf settings."""

    def _setUp(self):
        CONF.set_default('host', 'fake-mini')
        CONF.set_default('connection', "sqlite://", group='database')
        CONF.set_default('sqlite_synchronous', False, group='database')
        # Set a fixed trustee_domain_id so that policy.add_policy_attributes()
        # can read it directly from config without making any Keystone call.
        # This matches the value used by the global trustee_domain_id mock in
        # tests/base.py and avoids 'An auth plugin is required' errors in
        # no-auth test configurations.
        CONF.set_default('trustee_domain_id',
                         '12345678-9012-3456-7890-123456789abc',
                         group='trust')
        config.parse_args([], default_config_files=[])
        self.addCleanup(CONF.reset)
