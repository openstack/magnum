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


class TestRCController(db_base.DbTestCase):
    def mock_rc_create(self, rc):
        rc.create()
        return rc

    def mock_rc_destroy(self, rc):
        rc.destroy()

    def test_rc_api(self):
        with patch.object(api.API, 'rc_create') as mock_method:
            mock_method.side_effect = self.mock_rc_create
            # Create a replication controller
            params = '{"name": "rc_example_A", "images": ["ubuntu"],' \
                     '"selector": {"foo": "foo1"}, "replicas": 2,' \
                     '"rc_definition_url": "http://172.17.1.2/rc.json"}'
            response = self.app.post('/v1/rcs',
                                     params=params,
                                     content_type='application/json')
            self.assertEqual(response.status_int, 201)

            # Get all rcs
            response = self.app.get('/v1/rcs')
            self.assertEqual(response.status_int, 200)
            self.assertEqual(1, len(response.json))
            c = response.json['rcs'][0]
            self.assertIsNotNone(c.get('uuid'))
            self.assertEqual('rc_example_A', c.get('name'))
            self.assertEqual(['ubuntu'], c.get('images'))
            self.assertEqual('foo1', c.get('selector')['foo'])

            # Get just the one we created
            response = self.app.get('/v1/rcs/%s' % c.get('uuid'))
            self.assertEqual(response.status_int, 200)

        with patch.object(api.API, 'rc_delete') as mock_method:
            mock_method.side_effect = self.mock_rc_destroy
            # Delete the rc we created
            response = self.app.delete('/v1/rcs/%s' % c.get('uuid'))
            self.assertEqual(response.status_int, 204)

            response = self.app.get('/v1/rcs')
            self.assertEqual(response.status_int, 200)
            c = response.json['rcs']
            self.assertEqual(0, len(c))
