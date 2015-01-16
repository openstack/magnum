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

from mock import patch


class TestPodController(db_base.DbTestCase):
    def mock_pod_create(self, pod):
        pod.create()
        return pod

    def mock_pod_destroy(self, pod_uuid):
        pod = objects.Pod.get_by_uuid({}, pod_uuid)
        pod.destroy()

    def test_pod_api(self):
        with patch.object(api.API, 'pod_create') as mock_method:
            mock_method.side_effect = self.mock_pod_create
            # Create a pod
            params = '''
            {
                "desc": "My Pod",
                "bay_uuid": "7ae81bb3-dec3-4289-8d6c-da80bd8001ae",
                "images": ["ubuntu"],
                "manifest": "{\\"id\\": \\"name_of_pod\\", \
                \\"labels\\": {\\"foo\\": \\"foo1\\"} }"
            }
            '''
            response = self.app.post('/v1/pods',
                                     params=params,
                                     content_type='application/json')
            self.assertEqual(response.status_int, 201)

            # Get all pods
            response = self.app.get('/v1/pods')
            self.assertEqual(response.status_int, 200)
            self.assertEqual(1, len(response.json))
            c = response.json['pods'][0]
            self.assertIsNotNone(c.get('uuid'))
            self.assertEqual('name_of_pod', c.get('name'))
            self.assertEqual('My Pod', c.get('desc'))
            self.assertEqual('7ae81bb3-dec3-4289-8d6c-da80bd8001ae',
                             c.get('bay_uuid'))
            self.assertEqual(['ubuntu'], c.get('images'))
            self.assertEqual('foo1', c.get('labels')['foo'])

            # Get just the one we created
            response = self.app.get('/v1/pods/%s' % c.get('uuid'))
            self.assertEqual(response.status_int, 200)

            # Update the description
            params = [{'path': '/name',
                       'value': 'pod_example_B',
                       'op': 'replace'}]
            response = self.app.patch_json('/v1/pods/%s' % c.get('uuid'),
                                           params=params)
            self.assertEqual(response.status_int, 200)

        with patch.object(api.API, 'pod_delete') as mock_method:
            mock_method.side_effect = self.mock_pod_destroy
            # Delete the pod we created
            response = self.app.delete('/v1/pods/%s' % c.get('uuid'))
            self.assertEqual(response.status_int, 204)

            response = self.app.get('/v1/pods')
            self.assertEqual(response.status_int, 200)
            c = response.json['pods']
            self.assertEqual(0, len(c))
