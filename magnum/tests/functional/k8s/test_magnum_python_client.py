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


from magnum.tests.functional.python_client_base import BaseMagnumClient


class TestListResources(BaseMagnumClient):
    def test_cluster_model_list(self):
        self.assertIsNotNone(self.cs.cluster_templates.list())

    def test_cluster_list(self):
        self.assertIsNotNone(self.cs.clusters.list())
