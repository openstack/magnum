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

import datetime

import mock
from oslo_config import cfg
from oslo_utils import timeutils
from six.moves.urllib import parse as urlparse
from webtest.app import AppError
from wsme import types as wtypes

from magnum.api.controllers.v1 import baymodel as api_baymodel
from magnum.common import utils
from magnum.tests import base
from magnum.tests.unit.api import base as api_base
from magnum.tests.unit.api import utils as apiutils
from magnum.tests.unit.objects import utils as obj_utils


class TestBayModelObject(base.TestCase):

    def test_baymodel_init(self):
        baymodel_dict = apiutils.baymodel_post_data()
        del baymodel_dict['image_id']
        baymodel = api_baymodel.BayModel(**baymodel_dict)
        self.assertEqual(wtypes.Unset, baymodel.image_id)


class TestListBayModel(api_base.FunctionalTest):

    def test_empty(self):
        response = self.get_json('/baymodels')
        self.assertEqual([], response['baymodels'])

    def test_one(self):
        baymodel = obj_utils.create_test_baymodel(self.context)
        response = self.get_json('/baymodels')
        self.assertEqual(baymodel.uuid, response['baymodels'][0]["uuid"])
        self.assertNotIn('flavor_id', response['baymodels'][0])
        self.assertNotIn('master_flavor_id', response['baymodels'][0])
        self.assertNotIn('dns_nameserver', response['baymodels'][0])
        self.assertNotIn('keypair_id', response['baymodels'][0])
        self.assertNotIn('external_network_id', response['baymodels'][0])
        self.assertNotIn('fixed_network', response['baymodels'][0])
        self.assertNotIn('docker_volume_size', response['baymodels'][0])
        self.assertNotIn('ssh_authorized_key', response['baymodels'][0])

    def test_get_one(self):
        baymodel = obj_utils.create_test_baymodel(self.context)
        response = self.get_json('/baymodels/%s' % baymodel['uuid'])
        self.assertEqual(baymodel.uuid, response['uuid'])
        self.assertIn('flavor_id', response)
        self.assertIn('master_flavor_id', response)
        self.assertIn('dns_nameserver', response)
        self.assertIn('keypair_id', response)
        self.assertIn('external_network_id', response)
        self.assertIn('fixed_network', response)
        self.assertIn('docker_volume_size', response)
        self.assertIn('ssh_authorized_key', response)
        self.assertIn('coe', response)

    def test_get_one_by_name(self):
        baymodel = obj_utils.create_test_baymodel(self.context)
        response = self.get_json('/baymodels/%s' % baymodel['name'])
        self.assertEqual(baymodel.uuid, response['uuid'])
        self.assertIn('flavor_id', response)
        self.assertIn('master_flavor_id', response)
        self.assertIn('dns_nameserver', response)
        self.assertIn('keypair_id', response)
        self.assertIn('external_network_id', response)
        self.assertIn('fixed_network', response)
        self.assertIn('docker_volume_size', response)
        self.assertIn('coe', response)

    def test_get_one_by_name_not_found(self):
        response = self.get_json('/baymodels/not_found',
                                  expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_get_one_by_name_multiple_baymodel(self):
        obj_utils.create_test_baymodel(self.context, name='test_baymodel',
                                  uuid=utils.generate_uuid())
        obj_utils.create_test_baymodel(self.context, name='test_baymodel',
                                  uuid=utils.generate_uuid())
        response = self.get_json('/baymodels/test_baymodel',
                                 expect_errors=True)
        self.assertEqual(409, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_detail(self):
        baymodel = obj_utils.create_test_baymodel(self.context)
        response = self.get_json('/baymodels/detail')
        self.assertEqual(baymodel.uuid, response['baymodels'][0]["uuid"])
        self.assertIn('flavor_id', response['baymodels'][0])
        self.assertIn('master_flavor_id', response['baymodels'][0])
        self.assertIn('dns_nameserver', response['baymodels'][0])
        self.assertIn('keypair_id', response['baymodels'][0])
        self.assertIn('external_network_id', response['baymodels'][0])
        self.assertIn('fixed_network', response['baymodels'][0])
        self.assertIn('docker_volume_size', response['baymodels'][0])
        self.assertIn('ssh_authorized_key', response['baymodels'][0])
        self.assertIn('coe', response['baymodels'][0])

    def test_detail_against_single(self):
        baymodel = obj_utils.create_test_baymodel(self.context)
        response = self.get_json('/baymodels/%s/detail' % baymodel['uuid'],
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_many(self):
        bm_list = []
        for id_ in range(5):
            baymodel = obj_utils.create_test_baymodel(self.context, id=id_,
                                                    uuid=utils.generate_uuid())
            bm_list.append(baymodel.uuid)
        response = self.get_json('/baymodels')
        self.assertEqual(len(bm_list), len(response['baymodels']))
        uuids = [bm['uuid'] for bm in response['baymodels']]
        self.assertEqual(sorted(bm_list), sorted(uuids))

    def test_links(self):
        uuid = utils.generate_uuid()
        obj_utils.create_test_baymodel(self.context, id=1, uuid=uuid)
        response = self.get_json('/baymodels/%s' % uuid)
        self.assertIn('links', response.keys())
        self.assertEqual(2, len(response['links']))
        self.assertIn(uuid, response['links'][0]['href'])
        for l in response['links']:
            bookmark = l['rel'] == 'bookmark'
            self.assertTrue(self.validate_link(l['href'], bookmark=bookmark))

    def test_collection_links(self):
        for id_ in range(5):
            obj_utils.create_test_baymodel(self.context, id=id_,
                                          uuid=utils.generate_uuid())
        response = self.get_json('/baymodels/?limit=3')
        self.assertEqual(3, len(response['baymodels']))

        next_marker = response['baymodels'][-1]['uuid']
        self.assertIn(next_marker, response['next'])

    def test_collection_links_default_limit(self):
        cfg.CONF.set_override('max_limit', 3, 'api')
        for id_ in range(5):
            obj_utils.create_test_baymodel(self.context, id=id_,
                                           uuid=utils.generate_uuid())
        response = self.get_json('/baymodels')
        self.assertEqual(3, len(response['baymodels']))

        next_marker = response['baymodels'][-1]['uuid']
        self.assertIn(next_marker, response['next'])


class TestPatch(api_base.FunctionalTest):

    def setUp(self):
        super(TestPatch, self).setUp()
        self.baymodel = obj_utils.create_test_baymodel(self.context,
                            name='bay_model_example_A',
                            image_id='nerdherd',
                            apiserver_port=8080,
                            fixed_network='private',
                            docker_volume_size=20,
                            ssh_authorized_key='ssh-rsa AAAAB3NzaC1ycEAAAADA'
                                               'v0XRqg3tm+jlsOKGO81lPDH+KaSJ'
                                               'Q7wvmjUqszP/H6NC/m+qiGp/sTis'
                                               'DYucqbeuM7nmJi+8Hb55y1xWoOZI'
                                               'KMa71G5/4EOQxuQ/sgW965OOO2Hq'
                                               'X8vjlQUnTK0HijrbSTLxp/9kazWW'
                                               'FrfsdB8RtZBN digambar@magnum',
                            coe='swarm'
                        )

    def test_update_not_found(self):
        uuid = utils.generate_uuid()
        response = self.patch_json('/baymodels/%s' % uuid,
                                   [{'path': '/name',
                                     'value': 'bay_model_example_B',
                                     'op': 'add'}],
                                   expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_singular(self, mock_utcnow):
        name = 'bay_model_example_B'
        test_time = datetime.datetime(2000, 1, 1, 0, 0)

        mock_utcnow.return_value = test_time
        response = self.patch_json('/baymodels/%s' % self.baymodel.uuid,
                                   [{'path': '/name', 'value': name,
                                     'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json('/baymodels/%s' % self.baymodel.uuid)
        self.assertEqual(name, response['name'])
        return_updated_at = timeutils.parse_isotime(
                            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)
        # Assert nothing else was changed
        self.assertEqual(self.baymodel.uuid, response['uuid'])
        self.assertEqual(self.baymodel.image_id, response['image_id'])
        self.assertEqual(self.baymodel.apiserver_port,
                         response['apiserver_port'])
        self.assertEqual(self.baymodel.fixed_network,
                         response['fixed_network'])
        self.assertEqual(self.baymodel.docker_volume_size,
                         response['docker_volume_size'])
        self.assertEqual(self.baymodel.ssh_authorized_key,
                         response['ssh_authorized_key'])
        self.assertEqual(self.baymodel.coe,
                         response['coe'])

    def test_remove_singular(self):
        baymodel = obj_utils.create_test_baymodel(self.context,
                                                  uuid=utils.generate_uuid())
        response = self.get_json('/baymodels/%s' % baymodel.uuid)
        self.assertIsNotNone(response['image_id'])

        response = self.patch_json('/baymodels/%s' % baymodel.uuid,
                                   [{'path': '/image_id', 'op': 'remove'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json('/baymodels/%s' % baymodel.uuid)
        self.assertIsNone(response['image_id'])
        # Assert nothing else was changed
        self.assertEqual(baymodel.uuid, response['uuid'])
        self.assertEqual(baymodel.name, response['name'])
        self.assertEqual(baymodel.apiserver_port, response['apiserver_port'])
        self.assertEqual(self.baymodel.fixed_network,
                         response['fixed_network'])
        self.assertEqual(self.baymodel.docker_volume_size,
                         response['docker_volume_size'])
        self.assertEqual(self.baymodel.ssh_authorized_key,
                         response['ssh_authorized_key'])
        self.assertEqual(self.baymodel.coe,
                         response['coe'])

    def test_remove_non_existent_property_fail(self):
        response = self.patch_json('/baymodels/%s' % self.baymodel.uuid,
                             [{'path': '/non-existent', 'op': 'remove'}],
                             expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['error_message'])

    def test_add_root(self):
        name = 'bay_model_example_B'
        response = self.patch_json('/baymodels/%s' % self.baymodel.uuid,
                            [{'path': '/name', 'value': name, 'op': 'add'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_int)

        response = self.get_json('/baymodels/%s' % self.baymodel.uuid)
        self.assertEqual(name, response['name'])
        # Assert nothing else was changed
        self.assertEqual(self.baymodel.uuid, response['uuid'])
        self.assertEqual(self.baymodel.image_id, response['image_id'])
        self.assertEqual(self.baymodel.apiserver_port,
                         response['apiserver_port'])
        self.assertEqual(self.baymodel.docker_volume_size,
                         response['docker_volume_size'])
        self.assertEqual(self.baymodel.coe,
                         response['coe'])

    def test_add_root_non_existent(self):
        response = self.patch_json('/baymodels/%s' % self.baymodel.uuid,
                            [{'path': '/foo', 'value': 'bar', 'op': 'add'}],
                            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_add_multi(self):
        json = [
            {
                'path': '/name',
                'value': 'bay_model_example_B',
                'op': 'add'
            },
            {
                'path': '/image_id',
                'value': 'my-image',
                'op': 'add'
            }
        ]
        response = self.patch_json('/baymodels/%s' % self.baymodel.uuid, json)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json('/baymodels/%s' % self.baymodel.uuid)
        self.assertEqual('bay_model_example_B', response['name'])
        self.assertEqual('my-image', response['image_id'])
        # Assert nothing else was changed
        self.assertEqual(self.baymodel.uuid, response['uuid'])
        self.assertEqual(self.baymodel.apiserver_port,
                         response['apiserver_port'])
        self.assertEqual(self.baymodel.fixed_network,
                         response['fixed_network'])
        self.assertEqual(self.baymodel.docker_volume_size,
                         response['docker_volume_size'])
        self.assertEqual(self.baymodel.ssh_authorized_key,
                         response['ssh_authorized_key'])
        self.assertEqual(self.baymodel.coe,
                         response['coe'])

    def test_remove_uuid(self):
        response = self.patch_json('/baymodels/%s' % self.baymodel.uuid,
                                   [{'path': '/uuid', 'op': 'remove'}],
                                   expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


class TestPost(api_base.FunctionalTest):

    def setUp(self):
        super(TestPost, self).setUp()

    @mock.patch('magnum.common.clients.OpenStackClients')
    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_baymodel(self, mock_utcnow, mock_openstack_client):
        cdict = apiutils.baymodel_post_data()
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time
        test_auth_url = 'http://127.0.0.1:5000/v2.0'
        mock_openstack_client.glance.return_value = test_auth_url

        response = self.post_json('/baymodels', cdict)
        self.assertEqual(201, response.status_int)
        # Check location header
        self.assertIsNotNone(response.location)
        expected_location = '/v1/baymodels/%s' % cdict['uuid']
        self.assertEqual(urlparse.urlparse(response.location).path,
                         expected_location)
        self.assertEqual(cdict['uuid'], response.json['uuid'])
        self.assertNotIn('updated_at', response.json.keys)
        return_created_at = timeutils.parse_isotime(
                            response.json['created_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_created_at)

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_create_baymodel_doesnt_contain_id(self, mock_openstack_client):
        with mock.patch.object(self.dbapi, 'create_baymodel',
                               wraps=self.dbapi.create_baymodel) as cc_mock:
            test_auth_url = 'http://127.0.0.1:5000/v2.0'
            mock_openstack_client.glance.return_value = test_auth_url
            cdict = apiutils.baymodel_post_data(image_id='my-image')
            response = self.post_json('/baymodels', cdict)
            self.assertEqual(cdict['image_id'], response.json['image_id'])
            cc_mock.assert_called_once_with(mock.ANY)
            # Check that 'id' is not in first arg of positional args
            self.assertNotIn('id', cc_mock.call_args[0][0])

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_create_baymodel_with_invalid_docker_volume_size(self,
                               mock_openstack_client):
        with mock.patch.object(self.dbapi, 'create_baymodel',
                               wraps=self.dbapi.create_baymodel) as cc_mock:
            test_auth_url = 'http://127.0.0.1:5000/v2.0'
            mock_openstack_client.glance.return_value = test_auth_url
            cdict = apiutils.baymodel_post_data(docker_volume_size='docker')
            self.assertRaises(AppError, self.post_json, '/baymodels', cdict)
            self.assertFalse(cc_mock.called)

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_create_baymodel_with_docker_volume_size(self,
                               mock_openstack_client):
        with mock.patch.object(self.dbapi, 'create_baymodel',
                               wraps=self.dbapi.create_baymodel) as cc_mock:
            test_auth_url = 'http://127.0.0.1:5000/v2.0'
            mock_openstack_client.glance.return_value = test_auth_url
            cdict = apiutils.baymodel_post_data(docker_volume_size=99)
            response = self.post_json('/baymodels', cdict)
            self.assertEqual(cdict['docker_volume_size'],
                    response.json['docker_volume_size'])
            cc_mock.assert_called_once_with(mock.ANY)
            self.assertNotIn('id', cc_mock.call_args[0][0])

    @mock.patch('magnum.common.clients.OpenStackClients')
    def test_create_baymodel_generate_uuid(self, mock_openstack_client):
        test_auth_url = 'http://127.0.0.1:5000/v2.0'
        mock_openstack_client.glance.return_value = test_auth_url
        cdict = apiutils.baymodel_post_data()
        del cdict['uuid']
        response = self.post_json('/baymodels', cdict)
        self.assertEqual(cdict['image_id'],
                         response.json['image_id'])
        self.assertTrue(utils.is_uuid_like(response.json['uuid']))

    @mock.patch.object(api_baymodel.BayModelsController, '_get_image_data')
    def test_create_baymodel_with_no_os_distro_image(self, mock_image_data):
        mock_image_data.return_value = {'name': 'mock_name'}
        cdict = apiutils.baymodel_post_data()
        del cdict['uuid']
        response = self.post_json('/baymodels', cdict, expect_errors=True)
        self.assertEqual(404, response.status_int)

    @mock.patch.object(api_baymodel.BayModelsController, '_get_image_data')
    def test_create_baymodel_with_os_distro_image(self, mock_image_data):
        mock_image_data.return_value = {'name': 'mock_name',
                                        'os_distro': 'fedora-atomic'}
        cdict = apiutils.baymodel_post_data()
        del cdict['uuid']
        response = self.post_json('/baymodels', cdict, expect_errors=True)
        self.assertEqual(201, response.status_int)


class TestDelete(api_base.FunctionalTest):

    def test_delete_baymodel(self):
        baymodel = obj_utils.create_test_baymodel(self.context)
        self.delete('/baymodels/%s' % baymodel.uuid)
        response = self.get_json('/baymodels/%s' % baymodel.uuid,
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_delete_baymodel_with_bay(self):
        baymodel = obj_utils.create_test_baymodel(self.context)
        obj_utils.create_test_bay(self.context, baymodel_id=baymodel.uuid)
        response = self.delete('/baymodels/%s' % baymodel.uuid,
                               expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])
        self.assertIn(baymodel.uuid, response.json['error_message'])

    def test_delete_baymodel_not_found(self):
        uuid = utils.generate_uuid()
        response = self.delete('/baymodels/%s' % uuid, expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_delete_baymodel_with_name(self):
        baymodel = obj_utils.create_test_baymodel(self.context)
        response = self.delete('/baymodels/%s' % baymodel['name'],
                               expect_errors=True)
        self.assertEqual(204, response.status_int)

    def test_delete_baymodel_with_name_not_found(self):
        response = self.delete('/baymodels/not_found', expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_delete_multiple_baymodel_by_name(self):
        obj_utils.create_test_baymodel(self.context, name='test_baymodel',
                                  uuid=utils.generate_uuid())
        obj_utils.create_test_baymodel(self.context, name='test_baymodel',
                                  uuid=utils.generate_uuid())
        response = self.delete('/baymodels/test_baymodel', expect_errors=True)
        self.assertEqual(409, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])
