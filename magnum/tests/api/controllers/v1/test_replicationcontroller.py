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


class TestRCController(db_base.DbTestCase):
    def mock_rc_create(self, rc):
        rc.create()
        return rc

    def mock_rc_destroy(self, uuid):
        rc = objects.ReplicationController.get_by_uuid({}, uuid)
        rc.destroy()

    def test_rc_api(self):
        with patch.object(api.API, 'rc_create') as mock_method:
            mock_method.side_effect = self.mock_rc_create
            # Create a bay
            bay = db_utils.create_test_bay()

            # Create a replication controller
            params = '''
            {
                "bay_uuid": "%s",
                "manifest": "\
                {\
                  \\"id\\": \\"name_of_rc\\", \
                  \\"replicas\\": 3, \
                  \\"labels\\": {\
                    \\"foo\\": \\"foo1\\"\
                  }\
                }\
                \"
            }
            ''' % bay.uuid
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
            self.assertEqual('name_of_rc', c.get('name'))
            self.assertEqual(bay.uuid, c.get('bay_uuid'))
            self.assertEqual('foo1', c.get('labels')['foo'])

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
