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

from magnum.conductor.handlers import federation_conductor
from magnum import objects
from magnum.tests.unit.db import base as db_base
from magnum.tests.unit.db import utils


class TestHandler(db_base.DbTestCase):

    def setUp(self):
        super(TestHandler, self).setUp()
        self.handler = federation_conductor.Handler()
        federation_dict = utils.get_test_federation()
        self.federation = objects.Federation(self.context, **federation_dict)
        self.federation.create()

    def test_create_federation(self):
        self.assertRaises(NotImplementedError, self.handler.federation_create,
                          self.context, self.federation, create_timeout=15)

    def test_update_federation(self):
        self.assertRaises(NotImplementedError, self.handler.federation_update,
                          self.context, self.federation, rollback=False)

    def test_delete_federation(self):
        self.assertRaises(NotImplementedError, self.handler.federation_delete,
                          self.context, self.federation.uuid)
