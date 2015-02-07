#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import os
import unittest

from oslo_config import cfg
import pecan
from pecan import testing


cfg.CONF.import_opt('enable_authentication', 'magnum.api.auth')


__all__ = ['FunctionalTest']


class FunctionalTest(unittest.TestCase):
    """Functional tests

    Used for functional tests where you need to test your
    literal application and its integration with the framework.
    """

    def setUp(self):
        cfg.CONF.set_override("enable_authentication", False)
        self.app = testing.load_test_app(os.path.join(
            os.path.dirname(__file__),
            'config.py'
        ))

    def tearDown(self):
        pecan.set_config({}, overwrite=True)
