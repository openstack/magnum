# Copyright 2014
# The Cloudscaling Group, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from magnum.api import app as api_app
from magnum.api import config as api_config
from magnum.api import hooks
from magnum.tests import base


class TestAppConfig(base.BaseTestCase):

    def test_get_pecan_config(self):
        config = api_app.get_pecan_config()

        config_d = dict(config.app)

        self.assertEqual(api_config.app['modules'], config_d['modules'])
        self.assertEqual(api_config.app['root'], config_d['root'])
        self.assertIsInstance(config_d['hooks'][0], hooks.ContextHook)
