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


class TestBayController(tests.FunctionalTest):
    def test_bay_api(self):
        # Create a bay
        params = '{"name": "bay_example_A", "type": "virt"}'
        response = self.app.post('/v1/bays',
                                 params=params,
                                 content_type='application/json')
        self.assertEqual(response.status_int, 200)

        # Get all bays
        response = self.app.get('/v1/bays')
        self.assertEqual(response.status_int, 200)
        self.assertEqual(1, len(response.json))
        c = response.json[0]
        self.assertIsNotNone(c.get('id'))
        self.assertEqual('bay_example_A', c.get('name'))
        self.assertEqual('virt', c.get('type'))

        # Get just the one we created
        response = self.app.get('/v1/bays/%s' % c.get('id'))
        self.assertEqual(response.status_int, 200)

        # Update the description
        params = ('{"id":"' + c.get('id') + '", '
                   '"type": "virt", '
                   '"name": "bay_example_B"}')
        response = self.app.put('/v1/bays',
                                params=params,
                                content_type='application/json')
        self.assertEqual(response.status_int, 200)

        # Delete the bay we created
        response = self.app.delete('/v1/bays/%s' % c.get('id'))
        self.assertEqual(response.status_int, 200)

        response = self.app.get('/v1/bays')
        self.assertEqual(response.status_int, 200)
        self.assertEqual(0, len(response.json))


class TestPodController(tests.FunctionalTest):
    def test_pod_api(self):
        # Create a pod
        params = '{"desc": "my pod", "name": "pod_example_A"}'
        response = self.app.post('/v1/pods',
                                 params=params,
                                 content_type='application/json')
        self.assertEqual(response.status_int, 200)

        # Get all bays
        response = self.app.get('/v1/pods')
        self.assertEqual(response.status_int, 200)
        self.assertEqual(1, len(response.json))
        c = response.json[0]
        self.assertIsNotNone(c.get('id'))
        self.assertEqual('pod_example_A', c.get('name'))
        self.assertEqual('my pod', c.get('desc'))

        # Get just the one we created
        response = self.app.get('/v1/pods/%s' % c.get('id'))
        self.assertEqual(response.status_int, 200)

        # Update the description
        params = ('{"id":"' + c.get('id') + '", '
                   '"desc": "your pod", '
                   '"name": "pod_example_A"}')
        response = self.app.put('/v1/pods',
                                params=params,
                                content_type='application/json')
        self.assertEqual(response.status_int, 200)

        # Delete the bay we created
        response = self.app.delete('/v1/pods/%s' % c.get('id'))
        self.assertEqual(response.status_int, 200)

        response = self.app.get('/v1/pods')
        self.assertEqual(response.status_int, 200)
        self.assertEqual(0, len(response.json))


class TestContainerController(tests.FunctionalTest):
    def test_container_api(self):
        # Create a container
        params = '{"desc": "My Docker Containers", "name": "My Docker"}'
        response = self.app.post('/v1/containers',
                                 params=params,
                                 content_type='application/json')
        self.assertEqual(response.status_int, 200)

        # Get all containers
        response = self.app.get('/v1/containers')
        self.assertEqual(response.status_int, 200)
        self.assertEqual(1, len(response.json))
        c = response.json[0]
        self.assertIsNotNone(c.get('id'))
        self.assertEqual('My Docker', c.get('name'))
        self.assertEqual('My Docker Containers', c.get('desc'))

        # Get just the one we created
        response = self.app.get('/v1/containers/%s' % c.get('id'))
        self.assertEqual(response.status_int, 200)

        # Update the description
        params = ('{"id":"' + c.get('id') + '", '
                   '"desc": "My Docker Containers - 2", '
                   '"name": "My Docker"}')
        response = self.app.put('/v1/containers',
                                params=params,
                                content_type='application/json')
        self.assertEqual(response.status_int, 200)

        # Execute some actions
        actions = ['start', 'stop', 'pause', 'unpause',
                   'reboot', 'logs', 'execute']
        for action in actions:
            response = self.app.put('/v1/containers/%s/%s' % (c.get('id'),
                                                              action))
            self.assertEqual(response.status_int, 200)

        # Delete the container we created
        response = self.app.delete('/v1/containers/%s' % c.get('id'))
        self.assertEqual(response.status_int, 200)

        response = self.app.get('/v1/containers')
        self.assertEqual(response.status_int, 200)
        self.assertEqual(0, len(response.json))
