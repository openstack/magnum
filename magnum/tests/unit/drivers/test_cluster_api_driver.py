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

from magnum.drivers.cluster_api import driver
from magnum.tests.unit.db import base
from magnum.tests.unit.objects import utils as obj_utils


class ClusterAPIDriverTest(base.DbTestCase):

    def setUp(self):
        super(ClusterAPIDriverTest, self).setUp()
        self.driver = driver.Driver()
        self.cluster_obj = obj_utils.create_test_cluster(
            self.context, name='cluster_example_A',
            master_flavor_id="flavor_small",
            flavor_id="flavor_medium")
        self.cluster_template = self.cluster_obj.cluster_template
        self.cluster_template.labels = {'kube_tag': 'v1.24.3'}
        # TODO(johngarbutt) : complete this testing!!
