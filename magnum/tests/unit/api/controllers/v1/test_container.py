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

from magnum import objects
from magnum.tests.unit.db import base as db_base
from magnum.tests.unit.db import utils

from mock import patch
from webtest.app import AppError


class TestContainerController(db_base.DbTestCase):
    @patch('magnum.objects.bay.Bay.get_by_uuid')
    @patch('magnum.conductor.api.API.container_create')
    @patch('magnum.conductor.api.API.container_delete')
    @patch('magnum.conductor.api.API.container_start')
    @patch('magnum.conductor.api.API.container_stop')
    @patch('magnum.conductor.api.API.container_pause')
    @patch('magnum.conductor.api.API.container_unpause')
    @patch('magnum.conductor.api.API.container_reboot')
    @patch('magnum.conductor.api.API.container_logs')
    @patch('magnum.conductor.api.API.container_execute')
    def test_containers_api(self,
                            mock_container_execute,
                            mock_container_logs,
                            mock_container_reboot,
                            mock_container_unpause,
                            mock_container_pause,
                            mock_container_stop,
                            mock_container_start,
                            mock_container_delete,
                            mock_container_create,
                            mock_get_by_uuid):
        mock_container_create.side_effect = lambda x, y, z: z
        mock_container_start.return_value = None
        mock_container_stop.return_value = None
        mock_container_pause.return_value = None
        mock_container_unpause.return_value = None
        mock_container_reboot.return_value = None
        mock_container_logs.return_value = None
        mock_container_execute.return_value = None

        # Create a container
        params = ('{"name": "My Docker", "image_id": "ubuntu",'
                  '"command": "env",'
                  '"bay_uuid": "fff114da-3bfa-4a0f-a123-c0dffad9718e"}')
        self.fake_bay = utils.get_test_bay()
        value = self.fake_bay['uuid']
        mock_get_by_uuid.return_value = self.fake_bay
        bay = objects.Bay.get_by_uuid(self.context, value)
        self.assertEqual(value, bay['uuid'])
        response = self.app.post('/v1/containers',
                                 params=params,
                                 content_type='application/json')
        self.assertEqual(response.status_int, 201)

        # Get all containers
        response = self.app.get('/v1/containers')
        self.assertEqual(response.status_int, 200)
        self.assertEqual(1, len(response.json))
        c = response.json['containers'][0]
        self.assertIsNotNone(c.get('uuid'))
        self.assertEqual('My Docker', c.get('name'))

        # Get just the one we created
        response = self.app.get('/v1/containers/%s' % c.get('uuid'))
        self.assertEqual(response.status_int, 200)

        # Update the description
        params = [{'path': '/name',
                   'value': 'container_example_B',
                   'op': 'replace'}]
        response = self.app.patch_json('/v1/containers/%s' % c.get('uuid'),
                               params=params)
        self.assertEqual(response.status_int, 200)

        # Execute some actions
        actions = ['start', 'stop', 'pause', 'unpause',
                   'reboot']
        for action in actions:
            response = self.app.put('/v1/containers/%s/%s' % (c.get('uuid'),
                                                              action))
            self.assertEqual(response.status_int, 200)

            # Only PUT should work, others like GET should fail
            self.assertRaises(AppError, self.app.get,
                              ('/v1/containers/%s/%s' %
                               (c.get('uuid'), action)))

        # Fetch the logs
        response = self.app.get('/v1/containers/%s/logs' % c.get('uuid'))
        self.assertEqual(response.status_int, 200)

        # Fetch the logs should fail with put
        self.assertRaises(AppError, self.app.put,
                          ('/v1/containers/%s/logs' % c.get('uuid')))

        # Execute command in docker container
        response = self.app.put('/v1/containers/%s/%s' % (c.get('uuid'),
                                              'execute'), {'command': 'ls'})
        self.assertEqual(response.status_int, 200)

        # Delete the container we created
        response = self.app.delete('/v1/containers/%s' % c.get('uuid'))
        self.assertEqual(response.status_int, 204)

        response = self.app.get('/v1/containers')
        self.assertEqual(response.status_int, 200)
        c = response.json['containers']
        self.assertEqual(0, len(c))

    @patch('magnum.objects.bay.Bay.get_by_uuid')
    @patch('magnum.conductor.api.API.container_create')
    @patch('magnum.conductor.api.API.container_delete')
    def test_create_container_with_command(self,
                                           mock_container_delete,
                                           mock_container_create,
                                           mock_get_by_uuid):
        mock_container_create.side_effect = lambda x, y, z: z
        # Create a container with a command
        params = ('{"name": "My Docker", "image_id": "ubuntu",'
                  '"command": "env",'
                  '"bay_uuid": "fff114da-3bfa-4a0f-a123-c0dffad9718e"}')
        self.fake_bay = utils.get_test_bay()
        value = self.fake_bay['uuid']
        mock_get_by_uuid.return_value = self.fake_bay
        bay = objects.Bay.get_by_uuid(self.context, value)
        self.assertEqual(value, bay['uuid'])
        response = self.app.post('/v1/containers',
                                 params=params,
                                 content_type='application/json')
        self.assertEqual(response.status_int, 201)
        # get all containers
        response = self.app.get('/v1/containers')
        self.assertEqual(response.status_int, 200)
        self.assertEqual(1, len(response.json))
        c = response.json['containers'][0]
        self.assertIsNotNone(c.get('uuid'))
        self.assertEqual('My Docker', c.get('name'))
        self.assertEqual('env', c.get('command'))
        # Delete the container we created
        response = self.app.delete('/v1/containers/%s' % c.get('uuid'))
        self.assertEqual(response.status_int, 204)

        response = self.app.get('/v1/containers')
        self.assertEqual(response.status_int, 200)
        c = response.json['containers']
        self.assertEqual(0, len(c))

    @patch('magnum.objects.bay.Bay.get_by_uuid')
    @patch('magnum.conductor.api.API.container_create')
    @patch('magnum.conductor.api.API.container_delete')
    def test_create_container_with_bay_uuid(self,
                                           mock_container_delete,
                                           mock_container_create,
                                           mock_get_by_uuid):
        mock_container_create.side_effect = lambda x, y, z: z
        # Create a container with a command
        params = ('{"name": "My Docker", "image_id": "ubuntu",'
                  '"command": "env",'
                  '"bay_uuid": "fff114da-3bfa-4a0f-a123-c0dffad9718e"}')
        self.fake_bay = utils.get_test_bay()
        value = self.fake_bay['uuid']
        mock_get_by_uuid.return_value = self.fake_bay
        bay = objects.Bay.get_by_uuid(self.context, value)
        self.assertEqual(value, bay['uuid'])
        response = self.app.post('/v1/containers',
                                 params=params,
                                 content_type='application/json')
        self.assertEqual(response.status_int, 201)
        # get all containers
        response = self.app.get('/v1/containers')
        self.assertEqual(response.status_int, 200)
        self.assertEqual(1, len(response.json))
        c = response.json['containers'][0]
        self.assertIsNotNone(c.get('uuid'))
        self.assertEqual('My Docker', c.get('name'))
        self.assertEqual('env', c.get('command'))
        # Delete the container we created
        response = self.app.delete('/v1/containers/%s' % c.get('uuid'))
        self.assertEqual(response.status_int, 204)

        response = self.app.get('/v1/containers')
        self.assertEqual(response.status_int, 200)
        c = response.json['containers']
        self.assertEqual(0, len(c))
