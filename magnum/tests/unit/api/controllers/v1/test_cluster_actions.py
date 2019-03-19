# Licensed under the Apache License, Version 2.0 (the "License");
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

import mock

from magnum.conductor import api as rpcapi
import magnum.conf
from magnum.tests.unit.api import base as api_base
from magnum.tests.unit.objects import utils as obj_utils

CONF = magnum.conf.CONF


class TestClusterActions(api_base.FunctionalTest):

    def setUp(self):
        super(TestClusterActions, self).setUp()
        self.cluster_obj = obj_utils.create_test_cluster(
            self.context, name='cluster_example_A', node_count=3)
        p = mock.patch.object(rpcapi.API, 'cluster_resize_async')
        self.mock_cluster_resize = p.start()
        self.mock_cluster_resize.side_effect = self._sim_rpc_cluster_resize
        self.addCleanup(p.stop)

    def _sim_rpc_cluster_resize(self, cluster, node_count, nodes_to_remove,
                                nodegroup=None, rollback=False):
        cluster.node_count = node_count
        cluster.save()
        return cluster

    def test_resize(self):
        new_node_count = 6
        response = self.post_json('/clusters/%s/actions/resize' %
                                  self.cluster_obj.uuid,
                                  {"node_count": new_node_count},
                                  headers={"Openstack-Api-Version":
                                           "container-infra 1.7"})
        self.assertEqual(202, response.status_code)

        response = self.get_json('/clusters/%s' % self.cluster_obj.uuid)
        self.assertEqual(new_node_count, response['node_count'])
        self.assertEqual(self.cluster_obj.uuid, response['uuid'])
        self.assertEqual(self.cluster_obj.cluster_template_id,
                         response['cluster_template_id'])
