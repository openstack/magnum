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
from oslo_policy import policy
from oslo_utils import timeutils
from six.moves.urllib import parse as urlparse
from webtest.app import AppError
from wsme import types as wtypes

from magnum.api.controllers.v1 import baymodel as api_baymodel
from magnum.common.clients import OpenStackClients as openstack_client
from magnum.common import exception
from magnum.common import policy as magnum_policy
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
        self.assertNotIn('network_driver', response['baymodels'][0])
        self.assertNotIn('docker_volume_size', response['baymodels'][0])
        self.assertNotIn('ssh_authorized_key', response['baymodels'][0])
        self.assertNotIn('http_proxy', response['baymodels'][0])
        self.assertNotIn('https_proxy', response['baymodels'][0])
        self.assertNotIn('no_proxy', response['baymodels'][0])
        self.assertNotIn('labels', response['baymodels'][0])

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
        self.assertIn('network_driver', response)
        self.assertIn('docker_volume_size', response)
        self.assertIn('ssh_authorized_key', response)
        self.assertIn('coe', response)
        self.assertIn('http_proxy', response)
        self.assertIn('https_proxy', response)
        self.assertIn('no_proxy', response)
        self.assertIn('labels', response)

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
        self.assertIn('network_driver', response)
        self.assertIn('docker_volume_size', response)
        self.assertIn('coe', response)
        self.assertIn('http_proxy', response)
        self.assertIn('https_proxy', response)
        self.assertIn('https_proxy', response)
        self.assertIn('labels', response)

    def test_get_one_by_name_not_found(self):
        response = self.get_json(
            '/baymodels/not_found',
            expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_get_one_by_name_multiple_baymodel(self):
        obj_utils.create_test_baymodel(
            self.context, name='test_baymodel',
            uuid=utils.generate_uuid())
        obj_utils.create_test_baymodel(
            self.context, name='test_baymodel',
            uuid=utils.generate_uuid())
        response = self.get_json(
            '/baymodels/test_baymodel',
            expect_errors=True)
        self.assertEqual(409, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_get_all_with_pagination_marker(self):
        bm_list = []
        for id_ in range(4):
            baymodel = obj_utils.create_test_baymodel(
                self.context, id=id_,
                uuid=utils.generate_uuid())
            bm_list.append(baymodel)

        response = self.get_json('/baymodels?limit=3&marker=%s'
                                 % bm_list[2].uuid)
        self.assertEqual(1, len(response['baymodels']))
        self.assertEqual(bm_list[-1].uuid, response['baymodels'][0]['uuid'])

    def test_detail(self):
        baymodel = obj_utils.create_test_baymodel(self.context)
        response = self.get_json('/baymodels/detail')
        self.assertEqual(baymodel.uuid, response['baymodels'][0]["uuid"])
        for key in ("flavor_id", "master_flavor_id", "dns_nameserver",
                    "keypair_id", "external_network_id", "fixed_network",
                    "docker_volume_size", "ssh_authorized_key", "coe",
                    "http_proxy", "https_proxy", "no_proxy", "labels",
                    "network_driver"):
            self.assertIn(key, response['baymodels'][0])

    def test_detail_with_pagination_marker(self):
        bm_list = []
        for id_ in range(4):
            baymodel = obj_utils.create_test_baymodel(
                self.context, id=id_,
                uuid=utils.generate_uuid())
            bm_list.append(baymodel)

        response = self.get_json('/baymodels/detail?limit=3&marker=%s'
                                 % bm_list[2].uuid)
        self.assertEqual(1, len(response['baymodels']))
        self.assertEqual(bm_list[-1].uuid, response['baymodels'][0]['uuid'])
        for key in ("flavor_id", "master_flavor_id", "dns_nameserver",
                    "keypair_id", "external_network_id", "fixed_network",
                    "network_driver", "docker_volume_size", "labels",
                    "ssh_authorized_key", "coe"):
            self.assertIn(key, response['baymodels'][0])
            self.assertIn('flavor_id', response['baymodels'][0])
            self.assertIn('master_flavor_id', response['baymodels'][0])
            self.assertIn('dns_nameserver', response['baymodels'][0])
            self.assertIn('keypair_id', response['baymodels'][0])
            self.assertIn('external_network_id', response['baymodels'][0])
            self.assertIn('fixed_network', response['baymodels'][0])
            self.assertIn('docker_volume_size', response['baymodels'][0])
            self.assertIn('ssh_authorized_key', response['baymodels'][0])
            self.assertIn('coe', response['baymodels'][0])
            self.assertIn('http_proxy', response['baymodels'][0])
            self.assertIn('https_proxy', response['baymodels'][0])
            self.assertIn('no_proxy', response['baymodels'][0])

    def test_detail_against_single(self):
        baymodel = obj_utils.create_test_baymodel(self.context)
        response = self.get_json('/baymodels/%s/detail' % baymodel['uuid'],
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_many(self):
        bm_list = []
        for id_ in range(5):
            baymodel = obj_utils.create_test_baymodel(
                self.context, id=id_,
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
        self.baymodel = obj_utils.create_test_baymodel(
            self.context,
            name='bay_model_example_A',
            image_id='nerdherd',
            apiserver_port=8080,
            fixed_network='private',
            public=False,
            docker_volume_size=20,
            ssh_authorized_key='ssh-rsa AAAAB3NzaC1ycEAAAADA'
                               'v0XRqg3tm+jlsOKGO81lPDH+KaSJ'
                               'Q7wvmjUqszP/H6NC/m+qiGp/sTis'
                               'DYucqbeuM7nmJi+8Hb55y1xWoOZI'
                               'KMa71G5/4EOQxuQ/sgW965OOO2Hq'
                               'X8vjlQUnTK0HijrbSTLxp/9kazWW'
                               'FrfsdB8RtAAA test1234@magnum',
            coe='swarm',
            labels={'key1': 'val1', 'key2': 'val2'}
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

    @mock.patch.object(magnum_policy, 'enforce')
    def test_update_public_baymodel_success(self, mock_policy):
        mock_policy.return_value = True
        response = self.patch_json('/baymodels/%s' % self.baymodel.uuid,
                                   [{'path': '/public', 'value': True,
                                     'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json('/baymodels/%s' % self.baymodel.uuid)
        self.assertTrue(response['public'])

    @mock.patch.object(magnum_policy, 'enforce')
    def test_update_public_baymodel_fail(self, mock_policy):
        mock_policy.return_value = False
        self.assertRaises(AppError, self.patch_json,
                          '/baymodels/%s' % self.baymodel.uuid,
                          [{'path': '/public', 'value': True,
                            'op': 'replace'}])

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
        self.assertEqual(self.baymodel.network_driver,
                         response['network_driver'])
        self.assertEqual(self.baymodel.docker_volume_size,
                         response['docker_volume_size'])
        self.assertEqual(self.baymodel.ssh_authorized_key,
                         response['ssh_authorized_key'])
        self.assertEqual(self.baymodel.coe,
                         response['coe'])
        self.assertEqual(self.baymodel.http_proxy,
                         response['http_proxy'])
        self.assertEqual(self.baymodel.https_proxy,
                         response['https_proxy'])
        self.assertEqual(self.baymodel.no_proxy,
                         response['no_proxy'])
        self.assertEqual(self.baymodel.labels,
                         response['labels'])

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
        self.assertEqual(self.baymodel.network_driver,
                         response['network_driver'])
        self.assertEqual(self.baymodel.docker_volume_size,
                         response['docker_volume_size'])
        self.assertEqual(self.baymodel.ssh_authorized_key,
                         response['ssh_authorized_key'])
        self.assertEqual(self.baymodel.coe,
                         response['coe'])
        self.assertEqual(self.baymodel.http_proxy,
                         response['http_proxy'])
        self.assertEqual(self.baymodel.https_proxy,
                         response['https_proxy'])
        self.assertEqual(self.baymodel.no_proxy,
                         response['no_proxy'])
        self.assertEqual(self.baymodel.labels,
                         response['labels'])

    def test_remove_non_existent_property_fail(self):
        response = self.patch_json('/baymodels/%s' % self.baymodel.uuid,
                                   [{'path': '/non-existent', 'op': 'remove'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['error_message'])

    def test_add_root_non_existent(self):
        response = self.patch_json(
            '/baymodels/%s' % self.baymodel.uuid,
            [{'path': '/foo', 'value': 'bar', 'op': 'add'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_remove_uuid(self):
        response = self.patch_json('/baymodels/%s' % self.baymodel.uuid,
                                   [{'path': '/uuid', 'op': 'remove'}],
                                   expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


class TestPost(api_base.FunctionalTest):

    @mock.patch.object(api_baymodel.BayModelsController, '_get_image_data')
    @mock.patch('magnum.api.attr_validator.validate_keypair')
    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_baymodel(self, mock_utcnow,
                             mock_keypair_exists, mock_image_data):
        bdict = apiutils.baymodel_post_data()
        mock_keypair_exists.return_value = None
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time
        mock_image_data.return_value = {'name': 'mock_name',
                                        'os_distro': 'fedora-atomic'}

        response = self.post_json('/baymodels', bdict)
        self.assertEqual(201, response.status_int)
        # Check location header
        self.assertIsNotNone(response.location)
        expected_location = '/v1/baymodels/%s' % bdict['uuid']
        self.assertEqual(expected_location,
                         urlparse.urlparse(response.location).path)
        self.assertEqual(bdict['uuid'], response.json['uuid'])
        self.assertNotIn('updated_at', response.json.keys)
        return_created_at = timeutils.parse_isotime(
            response.json['created_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_created_at)

    @mock.patch.object(api_baymodel.BayModelsController, '_get_image_data')
    @mock.patch('magnum.api.attr_validator.validate_keypair')
    def test_create_baymodel_set_project_id_and_user_id(self,
                                                        mock_keypair_exists,
                                                        mock_image_data):
        with mock.patch.object(self.dbapi, 'create_baymodel',
                               wraps=self.dbapi.create_baymodel) as cc_mock:
            mock_keypair_exists.return_value = None
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.baymodel_post_data()
            self.post_json('/baymodels', bdict)
            cc_mock.assert_called_once_with(mock.ANY)
            self.assertEqual(self.context.project_id,
                             cc_mock.call_args[0][0]['project_id'])
            self.assertEqual(self.context.user_id,
                             cc_mock.call_args[0][0]['user_id'])

    @mock.patch.object(api_baymodel.BayModelsController, '_get_image_data')
    @mock.patch('magnum.api.attr_validator.validate_keypair')
    def test_create_baymodel_doesnt_contain_id(self,
                                               mock_keypair_exists,
                                               mock_image_data):
        with mock.patch.object(self.dbapi, 'create_baymodel',
                               wraps=self.dbapi.create_baymodel) as cc_mock:
            mock_keypair_exists.return_value = None
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.baymodel_post_data(image_id='my-image')
            response = self.post_json('/baymodels', bdict)
            self.assertEqual(bdict['image_id'], response.json['image_id'])
            cc_mock.assert_called_once_with(mock.ANY)
            # Check that 'id' is not in first arg of positional args
            self.assertNotIn('id', cc_mock.call_args[0][0])

    def _create_baymodel_raises_app_error(self, **kwargs):
        # Create mock for db and image data
        with mock.patch.object(self.dbapi, 'create_baymodel',
                               wraps=self.dbapi.create_baymodel) as cc_mock,\
            mock.patch.object(api_baymodel.BayModelsController,
                              '_get_image_data') as mock_image_data:
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.baymodel_post_data(**kwargs)
            self.assertRaises(AppError, self.post_json, '/baymodels', bdict)
            self.assertFalse(cc_mock.called)

    def test_create_baymodel_with_invalid_long_string(self):
        fields = ["uuid", "name", "image_id", "flavor_id", "master_flavor_id",
                  "dns_nameserver", "keypair_id", "external_network_id",
                  "cluster_distro", "fixed_network", "apiserver_port",
                  "docker_volume_size", "http_proxy", "https_proxy",
                  "no_proxy", "network_driver", "labels"]
        for field in fields:
            self._create_baymodel_raises_app_error(**{field: 'i' * 256})

    def test_create_baymodel_with_invalid_empty_string(self):
        fields = ["uuid", "name", "image_id", "flavor_id", "master_flavor_id",
                  "dns_nameserver", "keypair_id", "external_network_id",
                  "cluster_distro", "fixed_network", "apiserver_port",
                  "docker_volume_size", "ssh_authorized_key", "labels",
                  "http_proxy", "https_proxy", "no_proxy", "network_driver"]
        for field in fields:
            self._create_baymodel_raises_app_error(**{field: ''})

    def test_create_baymodel_with_invalid_docker_volume_size(self):
        self._create_baymodel_raises_app_error(docker_volume_size=0)
        self._create_baymodel_raises_app_error(docker_volume_size=-1)
        self._create_baymodel_raises_app_error(docker_volume_size='notanint')

    def test_create_baymodel_with_invalid_dns_nameserver(self):
        self._create_baymodel_raises_app_error(dns_nameserver='1.1.2')
        self._create_baymodel_raises_app_error(dns_nameserver='1.1..1')
        self._create_baymodel_raises_app_error(dns_nameserver='openstack.org')

    def test_create_baymodel_with_invalid_apiserver_port(self):
        self._create_baymodel_raises_app_error(apiserver_port=-12)
        self._create_baymodel_raises_app_error(apiserver_port=65536)
        self._create_baymodel_raises_app_error(apiserver_port=0)
        self._create_baymodel_raises_app_error(apiserver_port=1023)
        self._create_baymodel_raises_app_error(apiserver_port='not an int')

    @mock.patch.object(api_baymodel.BayModelsController, '_get_image_data')
    @mock.patch('magnum.api.attr_validator.validate_keypair')
    def test_create_baymodel_with_labels(self, mock_keypair_exists,
                                         mock_image_data):
        with mock.patch.object(self.dbapi, 'create_baymodel',
                               wraps=self.dbapi.create_baymodel) as cc_mock:
            mock_keypair_exists.return_value = None
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.baymodel_post_data(labels={'key1': 'val1',
                                                        'key2': 'val2'})
            response = self.post_json('/baymodels', bdict)
            self.assertEqual(bdict['labels'],
                             response.json['labels'])
            cc_mock.assert_called_once_with(mock.ANY)
            self.assertNotIn('id', cc_mock.call_args[0][0])

    @mock.patch.object(api_baymodel.BayModelsController, '_get_image_data')
    @mock.patch('magnum.api.attr_validator.validate_keypair')
    def test_create_baymodel_with_docker_volume_size(self,
                                                     mock_keypair_exists,
                                                     mock_image_data):
        with mock.patch.object(self.dbapi, 'create_baymodel',
                               wraps=self.dbapi.create_baymodel) as cc_mock:
            mock_keypair_exists.return_value = None
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.baymodel_post_data(docker_volume_size=99)
            response = self.post_json('/baymodels', bdict)
            self.assertEqual(bdict['docker_volume_size'],
                             response.json['docker_volume_size'])
            cc_mock.assert_called_once_with(mock.ANY)
            self.assertNotIn('id', cc_mock.call_args[0][0])

    @mock.patch.object(api_baymodel.BayModelsController, '_get_image_data')
    @mock.patch('magnum.api.attr_validator.validate_keypair')
    def test_create_baymodel_generate_uuid(self,
                                           mock_keypair_exists,
                                           mock_image_data):
        mock_keypair_exists.return_value = None

    @mock.patch.object(api_baymodel.BayModelsController, '_get_image_data')
    @mock.patch('magnum.api.attr_validator.validate_keypair')
    def _test_create_baymodel_network_driver_attr(self,
                                                  baymodel_dict,
                                                  baymodel_config_dict,
                                                  expect_errors,
                                                  mock_keypair_exists,
                                                  mock_image_data):
        mock_keypair_exists.return_value = None
        mock_image_data.return_value = {'name': 'mock_name',
                                        'os_distro': 'fedora-atomic'}
        for k, v in baymodel_config_dict.items():
                    cfg.CONF.set_override(k, v, 'baymodel')
        with mock.patch.object(self.dbapi, 'create_baymodel',
                               wraps=self.dbapi.create_baymodel) as cc_mock:
            bdict = apiutils.baymodel_post_data(**baymodel_dict)
            response = self.post_json('/baymodels', bdict,
                                      expect_errors=expect_errors)
            if expect_errors:
                self.assertEqual(400, response.status_int)
            else:
                expected_driver = bdict.get('network_driver')
                if not expected_driver:
                    expected_driver = (
                        cfg.CONF.baymodel.swarm_default_network_driver)
                self.assertEqual(expected_driver,
                                 response.json['network_driver'])
                self.assertEqual(bdict['image_id'],
                                 response.json['image_id'])
                cc_mock.assert_called_once_with(mock.ANY)
                self.assertNotIn('id', cc_mock.call_args[0][0])
                self.assertTrue(utils.is_uuid_like(response.json['uuid']))

    def test_create_baymodel_with_network_driver(self):
        baymodel_dict = {'coe': 'kubernetes', 'network_driver': 'flannel'}
        config_dict = {}    # Default config
        expect_errors_flag = False
        self._test_create_baymodel_network_driver_attr(baymodel_dict,
                                                       config_dict,
                                                       expect_errors_flag)

    def test_create_baymodel_with_no_network_driver(self):
        baymodel_dict = {}
        config_dict = {}
        expect_errors_flag = False
        self._test_create_baymodel_network_driver_attr(baymodel_dict,
                                                       config_dict,
                                                       expect_errors_flag)

    def test_create_baymodel_with_network_driver_non_def_config(self):
        baymodel_dict = {'coe': 'kubernetes', 'network_driver': 'flannel'}
        config_dict = {
            'kubernetes_allowed_network_drivers': ['flannel', 'foo']}
        expect_errors_flag = False
        self._test_create_baymodel_network_driver_attr(baymodel_dict,
                                                       config_dict,
                                                       expect_errors_flag)

    def test_create_baymodel_with_invalid_network_driver(self):
        baymodel_dict = {'coe': 'kubernetes', 'network_driver': 'bad_driver'}
        config_dict = {
            'kubernetes_allowed_network_drivers': ['flannel', 'good_driver']}
        expect_errors_flag = True
        self._test_create_baymodel_network_driver_attr(baymodel_dict,
                                                       config_dict,
                                                       expect_errors_flag)

    @mock.patch.object(api_baymodel.BayModelsController, '_get_image_data')
    @mock.patch('magnum.api.attr_validator.validate_keypair')
    @mock.patch.object(magnum_policy, 'enforce')
    def test_create_baymodel_public_success(self, mock_policy,
                                            mock_keypair_exists,
                                            mock_image_data):
        with mock.patch.object(self.dbapi, 'create_baymodel',
                               wraps=self.dbapi.create_baymodel) as cc_mock:
            mock_keypair_exists.return_value = None
            mock_policy.return_value = True
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.baymodel_post_data(public=True)
            response = self.post_json('/baymodels', bdict)
            self.assertTrue(response.json['public'])
            mock_policy.assert_called_with(mock.ANY, "baymodel:publish",
                                           None, do_raise=False)
            cc_mock.assert_called_once_with(mock.ANY)
            self.assertNotIn('id', cc_mock.call_args[0][0])
            self.assertTrue(cc_mock.call_args[0][0]['public'])

    @mock.patch.object(api_baymodel.BayModelsController, '_get_image_data')
    @mock.patch('magnum.api.attr_validator.validate_keypair')
    @mock.patch.object(magnum_policy, 'enforce')
    def test_create_baymodel_public_fail(self, mock_policy,
                                         mock_keypair_exists,
                                         mock_image_data):
        with mock.patch.object(self.dbapi, 'create_baymodel',
                               wraps=self.dbapi.create_baymodel):
            mock_keypair_exists.return_value = None
            # make policy enforcement fail
            mock_policy.return_value = False
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.baymodel_post_data(public=True)
            self.assertRaises(AppError, self.post_json, '/baymodels', bdict)

    @mock.patch.object(api_baymodel.BayModelsController, '_get_image_data')
    @mock.patch('magnum.api.attr_validator.validate_keypair')
    @mock.patch.object(magnum_policy, 'enforce')
    def test_create_baymodel_public_not_set(self, mock_policy,
                                            mock_keypair_exists,
                                            mock_image_data):
        with mock.patch.object(self.dbapi, 'create_baymodel',
                               wraps=self.dbapi.create_baymodel) as cc_mock:
            mock_keypair_exists.return_value = None
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.baymodel_post_data(public=False)
            response = self.post_json('/baymodels', bdict)
            self.assertFalse(response.json['public'])
            # policy enforcement is called only once for enforce_wsgi
            mock_policy.assert_called_once_with(mock.ANY, mock.ANY, None)
            cc_mock.assert_called_once_with(mock.ANY)
            self.assertNotIn('id', cc_mock.call_args[0][0])
            self.assertFalse(cc_mock.call_args[0][0]['public'])

    @mock.patch.object(api_baymodel.BayModelsController, '_get_image_data')
    @mock.patch('magnum.api.attr_validator.validate_keypair')
    def test_create_baymodel_with_no_os_distro_image(self,
                                                     mock_keypair_exists,
                                                     mock_image_data):
        mock_keypair_exists.return_value = None
        mock_image_data.return_value = {'name': 'mock_name'}
        bdict = apiutils.baymodel_post_data()
        del bdict['uuid']
        response = self.post_json('/baymodels', bdict, expect_errors=True)
        self.assertEqual(404, response.status_int)

    @mock.patch.object(api_baymodel.BayModelsController, '_get_image_data')
    @mock.patch('magnum.api.attr_validator.validate_keypair')
    def test_create_baymodel_with_os_distro_image(self,
                                                  mock_keypair_exists,
                                                  mock_image_data):
        mock_keypair_exists.return_value = None
        mock_image_data.return_value = {'name': 'mock_name',
                                        'os_distro': 'fedora-atomic'}
        bdict = apiutils.baymodel_post_data()
        del bdict['uuid']
        response = self.post_json('/baymodels', bdict, expect_errors=True)
        self.assertEqual(201, response.status_int)

    @mock.patch.object(openstack_client, 'glance')
    @mock.patch('magnum.api.attr_validator.validate_keypair')
    def test_create_baymodel_with_image_name(self,
                                             mock_keypair_exists,
                                             mock_glance_client):
        mock_keypair_exists.return_value = None
        mock_images = [{'name': 'mock_name',
                       'os_distro': 'fedora-atomic'}]
        mock_glance = mock.MagicMock()
        mock_glance.images.list.return_value = mock_images
        mock_glance_client.return_value = mock_glance
        bdict = apiutils.baymodel_post_data()
        del bdict['uuid']
        response = self.post_json('/baymodels', bdict, expect_errors=True)
        self.assertEqual(201, response.status_int)

    @mock.patch.object(openstack_client, 'glance')
    @mock.patch('magnum.api.attr_validator.validate_keypair')
    def test_create_baymodel_with_no_exist_image_name(self,
                                                      mock_keypair_exists,
                                                      mock_glance_client):
        mock_images = []
        mock_keypair_exists.return_value = None
        mock_glance = mock.MagicMock()
        mock_glance.images.list.return_value = mock_images
        mock_glance_client.return_value = mock_glance
        bdict = apiutils.baymodel_post_data()
        del bdict['uuid']
        response = self.post_json('/baymodels', bdict, expect_errors=True)
        self.assertEqual(404, response.status_int)

    @mock.patch.object(openstack_client, 'glance')
    @mock.patch('magnum.api.attr_validator.validate_keypair')
    def test_create_baymodel_with_multi_image_name(self,
                                                   mock_keypair_exists,
                                                   mock_glance_client):
        mock_keypair_exists.return_value = None
        mock_images = [{'name': 'mock_name',
                       'os_distro': 'fedora-atomic'},
                       {'name': 'mock_name',
                       'os_distro': 'fedora-atomic'}]
        mock_glance = mock.MagicMock()
        mock_glance.images.list.return_value = mock_images
        mock_glance_client.return_value = mock_glance
        bdict = apiutils.baymodel_post_data()
        del bdict['uuid']
        response = self.post_json('/baymodels', bdict, expect_errors=True)
        self.assertEqual(409, response.status_int)

    def test_create_baymodel_without_image_id(self):
        bdict = apiutils.baymodel_post_data()
        del bdict['image_id']
        response = self.post_json('/baymodels', bdict, expect_errors=True)
        self.assertEqual(400, response.status_int)

    def test_create_baymodel_without_keypair_id(self):
        bdict = apiutils.baymodel_post_data()
        del bdict['keypair_id']
        response = self.post_json('/baymodels', bdict, expect_errors=True)
        self.assertEqual(400, response.status_int)

    @mock.patch.object(api_baymodel.BayModelsController, '_get_image_data')
    @mock.patch('magnum.api.attr_validator.validate_keypair')
    def test_create_baymodel_with_dns(self, mock_keypair_exists,
                                      mock_image_data):
        mock_keypair_exists.return_value = None
        mock_image_data.return_value = {'name': 'mock_name',
                                        'os_distro': 'fedora-atomic'}
        bdict = apiutils.baymodel_post_data()
        response = self.post_json('/baymodels', bdict)
        self.assertEqual(201, response.status_int)
        self.assertEqual(bdict['dns_nameserver'],
                         response.json['dns_nameserver'])

    @mock.patch.object(api_baymodel.BayModelsController, '_get_image_data')
    @mock.patch('magnum.api.attr_validator.validate_keypair')
    def test_create_baymodel_with_no_exist_keypair(self,
                                                   mock_keypair_exists,
                                                   mock_image_data):
        mock_keypair_exists.side_effect = exception.KeyPairNotFound("Test")
        mock_image_data.return_value = {'name': 'mock_name',
                                        'os_distro': 'fedora-atomic'}
        bdict = apiutils.baymodel_post_data()
        response = self.post_json('/baymodels', bdict, expect_errors=True)
        self.assertEqual(404, response.status_int)


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


class TestBayModelPolicyEnforcement(api_base.FunctionalTest):

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules({rule: "project:non_fake"})
        exc = self.assertRaises(policy.PolicyNotAuthorized,
                                func, *arg, **kwarg)
        self.assertTrue(exc.message.startswith(rule))
        self.assertTrue(exc.message.endswith("disallowed by policy"))

    def test_policy_disallow_get_all(self):
        self._common_policy_check(
            "baymodel:get_all", self.get_json, '/baymodels')

    def test_policy_disallow_get_one(self):
        self._common_policy_check(
            "baymodel:get", self.get_json, '/baymodels/111-222-333')

    def test_policy_disallow_detail(self):
        self._common_policy_check(
            "baymodel:detail", self.get_json, '/baymodels/111-222-333/detail')

    def test_policy_disallow_update(self):
        baymodel = obj_utils.create_test_baymodel(self.context,
                                                  name='example_A',
                                                  uuid="333-444-5555")
        self._common_policy_check(
            "baymodel:update", self.patch_json,
            '/baymodels/%s' % baymodel.name,
            [{'name': '/name', 'value': "new_name", 'op': 'replace'}])

    def test_policy_disallow_create(self):
        bdict = apiutils.baymodel_post_data(name='bay_model_example_A')
        self._common_policy_check(
            "baymodel:create", self.post_json, '/baymodels', bdict)

    def test_policy_disallow_delete(self):
        baymodel = obj_utils.create_test_baymodel(self.context,
                                                  uuid='137-246-789')
        self._common_policy_check(
            "baymodel:delete", self.delete,
            '/baymodels/%s' % baymodel.uuid)
