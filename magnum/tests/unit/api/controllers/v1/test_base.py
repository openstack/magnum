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
from mock import patch
from oslo_utils import timeutils

from magnum.api.controllers.v1 import base as api_base
from magnum.tests import base


class TestK8sResourceBase(base.BaseTestCase):
    def setUp(self):
        super(TestK8sResourceBase, self).setUp()
        self.resource_base = api_base.K8sResourceBase(
            uuid='fe78db47-9a37-4e9f-8572-804a10abc0aa',
            created_at=timeutils.utcnow(),
            updated_at=timeutils.utcnow())

    def test_get_manifest_with_manifest(self):
        expected_manifest = 'expected_manifest'
        self.resource_base.manifest = expected_manifest
        self.resource_base.manifest_url = 'file:///tmp/rc.yaml'

        self.assertEqual(expected_manifest,
                         self.resource_base._get_manifest())

    @patch('magnum.common.urlfetch.get')
    def test_get_manifest_with_manifest_url(self,
                                            mock_urlfetch_get):
        expected_manifest = 'expected_manifest_from_url'
        mock_urlfetch_get.return_value = expected_manifest

        self.resource_base.manifest_url = 'file:///tmp/rc.yaml'

        self.assertEqual(expected_manifest,
                         self.resource_base._get_manifest())
