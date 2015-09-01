# Copyright 2015 NEC Corporation.  All rights reserved.
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

from oslo_config import cfg
import six

from magnum import opts
from magnum.tests import base


class OptsTestCase(base.BaseTestCase):

    def test_list_opts(self):
        for group_name, opt_list in opts.list_opts():
            self.assertIsInstance(group_name, six.string_types)
            for opt in opt_list:
                self.assertIsInstance(opt, cfg.Opt)
