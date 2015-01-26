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
from magnum.conductor import api
from magnum import objects
from magnum.tests.db import base as db_base
from magnum.tests.db import utils as db_utils

from mock import patch


class TestBayController(db_base.DbTestCase):
    def simulate_rpc_bay_create(self, bay):
        bay.create()
        return bay

    def mock_bay_destroy(self, bay_uuid):
        bay = objects.Bay.get_by_uuid({}, bay_uuid)
        bay.destroy()

    @patch('magnum.common.context.RequestContext')
    def test_bay_api(self, mock_RequestContext):
        with patch.object(api.API, 'bay_create') as mock_method:
            # Create a baymodel
            baymodel = db_utils.get_test_baymodel()
            self.dbapi.create_baymodel(baymodel)

            # Create a bay
            mock_method.side_effect = self.simulate_rpc_bay_create
            mock_auth_token = mock_RequestContext.auth_token_info['token']
            mock_auth_token['project']['id'].return_value = 'fake_project'
            mock_auth_token['user']['id'].return_value = 'fake_user'
            params = '{"name": "bay_example_A", "baymodel_id": "12345", \
                "node_count": "3", "baymodel_id": "%s"}' % baymodel['uuid']
            response = self.app.post('/v1/bays',
                                     params=params,
                                     content_type='application/json')
            self.assertEqual(response.status_int, 201)

            # Get all bays
            response = self.app.get('/v1/bays')
            self.assertEqual(response.status_int, 200)
            self.assertEqual(1, len(response.json))
            c = response.json['bays'][0]
            self.assertIsNotNone(c.get('uuid'))
            self.assertEqual('bay_example_A', c.get('name'))
            self.assertEqual(3, c.get('node_count'))

            # Get just the one we created
            response = self.app.get('/v1/bays/%s' % c.get('uuid'))
            self.assertEqual(response.status_int, 200)

            # Update the description
            params = [{'path': '/name',
                       'value': 'bay_example_B',
                       'op': 'replace'}]
            response = self.app.patch_json('/v1/bays/%s' % c.get('uuid'),
                                   params=params)
            self.assertEqual(response.status_int, 200)

        with patch.object(api.API, 'bay_delete') as mock_method:
            mock_method.side_effect = self.mock_bay_destroy
            # Delete the bay we created
            response = self.app.delete('/v1/bays/%s' % c.get('uuid'))
            self.assertEqual(response.status_int, 204)

            response = self.app.get('/v1/bays')
            self.assertEqual(response.status_int, 200)
            c = response.json['bays']
            self.assertEqual(0, len(c))
