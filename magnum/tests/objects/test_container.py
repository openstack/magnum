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
# from magnum.objects import container
from magnum.tests import base
from magnum.tests import utils


class TestContainer(base.BaseTestCase):
    def setUp(self):
        super(TestContainer, self).setUp()
#        self.db = self.useFixture(utils.Database())
        self.ctx = utils.dummy_context()

        self.data = [{'uuid': 'ce43e347f0b0422825245b3e5f140a81cef6e65b',
                      'name': 'container1',
                      'dns': ['8.8.8.8'],
                      'image': 'ubuntu:latest',
                      'command': ['echo', 'Hello World!'],
                      'ports': [{"container_port": 80, "host_port": 8080}],
                      'env': {'FOO': 'BAR'}}]
#        utils.create_models_from_data(container.Container, self.data,
#            self.ctx)

#    def test_objects_registered(self):
#        self.assertTrue(registry.Container)
#        self.assertTrue(registry.ContainerList)
#
#    def test_get_all(self):
#        lst = container.ContainerList()
#        self.assertEqual(1, len(lst.get_all(self.ctx)))
#
#    def test_check_data(self):
#        ta = container.Container().get_by_id(self.ctx, self.data[0]['id'])
#        for key, value in self.data[0].items():
#            self.assertEqual(value, getattr(ta, key))
