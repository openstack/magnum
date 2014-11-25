#    Licensed under the Apache License, Version 2.0 (the "License");
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

from magnum import tests


class TestRootController(tests.FunctionalTest):

    def test_version(self):
        expected = [{'status': 'CURRENT',
                     'link': {'href': 'http://localhost/v1',
                              'target_name': 'v1'},
                     'id': 'v1.0'}]
        response = self.app.get('/')
        self.assertEqual(expected, response.json)

    def test_v1_controller_redirect(self):
        response = self.app.get('/v1')
        self.assertEqual(302, response.status_int)
        self.assertEqual('http://localhost/v1/',
                         response.headers['Location'])

    def test_v1_controller(self):
        expected = {'containers_uri': 'http://localhost/v1/containers',
                    'name': 'magnum',
                    'services_uri': 'http://localhost/v1/services',
                    'type': 'platform',
                    'uri': 'http://localhost/v1',
                    'bays_uri': 'http://localhost/v1/bays',
                    'description': 'magnum native implementation',
                    'pods_uri': 'http://localhost/v1/pods'}
        response = self.app.get('/v1/')
        self.assertEqual(expected, response.json)

    def test_get_not_found(self):
        response = self.app.get('/a/bogus/url', expect_errors=True)
        assert response.status_int == 404