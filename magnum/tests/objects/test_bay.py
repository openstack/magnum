# Copyright 2014 NEC Corporation.  All rights reserved.
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

# import magnum.objects
# from magnum.objects import bay
from magnum.tests import base
from magnum.tests import utils


class TestBay(base.BaseTestCase):
    def setUp(self):
        super(TestBay, self).setUp()
        self.ctx = utils.dummy_context()

        self.data = [{'uuid': 'ce43e347f0b0422825245b3e5f140a81cef6e65b',
                      'name': 'bay1',
                      'type': 'virt',
                      'ip_address': '10.0.0.3',
                      'external_ip_address': '192.0.2.3'}]
