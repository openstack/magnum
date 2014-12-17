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
from magnum import tests
from magnum.tests.db import base as db_base

from mock import patch


class TestRootController(tests.FunctionalTest):
    def test_version(self):
        expected = {u'default_version':
                    {u'id': u'v1', u'links':
                     [{u'href': u'http://localhost/v1/', u'rel': u'self'}]},
                    u'description': u'Magnum is an OpenStack project which '
                    'aims to provide container management.',
                    u'name': u'OpenStack Magnum API',
                    u'versions': [{u'id': u'v1',
                                  u'links':
                                      [{u'href': u'http://localhost/v1/',
                                        u'rel': u'self'}]}]}

        response = self.app.get('/')
        self.assertEqual(expected, response.json)

    def test_v1_controller(self):
        expected = {u'media_types':
            [{u'base': u'application/json',
            u'type': u'application/vnd.openstack.magnum.v1+json'}],
            u'links': [{u'href': u'http://localhost/v1/',
            u'rel': u'self'},
            {u'href':
             u'http://docs.openstack.org/developer'
              '/magnum/dev/api-spec-v1.html',
            u'type': u'text/html', u'rel': u'describedby'}],
            u'bays': [{u'href': u'http://localhost/v1/bays/',
                u'rel': u'self'},
                {u'href': u'http://localhost/bays/',
                u'rel': u'bookmark'}],
            u'services': [{u'href': u'http://localhost/v1/services/',
                u'rel': u'self'},
                {u'href': u'http://localhost/services/',
                u'rel': u'bookmark'}],
            u'baymodels': [{u'href': u'http://localhost/v1/baymodels/',
                u'rel': u'self'},
                {u'href': u'http://localhost/bays/',
                u'rel': u'bookmark'}],
                u'pods': [{u'href': u'http://localhost/v1/pods/',
            u'rel': u'self'},
                {u'href': u'http://localhost/pods/',
                u'rel': u'bookmark'}],
                u'id': u'v1',
            u'containers': [{u'href': u'http://localhost/v1/containers/',
                u'rel': u'self'},
                {u'href': u'http://localhost/containers/',
                u'rel': u'bookmark'}]}

        response = self.app.get('/v1/')
        self.assertEqual(expected, response.json)

    def test_get_not_found(self):
        response = self.app.get('/a/bogus/url', expect_errors=True)
        assert response.status_int == 404


class TestBayController(db_base.DbTestCase):
    def simulate_rpc_bay_create(self, bay):
        bay.create()
        return bay

    def test_bay_api(self):
        with patch.object(api.API, 'bay_create') as mock_method:
            # Create a bay
            mock_method.side_effect = self.simulate_rpc_bay_create
            params = '{"name": "bay_example_A", "type": "virt", \
                "image_id": "Fedora", "node_count": "3"}'
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
            self.assertEqual('virt', c.get('type'))
            self.assertEqual('Fedora', c.get('image_id'))
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

            # Delete the bay we created
            response = self.app.delete('/v1/bays/%s' % c.get('uuid'))
            self.assertEqual(response.status_int, 204)

            response = self.app.get('/v1/bays')
            self.assertEqual(response.status_int, 200)
            c = response.json['bays']
            self.assertEqual(0, len(c))


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


class TestNodeController(db_base.DbTestCase):
    def test_node_api(self):
        # Create a node
        params = '{"type": "bare", "image_id": "Fedora"}'
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


class TestPodController(db_base.DbTestCase):
    def mock_pod_create(self, pod):
        pod.create()
        return pod

    def mock_pod_destroy(self, pod):
        pod.destroy()

    def test_pod_api(self):
        with patch.object(api.API, 'pod_create') as mock_method:
            mock_method.side_effect = self.mock_pod_create
            # Create a pod
            params = '{"name": "pod_example_A", "desc": "My Pod",' \
                     '"bay_uuid": "7ae81bb3-dec3-4289-8d6c-da80bd8001ae"}'
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
            self.assertEqual('pod_example_A', c.get('name'))
            self.assertEqual('My Pod', c.get('desc'))
            self.assertEqual('7ae81bb3-dec3-4289-8d6c-da80bd8001ae',
                             c.get('bay_uuid'))

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


class TestContainerController(db_base.DbTestCase):
    def test_containers_api(self):
        # Create a container
        params = '{"name": "My Docker"}'
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
                   'reboot', 'logs', 'execute']
        for action in actions:
            response = self.app.put('/v1/containers/%s/%s' % (c.get('uuid'),
                                                              action))
            self.assertEqual(response.status_int, 200)

        # Delete the bay we created
        response = self.app.delete('/v1/containers/%s' % c.get('uuid'))
        self.assertEqual(response.status_int, 204)

        response = self.app.get('/v1/containers')
        self.assertEqual(response.status_int, 200)
        c = response.json['containers']
        self.assertEqual(0, len(c))


class TestServiceController(db_base.DbTestCase):

    def mock_service_create(self, service):
        service.create()
        return service

    def mock_service_destroy(self, service):
        service.destroy()

    def test_service_api(self):
        with patch.object(api.API, 'service_create') as mock_method:
            mock_method.side_effect = self.mock_service_create
            # Create a service
            params = '{"name": "service_foo",'\
                     '"bay_uuid": "7ae81bb3-dec3-4289-8d6c-da80bd8001ae"}'
            response = self.app.post('/v1/services',
                                     params=params,
                                     content_type='application/json')
            self.assertEqual(response.status_int, 201)
            # Get all services
            response = self.app.get('/v1/services')
            self.assertEqual(response.status_int, 200)
            self.assertEqual(1, len(response.json))
            c = response.json['services'][0]
            self.assertIsNotNone(c.get('uuid'))
            self.assertEqual('service_foo', c.get('name'))
            self.assertEqual('7ae81bb3-dec3-4289-8d6c-da80bd8001ae',
                             c.get('bay_uuid'))

            # Get just the one we created
            response = self.app.get('/v1/services/%s' % c.get('uuid'))
            self.assertEqual(response.status_int, 200)

            # Update the description
            params = [{'path': '/name',
                       'value': 'service_bar',
                       'op': 'replace'}]
            response = self.app.patch_json('/v1/services/%s' % c.get('uuid'),
                                           params=params)
            self.assertEqual(response.status_int, 200)

        with patch.object(api.API, 'service_delete') as mock_method:
            mock_method.side_effect = self.mock_service_destroy
            # Delete the service we created
            response = self.app.delete('/v1/services/%s' % c.get('uuid'))
            self.assertEqual(response.status_int, 204)

            response = self.app.get('/v1/services')
            self.assertEqual(response.status_int, 200)
            c = response.json['services']
            self.assertEqual(0, len(c))
