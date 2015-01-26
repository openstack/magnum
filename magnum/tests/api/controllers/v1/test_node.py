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

from magnum.tests.db import base as db_base


class TestNodeController(db_base.DbTestCase):
    @patch('magnum.common.context.RequestContext')
    def test_node_api(self, mock_RequestContext):
        # Create a node
        params = '{"type": "bare", "image_id": "Fedora"}'
        mock_auth_token = mock_RequestContext.auth_token_info['token']
        mock_auth_token['project']['id'].return_value = 'fake_project'
        mock_auth_token['user']['id'].return_value = 'fake_user'
        response = self.app.post('/v1/nodes',
                                 params=params,
                                 content_type='application/json')
        self.assertEqual(response.status_int, 201)

        # Get all nodes
        response = self.app.get('/v1/nodes')
        self.assertEqual(response.status_int, 200)
        self.assertEqual(1, len(response.json))
        c = response.json['nodes'][0]
        self.assertIsNotNone(c.get('uuid'))
        self.assertEqual('bare', c.get('type'))
        self.assertEqual('Fedora', c.get('image_id'))

        # Get just the one we created
        response = self.app.get('/v1/nodes/%s' % c.get('uuid'))
        self.assertEqual(response.status_int, 200)

        # Delete the node we created
        response = self.app.delete('/v1/nodes/%s' % c.get('uuid'))
        self.assertEqual(response.status_int, 204)

        response = self.app.get('/v1/nodes')
        self.assertEqual(response.status_int, 200)
        c = response.json['nodes']
        self.assertEqual(0, len(c))
