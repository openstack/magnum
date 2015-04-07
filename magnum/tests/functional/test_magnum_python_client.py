# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
test_magnum
----------------------------------

Tests for `magnum` module.
"""

from magnumclient.openstack.common import cliutils
from magnumclient.v1 import client

from magnum.tests import base


class TestMagnumClient(base.TestCase):
    def setUp(self):
        super(TestMagnumClient, self).setUp()
        self.cs = client.Client(username=cliutils.env('OS_USERNAME'),
                                api_key=cliutils.env('OS_PASSWORD'),
                                project_id=cliutils.env('OS_TENANT_ID'),
                                project_name=cliutils.env('OS_TENANT_NAME'),
                                auth_url=cliutils.env('OS_AUTH_URL'),
                                service_type='container',
                                region_name=cliutils.env('OS_REGION_NAME'),
                                magnum_url=cliutils.env('BYPASS_URL'))

    def test_bay_list(self):
        self.assertEqual([], self.cs.bays.list())
