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
from magnum.tests.db import base as db_base

from mock import patch


class TestBayModelController(db_base.DbTestCase):
    def simulate_rpc_baymodel_create(self, baymodel):
        baymodel.create()
        return baymodel

    def test_bay_model_api(self):
        with patch.object(api.API, 'baymodel_create') as mock_method:
            # Create a bay_model
            mock_method.side_effect = self.simulate_rpc_baymodel_create
            params = '{"name": "bay_model_example_A", "image_id": "nerdherd"}'
            response = self.app.post('/v1/baymodels',
                                     params=params,
                                     content_type='application/json')
            self.assertEqual(response.status_int, 201)

            # Get all baymodels
            response = self.app.get('/v1/baymodels')
            self.assertEqual(response.status_int, 200)
            self.assertEqual(1, len(response.json))
            c = response.json['baymodels'][0]
            self.assertIsNotNone(c.get('uuid'))
            self.assertEqual('bay_model_example_A', c.get('name'))
            self.assertEqual('nerdherd', c.get('image_id'))

            # Get just the one we created
            response = self.app.get('/v1/baymodels/%s' % c.get('uuid'))
            self.assertEqual(response.status_int, 200)

            # Update the description
            params = [{'path': '/name',
                       'value': 'bay_model_example_B',
                       'op': 'replace'}]
            response = self.app.patch_json('/v1/baymodels/%s' % c.get('uuid'),
                                   params=params)
            self.assertEqual(response.status_int, 200)

            # Delete the bay_model we created
            response = self.app.delete('/v1/baymodels/%s' % c.get('uuid'))
            self.assertEqual(response.status_int, 204)

            response = self.app.get('/v1/baymodels')
            self.assertEqual(response.status_int, 200)
            c = response.json['baymodels']
            self.assertEqual(0, len(c))
