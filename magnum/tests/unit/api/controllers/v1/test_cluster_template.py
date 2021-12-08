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
from unittest import mock

from oslo_config import cfg
from oslo_utils import timeutils
from oslo_utils import uuidutils
from six.moves.urllib import parse as urlparse
from webtest.app import AppError
from wsme import types as wtypes

from magnum.api import attr_validator
from magnum.api.controllers.v1 import cluster_template as api_cluster_template
from magnum.common import exception
from magnum.common import policy as magnum_policy
from magnum.tests import base
from magnum.tests.unit.api import base as api_base
from magnum.tests.unit.api import utils as apiutils
from magnum.tests.unit.objects import utils as obj_utils


class TestClusterTemplateObject(base.TestCase):

    def test_cluster_template_init(self):
        cluster_template_dict = apiutils.cluster_template_post_data()
        del cluster_template_dict['image_id']
        del cluster_template_dict['registry_enabled']
        del cluster_template_dict['tls_disabled']
        del cluster_template_dict['public']
        del cluster_template_dict['server_type']
        del cluster_template_dict['master_lb_enabled']
        del cluster_template_dict['floating_ip_enabled']
        del cluster_template_dict['hidden']
        cluster_template = api_cluster_template.ClusterTemplate(
            **cluster_template_dict)
        self.assertEqual(wtypes.Unset, cluster_template.image_id)
        self.assertFalse(cluster_template.registry_enabled)
        self.assertFalse(cluster_template.tls_disabled)
        self.assertFalse(cluster_template.public)
        self.assertEqual('vm', cluster_template.server_type)
        self.assertFalse(cluster_template.master_lb_enabled)
        self.assertTrue(cluster_template.floating_ip_enabled)
        self.assertFalse(cluster_template.hidden)


class TestListClusterTemplate(api_base.FunctionalTest):

    _cluster_template_attrs = ('name', 'apiserver_port', 'network_driver',
                               'coe', 'flavor_id', 'fixed_network',
                               'dns_nameserver', 'http_proxy',
                               'docker_volume_size', 'server_type',
                               'cluster_distro', 'external_network_id',
                               'image_id', 'registry_enabled', 'no_proxy',
                               'keypair_id', 'https_proxy', 'tls_disabled',
                               'public', 'labels', 'master_flavor_id',
                               'volume_driver', 'insecure_registry', 'hidden',
                               'tags',)

    def test_empty(self):
        response = self.get_json('/clustertemplates')
        self.assertEqual([], response['clustertemplates'])

    def test_one(self):
        cluster_template = obj_utils.create_test_cluster_template(self.context)
        response = self.get_json('/clustertemplates')
        self.assertEqual(cluster_template.uuid,
                         response['clustertemplates'][0]["uuid"])
        self._verify_attrs(self._cluster_template_attrs,
                           response['clustertemplates'][0])

    def test_get_one(self):
        cluster_template = obj_utils.create_test_cluster_template(self.context)
        response = self.get_json('/clustertemplates/%s' %
                                 cluster_template['uuid'])
        self.assertEqual(cluster_template.uuid, response['uuid'])
        self._verify_attrs(self._cluster_template_attrs, response)

    def test_get_one_by_name(self):
        cluster_template = obj_utils.create_test_cluster_template(self.context)
        response = self.get_json('/clustertemplates/%s' %
                                 cluster_template['name'])
        self.assertEqual(cluster_template.uuid, response['uuid'])
        self._verify_attrs(self._cluster_template_attrs, response)

    def test_get_one_by_name_not_found(self):
        response = self.get_json(
            '/clustertemplates/not_found',
            expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_get_one_by_uuid(self):
        temp_uuid = uuidutils.generate_uuid()
        obj_utils.create_test_cluster_template(self.context, uuid=temp_uuid)
        response = self.get_json(
            '/clustertemplates/%s' % temp_uuid)
        self.assertEqual(temp_uuid, response['uuid'])

    def test_get_one_by_uuid_not_found(self):
        temp_uuid = uuidutils.generate_uuid()
        response = self.get_json(
            '/clustertemplates/%s' % temp_uuid,
            expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    @mock.patch("magnum.common.policy.enforce")
    @mock.patch("magnum.common.context.make_context")
    def test_get_one_by_uuid_admin(self, mock_context, mock_policy):
        temp_uuid = uuidutils.generate_uuid()
        obj_utils.create_test_cluster_template(self.context, uuid=temp_uuid,
                                               project_id=temp_uuid)
        self.context.is_admin = True
        response = self.get_json(
            '/clustertemplates/%s' % temp_uuid)
        self.assertEqual(temp_uuid, response['uuid'])

    def test_get_one_by_name_multiple_cluster_template(self):
        obj_utils.create_test_cluster_template(
            self.context, name='test_clustertemplate',
            uuid=uuidutils.generate_uuid())
        obj_utils.create_test_cluster_template(
            self.context, name='test_clustertemplate',
            uuid=uuidutils.generate_uuid())
        response = self.get_json(
            '/clustertemplates/test_clustertemplate',
            expect_errors=True)
        self.assertEqual(409, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_get_all_with_pagination_marker(self):
        bm_list = []
        for id_ in range(4):
            cluster_template = obj_utils.create_test_cluster_template(
                self.context, id=id_,
                uuid=uuidutils.generate_uuid())
            bm_list.append(cluster_template)

        response = self.get_json('/clustertemplates?limit=3&marker=%s'
                                 % bm_list[2].uuid)
        self.assertEqual(1, len(response['clustertemplates']))
        self.assertEqual(bm_list[-1].uuid,
                         response['clustertemplates'][0]['uuid'])

    @mock.patch("magnum.common.policy.enforce")
    @mock.patch("magnum.common.context.make_context")
    def test_get_all_with_all_projects(self, mock_context, mock_policy):
        for id_ in range(4):
            obj_utils.create_test_cluster_template(
                self.context, id=id_, project_id=id_,
                uuid=uuidutils.generate_uuid())

        self.context.is_admin = True
        response = self.get_json('/clustertemplates')
        self.assertEqual(4, len(response['clustertemplates']))

    def test_detail(self):
        cluster_template = obj_utils.create_test_cluster_template(self.context)
        response = self.get_json('/clustertemplates/detail')
        self.assertEqual(cluster_template.uuid,
                         response['clustertemplates'][0]["uuid"])
        self._verify_attrs(self._cluster_template_attrs,
                           response['clustertemplates'][0])

    def test_detail_with_pagination_marker(self):
        bm_list = []
        for id_ in range(4):
            cluster_template = obj_utils.create_test_cluster_template(
                self.context, id=id_,
                uuid=uuidutils.generate_uuid())
            bm_list.append(cluster_template)

        response = self.get_json('/clustertemplates/detail?limit=3&marker=%s'
                                 % bm_list[2].uuid)
        self.assertEqual(1, len(response['clustertemplates']))
        self.assertEqual(bm_list[-1].uuid,
                         response['clustertemplates'][0]['uuid'])
        self._verify_attrs(self._cluster_template_attrs,
                           response['clustertemplates'][0])

    def test_detail_against_single(self):
        cluster_template = obj_utils.create_test_cluster_template(self.context)
        response = self.get_json('/clustertemplates/%s/detail' %
                                 cluster_template['uuid'],
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_many(self):
        bm_list = []
        for id_ in range(5):
            cluster_template = obj_utils.create_test_cluster_template(
                self.context, id=id_,
                uuid=uuidutils.generate_uuid())
            bm_list.append(cluster_template.uuid)
        response = self.get_json('/clustertemplates')
        self.assertEqual(len(bm_list), len(response['clustertemplates']))
        uuids = [bm['uuid'] for bm in response['clustertemplates']]
        self.assertEqual(sorted(bm_list), sorted(uuids))

    def test_links(self):
        uuid = uuidutils.generate_uuid()
        obj_utils.create_test_cluster_template(self.context, id=1, uuid=uuid)
        response = self.get_json('/clustertemplates/%s' % uuid)
        self.assertIn('links', response.keys())
        self.assertEqual(2, len(response['links']))
        self.assertIn(uuid, response['links'][0]['href'])
        for link in response['links']:
            bookmark = link['rel'] == 'bookmark'
            self.assertTrue(self.validate_link(link['href'],
                                               bookmark=bookmark))

    def test_collection_links(self):
        for id_ in range(5):
            obj_utils.create_test_cluster_template(
                self.context, id=id_, uuid=uuidutils.generate_uuid())
        response = self.get_json('/clustertemplates/?limit=3')
        self.assertEqual(3, len(response['clustertemplates']))

        next_marker = response['clustertemplates'][-1]['uuid']
        self.assertIn(next_marker, response['next'])

    def test_collection_links_default_limit(self):
        cfg.CONF.set_override('max_limit', 3, 'api')
        for id_ in range(5):
            obj_utils.create_test_cluster_template(
                self.context, id=id_, uuid=uuidutils.generate_uuid())
        response = self.get_json('/clustertemplates')
        self.assertEqual(3, len(response['clustertemplates']))

        next_marker = response['clustertemplates'][-1]['uuid']
        self.assertIn(next_marker, response['next'])


class TestPatch(api_base.FunctionalTest):

    def setUp(self):
        super(TestPatch, self).setUp()
        p = mock.patch.object(attr_validator, 'validate_os_resources')
        self.mock_valid_os_res = p.start()
        self.addCleanup(p.stop)
        self.cluster_template = obj_utils.create_test_cluster_template(
            self.context,
            name='cluster_model_example_A',
            image_id='nerdherd',
            apiserver_port=8080,
            fixed_network='private',
            flavor_id='m1.magnum',
            master_flavor_id='m1.magnum',
            external_network_id='public',
            keypair_id='test',
            volume_driver='rexray',
            public=False,
            docker_volume_size=20,
            coe='swarm',
            labels={'key1': 'val1', 'key2': 'val2'},
            hidden=False
        )

    def test_update_not_found(self):
        uuid = uuidutils.generate_uuid()
        response = self.patch_json('/clustertemplates/%s' % uuid,
                                   [{'path': '/name',
                                     'value': 'cluster_model_example_B',
                                     'op': 'add'}],
                                   expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_update_cluster_template_with_cluster(self):
        cluster_template = obj_utils.create_test_cluster_template(self.context)
        obj_utils.create_test_cluster(
            self.context, cluster_template_id=cluster_template.uuid)

        response = self.patch_json('/clustertemplates/%s' %
                                   cluster_template.uuid,
                                   [{'path': '/network_driver',
                                     'value': 'flannel',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])
        self.assertIn(cluster_template.uuid,
                      response.json['errors'][0]['detail'])

    def test_update_cluster_template_name_with_cluster(self):
        cluster_template = obj_utils.create_test_cluster_template(self.context)
        obj_utils.create_test_cluster(
            self.context, cluster_template_id=cluster_template.uuid)

        response = self.patch_json('/clustertemplates/%s' %
                                   cluster_template.uuid,
                                   [{'path': '/name',
                                     'value': 'cluster_model_example_B',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual(200, response.status_int)

    @mock.patch.object(magnum_policy, 'enforce')
    def test_update_public_cluster_template_success(self, mock_policy):
        mock_policy.return_value = True
        response = self.patch_json('/clustertemplates/%s' %
                                   self.cluster_template.uuid,
                                   [{'path': '/public', 'value': True,
                                     'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json('/clustertemplates/%s' %
                                 self.cluster_template.uuid)
        self.assertTrue(response['public'])

    @mock.patch.object(magnum_policy, 'enforce')
    def test_update_public_cluster_template_fail(self, mock_policy):
        mock_policy.return_value = False
        self.assertRaises(AppError, self.patch_json,
                          '/clustertemplates/%s' % self.cluster_template.uuid,
                          [{'path': '/public', 'value': True,
                            'op': 'replace'}])

    @mock.patch.object(magnum_policy, 'enforce')
    def test_update_cluster_template_with_cluster_allow_update(self,
                                                               mock_policy):
        mock_policy.return_value = True
        cluster_template = obj_utils.create_test_cluster_template(self.context)
        obj_utils.create_test_cluster(
            self.context, cluster_template_id=cluster_template.uuid)
        response = self.patch_json('/clustertemplates/%s' %
                                   cluster_template.uuid,
                                   [{'path': '/public',
                                     'value': True,
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual(200, response.status_int)
        response = self.get_json('/clustertemplates/%s' %
                                 self.cluster_template.uuid)
        self.assertEqual(response['public'], True)

    @mock.patch.object(magnum_policy, 'enforce')
    def test_update_hidden_cluster_template_success(self, mock_policy):
        mock_policy.return_value = True
        response = self.patch_json('/clustertemplates/%s' %
                                   self.cluster_template.uuid,
                                   [{'path': '/hidden', 'value': True,
                                     'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json('/clustertemplates/%s' %
                                 self.cluster_template.uuid)
        self.assertTrue(response['hidden'])

    @mock.patch.object(magnum_policy, 'enforce')
    def test_update_hidden_cluster_template_fail(self, mock_policy):
        mock_policy.return_value = False
        self.assertRaises(AppError, self.patch_json,
                          '/clustertemplates/%s' % self.cluster_template.uuid,
                          [{'path': '/hidden', 'value': True,
                            'op': 'replace'}])

    @mock.patch.object(magnum_policy, 'enforce')
    def test_update_cluster_template_hidden_with_cluster_allow_update(
            self, mock_policy):
        mock_policy.return_value = True
        cluster_template = obj_utils.create_test_cluster_template(self.context)
        obj_utils.create_test_cluster(
            self.context, cluster_template_id=cluster_template.uuid)
        response = self.patch_json('/clustertemplates/%s' %
                                   cluster_template.uuid,
                                   [{'path': '/hidden',
                                     'value': True,
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual(200, response.status_int)
        response = self.get_json('/clustertemplates/%s' %
                                 self.cluster_template.uuid)
        self.assertEqual(response['hidden'], True)

    def test_update_cluster_template_with_devicemapper(self):
        cluster_template = obj_utils.create_test_cluster_template(self.context)
        note = 'deprecated in favor of overlay2'
        with self.assertWarnsRegex(DeprecationWarning, note):
            response = self.patch_json('/clustertemplates/%s' %
                                       cluster_template.uuid,
                                       [{'path': '/docker_storage_driver',
                                         'value': 'devicemapper',
                                         'op': 'replace'}],
                                       expect_errors=True)
        self.assertEqual(200, response.status_int)

    def test_update_cluster_template_replace_labels_success(self):
        cluster_template = obj_utils.create_test_cluster_template(self.context)
        response = self.patch_json('/clustertemplates/%s' %
                                   cluster_template.uuid,
                                   [{'path': '/labels',
                                     'value': '{\'etcd_volume_size\': \'1\'}',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual(200, response.status_int)
        response = self.get_json('/clustertemplates/%s' %
                                 self.cluster_template.uuid)
        self.assertEqual(response['labels'], {'etcd_volume_size': '1'})

    def test_update_cluster_template_with_cluster_not_allow_update(self):
        cluster_template = obj_utils.create_test_cluster_template(self.context)
        obj_utils.create_test_cluster(
            self.context, cluster_template_id=cluster_template.uuid)
        response = self.patch_json('/clustertemplates/%s' %
                                   cluster_template.uuid,
                                   [{'path': '/network_driver',
                                     'value': 'calico',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual(400, response.status_code)

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_singular(self, mock_utcnow):
        name = 'cluster_model_example_B'
        test_time = datetime.datetime(2000, 1, 1, 0, 0)

        mock_utcnow.return_value = test_time
        response = self.patch_json('/clustertemplates/%s' %
                                   self.cluster_template.uuid,
                                   [{'path': '/name', 'value': name,
                                     'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json('/clustertemplates/%s' %
                                 self.cluster_template.uuid)
        self.assertEqual(name, response['name'])
        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)
        # Assert nothing else was changed
        self.assertEqual(self.cluster_template.uuid, response['uuid'])
        self.assertEqual(self.cluster_template.image_id, response['image_id'])
        self.assertEqual(self.cluster_template.apiserver_port,
                         response['apiserver_port'])
        self.assertEqual(self.cluster_template.fixed_network,
                         response['fixed_network'])
        self.assertEqual(self.cluster_template.network_driver,
                         response['network_driver'])
        self.assertEqual(self.cluster_template.volume_driver,
                         response['volume_driver'])
        self.assertEqual(self.cluster_template.docker_volume_size,
                         response['docker_volume_size'])
        self.assertEqual(self.cluster_template.coe,
                         response['coe'])
        self.assertEqual(self.cluster_template.http_proxy,
                         response['http_proxy'])
        self.assertEqual(self.cluster_template.https_proxy,
                         response['https_proxy'])
        self.assertEqual(self.cluster_template.no_proxy,
                         response['no_proxy'])
        self.assertEqual(self.cluster_template.labels,
                         response['labels'])

    def test_replace_cluster_template_with_no_exist_flavor_id(self):
        self.mock_valid_os_res.side_effect = exception.FlavorNotFound("aaa")
        response = self.patch_json('/clustertemplates/%s' %
                                   self.cluster_template.uuid,
                                   [{'path': '/flavor_id', 'value': 'aaa',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['errors'])

    def test_replace_cluster_template_with_no_exist_keypair_id(self):
        self.mock_valid_os_res.side_effect = exception.KeyPairNotFound("aaa")
        response = self.patch_json('/clustertemplates/%s' %
                                   self.cluster_template.uuid,
                                   [{'path': '/keypair_id', 'value': 'aaa',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(404, response.status_code)
        self.assertTrue(response.json['errors'])

    def test_replace_cluster_template_with_no_exist_external_network_id(self):
        self.mock_valid_os_res.side_effect = exception.ExternalNetworkNotFound(
            "aaa")
        response = self.patch_json('/clustertemplates/%s' %
                                   self.cluster_template.uuid,
                                   [{'path': '/external_network_id',
                                     'value': 'aaa',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['errors'])

    def test_replace_cluster_template_with_no_exist_image_id(self):
        self.mock_valid_os_res.side_effect = exception.ImageNotFound("aaa")
        response = self.patch_json('/clustertemplates/%s' %
                                   self.cluster_template.uuid,
                                   [{'path': '/image_id', 'value': 'aaa',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_template_with_no_os_distro_image(self):
        image_exce = exception.OSDistroFieldNotFound('img')
        self.mock_valid_os_res.side_effect = image_exce
        response = self.patch_json('/clustertemplates/%s' %
                                   self.cluster_template.uuid,
                                   [{'path': '/image_id', 'value': 'img',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['errors'])

    def test_remove_singular(self):
        response = self.get_json('/clustertemplates/%s' %
                                 self.cluster_template.uuid)
        self.assertIsNotNone(response['dns_nameserver'])

        response = self.patch_json('/clustertemplates/%s' %
                                   self.cluster_template.uuid,
                                   [{'path': '/dns_nameserver',
                                     'op': 'remove'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json('/clustertemplates/%s' %
                                 self.cluster_template.uuid)
        self.assertIsNone(response['dns_nameserver'])
        # Assert nothing else was changed
        self.assertEqual(self.cluster_template.uuid, response['uuid'])
        self.assertEqual(self.cluster_template.name, response['name'])
        self.assertEqual(self.cluster_template.apiserver_port,
                         response['apiserver_port'])
        self.assertEqual(self.cluster_template.image_id,
                         response['image_id'])
        self.assertEqual(self.cluster_template.fixed_network,
                         response['fixed_network'])
        self.assertEqual(self.cluster_template.network_driver,
                         response['network_driver'])
        self.assertEqual(self.cluster_template.volume_driver,
                         response['volume_driver'])
        self.assertEqual(self.cluster_template.docker_volume_size,
                         response['docker_volume_size'])
        self.assertEqual(self.cluster_template.coe, response['coe'])
        self.assertEqual(self.cluster_template.http_proxy,
                         response['http_proxy'])
        self.assertEqual(self.cluster_template.https_proxy,
                         response['https_proxy'])
        self.assertEqual(self.cluster_template.no_proxy, response['no_proxy'])
        self.assertEqual(self.cluster_template.labels, response['labels'])

    def test_remove_non_existent_property_fail(self):
        response = self.patch_json('/clustertemplates/%s' %
                                   self.cluster_template.uuid,
                                   [{'path': '/non-existent',
                                     'op': 'remove'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['errors'])

    def test_remove_mandatory_property_fail(self):
        mandatory_properties = ('/image_id', '/coe',
                                '/external_network_id', '/server_type',
                                '/tls_disabled', '/public',
                                '/registry_enabled',
                                '/cluster_distro', '/network_driver')
        for p in mandatory_properties:
            response = self.patch_json('/clustertemplates/%s' %
                                       self.cluster_template.uuid,
                                       [{'path': p, 'op': 'remove'}],
                                       expect_errors=True)
            self.assertEqual('application/json', response.content_type)
            self.assertEqual(400, response.status_code)
            self.assertTrue(response.json['errors'])

    def test_add_root_non_existent(self):
        response = self.patch_json(
            '/clustertemplates/%s' % self.cluster_template.uuid,
            [{'path': '/foo', 'value': 'bar', 'op': 'add'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_remove_uuid(self):
        response = self.patch_json('/clustertemplates/%s' %
                                   self.cluster_template.uuid,
                                   [{'path': '/uuid', 'op': 'remove'}],
                                   expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    @mock.patch("magnum.common.policy.enforce")
    @mock.patch("magnum.common.context.make_context")
    def test_update_cluster_template_as_admin(self, mock_context, mock_policy):
        temp_uuid = uuidutils.generate_uuid()
        obj_utils.create_test_cluster_template(self.context, uuid=temp_uuid,
                                               project_id=temp_uuid)
        self.context.is_admin = True
        response = self.patch_json('/clustertemplates/%s' % temp_uuid,
                                   [{'path': '/name',
                                     'value': 'cluster_model_example_B',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual(200, response.status_int)


class TestPost(api_base.FunctionalTest):

    def setUp(self):
        super(TestPost, self).setUp()
        p = mock.patch.object(attr_validator, 'validate_os_resources')
        self.mock_valid_os_res = p.start()
        self.addCleanup(p.stop)

    @mock.patch('magnum.api.attr_validator.validate_image')
    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_cluster_template(self, mock_utcnow,
                                     mock_image_data):
        bdict = apiutils.cluster_template_post_data()
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time
        mock_image_data.return_value = {'name': 'mock_name',
                                        'os_distro': 'fedora-atomic'}

        response = self.post_json('/clustertemplates', bdict)
        self.assertEqual(201, response.status_int)
        # Check location header
        self.assertIsNotNone(response.location)
        expected_location = '/v1/clustertemplates/%s' % bdict['uuid']
        self.assertEqual(expected_location,
                         urlparse.urlparse(response.location).path)
        self.assertEqual(bdict['uuid'], response.json['uuid'])
        self.assertNotIn('updated_at', response.json.keys)
        return_created_at = timeutils.parse_isotime(
            response.json['created_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_created_at)

    @mock.patch('magnum.api.attr_validator.validate_image')
    def test_create_cluster_template_set_project_id_and_user_id(
            self, mock_image_data):
        with mock.patch.object(
                self.dbapi, 'create_cluster_template',
                wraps=self.dbapi.create_cluster_template) as cc_mock:
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.cluster_template_post_data()
            self.post_json('/clustertemplates', bdict)
            cc_mock.assert_called_once_with(mock.ANY)
            self.assertEqual(self.context.project_id,
                             cc_mock.call_args[0][0]['project_id'])
            self.assertEqual(self.context.user_id,
                             cc_mock.call_args[0][0]['user_id'])

    @mock.patch('magnum.api.attr_validator.validate_image')
    def test_create_cluster_template_doesnt_contain_id(self,
                                                       mock_image_data):
        with mock.patch.object(
                self.dbapi, 'create_cluster_template',
                wraps=self.dbapi.create_cluster_template) as cc_mock:
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.cluster_template_post_data(image_id='my-image')
            response = self.post_json('/clustertemplates', bdict)
            self.assertEqual(bdict['image_id'], response.json['image_id'])
            cc_mock.assert_called_once_with(mock.ANY)
            # Check that 'id' is not in first arg of positional args
            self.assertNotIn('id', cc_mock.call_args[0][0])

    def _create_model_raises_app_error(self, **kwargs):
        # Create mock for db and image data
        with mock.patch.object(
                self.dbapi, 'create_cluster_template',
                wraps=self.dbapi.create_cluster_template) as cc_mock,\
            mock.patch('magnum.api.attr_validator.validate_image')\
                as mock_image_data:
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.cluster_template_post_data(**kwargs)
            self.assertRaises(AppError, self.post_json, '/clustertemplates',
                              bdict)
            self.assertFalse(cc_mock.called)

    def test_create_cluster_template_with_invalid_long_string(self):
        fields = ["uuid", "name", "image_id", "flavor_id", "master_flavor_id",
                  "dns_nameserver", "keypair_id", "external_network_id",
                  "cluster_distro", "fixed_network", "apiserver_port",
                  "docker_volume_size", "http_proxy", "https_proxy",
                  "no_proxy", "network_driver", "labels", "volume_driver"]
        for field in fields:
            self._create_model_raises_app_error(**{field: 'i' * 256})

    def test_create_cluster_template_with_invalid_empty_string(self):
        fields = ["uuid", "name", "image_id", "flavor_id", "master_flavor_id",
                  "dns_nameserver", "keypair_id", "external_network_id",
                  "cluster_distro", "fixed_network", "apiserver_port",
                  "docker_volume_size", "labels", "http_proxy", "https_proxy",
                  "no_proxy", "network_driver", "volume_driver", "coe"]
        for field in fields:
            self._create_model_raises_app_error(**{field: ''})

    def test_create_cluster_template_with_invalid_coe(self):
        self._create_model_raises_app_error(coe='k8s')
        self._create_model_raises_app_error(coe='storm')
        self._create_model_raises_app_error(coe='meson')
        self._create_model_raises_app_error(coe='osomatsu')

    def test_create_cluster_template_with_invalid_docker_volume_size(self):
        self._create_model_raises_app_error(docker_volume_size=-1)
        self._create_model_raises_app_error(
            docker_volume_size=1,
            docker_storage_driver="devicemapper")
        self._create_model_raises_app_error(
            docker_volume_size=2,
            docker_storage_driver="devicemapper")
        self._create_model_raises_app_error(docker_volume_size='notanint')

    def test_create_cluster_template_with_invalid_dns_nameserver(self):
        self._create_model_raises_app_error(dns_nameserver='1.1.2')
        self._create_model_raises_app_error(dns_nameserver='1.1..1')
        self._create_model_raises_app_error(dns_nameserver='openstack.org')

    def test_create_cluster_template_with_invalid_apiserver_port(self):
        self._create_model_raises_app_error(apiserver_port=-12)
        self._create_model_raises_app_error(apiserver_port=65536)
        self._create_model_raises_app_error(apiserver_port=0)
        self._create_model_raises_app_error(apiserver_port=1023)
        self._create_model_raises_app_error(apiserver_port='not an int')

    @mock.patch('magnum.api.attr_validator.validate_image')
    def test_create_cluster_template_with_labels(self, mock_image_data):
        with mock.patch.object(
                self.dbapi, 'create_cluster_template',
                wraps=self.dbapi.create_cluster_template) as cc_mock:
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.cluster_template_post_data(
                labels={'key1': 'val1', 'key2': 'val2'})
            response = self.post_json('/clustertemplates', bdict)
            self.assertEqual(bdict['labels'],
                             response.json['labels'])
            cc_mock.assert_called_once_with(mock.ANY)
            self.assertNotIn('id', cc_mock.call_args[0][0])

    @mock.patch('magnum.api.attr_validator.validate_image')
    def test_create_cluster_template_with_docker_volume_size(self,
                                                             mock_image_data):
        with mock.patch.object(
                self.dbapi, 'create_cluster_template',
                wraps=self.dbapi.create_cluster_template) as cc_mock:
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.cluster_template_post_data(docker_volume_size=99)
            response = self.post_json('/clustertemplates', bdict)
            self.assertEqual(bdict['docker_volume_size'],
                             response.json['docker_volume_size'])
            cc_mock.assert_called_once_with(mock.ANY)
            self.assertNotIn('id', cc_mock.call_args[0][0])

    @mock.patch('magnum.api.attr_validator.validate_image')
    def test_create_cluster_template_with_overlay(self, mock_image_data):
        with mock.patch.object(
                self.dbapi, 'create_cluster_template',
                wraps=self.dbapi.create_cluster_template) as cc_mock:
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.cluster_template_post_data(
                docker_volume_size=1, docker_storage_driver="overlay")
            note = 'deprecated in favor of overlay2'
            with self.assertWarnsRegex(DeprecationWarning, note):
                response = self.post_json('/clustertemplates', bdict)
            self.assertEqual(bdict['docker_volume_size'],
                             response.json['docker_volume_size'])
            cc_mock.assert_called_once_with(mock.ANY)
            self.assertNotIn('id', cc_mock.call_args[0][0])

    @mock.patch('magnum.api.attr_validator.validate_image')
    def _test_create_cluster_template_network_driver_attr(
            self,
            cluster_template_dict,
            cluster_template_config_dict,
            expect_errors,
            mock_image_data):
        mock_image_data.return_value = {'name': 'mock_name',
                                        'os_distro': 'fedora-atomic'}
        for k, v in cluster_template_config_dict.items():
            cfg.CONF.set_override(k, v, 'cluster_template')
        with mock.patch.object(
                self.dbapi, 'create_cluster_template',
                wraps=self.dbapi.create_cluster_template) as cc_mock:

            bdict = apiutils.cluster_template_post_data(
                **cluster_template_dict)
            response = self.post_json('/clustertemplates', bdict,
                                      expect_errors=expect_errors)
            if expect_errors:
                self.assertEqual(400, response.status_int)
            else:
                expected_driver = bdict.get('network_driver')
                if not expected_driver:
                    expected_driver = (
                        cfg.CONF.cluster_template.swarm_default_network_driver)
                self.assertEqual(expected_driver,
                                 response.json['network_driver'])
                self.assertEqual(bdict['image_id'],
                                 response.json['image_id'])
                cc_mock.assert_called_once_with(mock.ANY)
                self.assertNotIn('id', cc_mock.call_args[0][0])
                self.assertTrue(uuidutils.is_uuid_like(response.json['uuid']))

    def test_create_cluster_template_with_network_driver(self):
        cluster_template_dict = {'coe': 'kubernetes',
                                 'network_driver': 'flannel'}
        config_dict = {}    # Default config
        expect_errors_flag = False
        self._test_create_cluster_template_network_driver_attr(
            cluster_template_dict,
            config_dict,
            expect_errors_flag)

    def test_create_cluster_template_with_no_network_driver(self):
        cluster_template_dict = {}
        config_dict = {}
        expect_errors_flag = False
        self._test_create_cluster_template_network_driver_attr(
            cluster_template_dict,
            config_dict,
            expect_errors_flag)

    def test_create_cluster_template_with_network_driver_non_def_config(self):
        cluster_template_dict = {'coe': 'kubernetes',
                                 'network_driver': 'flannel'}
        config_dict = {
            'kubernetes_allowed_network_drivers': ['flannel', 'foo']}
        expect_errors_flag = False
        self._test_create_cluster_template_network_driver_attr(
            cluster_template_dict,
            config_dict,
            expect_errors_flag)

    def test_create_cluster_template_with_invalid_network_driver(self):
        cluster_template_dict = {'coe': 'kubernetes',
                                 'network_driver': 'bad_driver'}
        config_dict = {
            'kubernetes_allowed_network_drivers': ['flannel', 'good_driver']}
        expect_errors_flag = True
        self._test_create_cluster_template_network_driver_attr(
            cluster_template_dict,
            config_dict,
            expect_errors_flag)

    @mock.patch('magnum.api.attr_validator.validate_image')
    def test_create_cluster_template_with_volume_driver(self,
                                                        mock_image_data):
        with mock.patch.object(
                self.dbapi, 'create_cluster_template',
                wraps=self.dbapi.create_cluster_template) as cc_mock:
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.cluster_template_post_data(volume_driver='rexray')
            response = self.post_json('/clustertemplates', bdict)
            self.assertEqual(bdict['volume_driver'],
                             response.json['volume_driver'])
            cc_mock.assert_called_once_with(mock.ANY)
            self.assertNotIn('id', cc_mock.call_args[0][0])

    @mock.patch('magnum.api.attr_validator.validate_image')
    def test_create_cluster_template_with_no_volume_driver(self,
                                                           mock_image_data):
        with mock.patch.object(
                self.dbapi, 'create_cluster_template',
                wraps=self.dbapi.create_cluster_template) as cc_mock:
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.cluster_template_post_data()
            response = self.post_json('/clustertemplates', bdict)
            self.assertEqual(bdict['volume_driver'],
                             response.json['volume_driver'])
            cc_mock.assert_called_once_with(mock.ANY)
            self.assertNotIn('id', cc_mock.call_args[0][0])

    @mock.patch('magnum.api.attr_validator.validate_image')
    @mock.patch.object(magnum_policy, 'enforce')
    def test_create_cluster_template_public_success(self, mock_policy,
                                                    mock_image_data):
        with mock.patch.object(
                self.dbapi, 'create_cluster_template',
                wraps=self.dbapi.create_cluster_template) as cc_mock:
            mock_policy.return_value = True
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.cluster_template_post_data(public=True)
            response = self.post_json('/clustertemplates', bdict)
            self.assertTrue(response.json['public'])
            mock_policy.assert_called_with(mock.ANY,
                                           "clustertemplate:publish",
                                           None, do_raise=False)
            cc_mock.assert_called_once_with(mock.ANY)
            self.assertNotIn('id', cc_mock.call_args[0][0])
            self.assertTrue(cc_mock.call_args[0][0]['public'])

    @mock.patch('magnum.api.attr_validator.validate_image')
    @mock.patch.object(magnum_policy, 'enforce')
    def test_create_cluster_template_public_fail(self, mock_policy,
                                                 mock_image_data):
        with mock.patch.object(self.dbapi, 'create_cluster_template',
                               wraps=self.dbapi.create_cluster_template):
            # make policy enforcement fail
            mock_policy.return_value = False
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.cluster_template_post_data(public=True)
            self.assertRaises(AppError, self.post_json, '/clustertemplates',
                              bdict)

    @mock.patch('magnum.api.attr_validator.validate_image')
    @mock.patch.object(magnum_policy, 'enforce')
    def test_create_cluster_template_public_not_set(self, mock_policy,
                                                    mock_image_data):
        with mock.patch.object(
                self.dbapi, 'create_cluster_template',
                wraps=self.dbapi.create_cluster_template) as cc_mock:
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.cluster_template_post_data(public=False)
            response = self.post_json('/clustertemplates', bdict)
            self.assertFalse(response.json['public'])
            # policy enforcement is called only once for enforce_wsgi
            self.assertEqual(1, mock_policy.call_count)
            cc_mock.assert_called_once_with(mock.ANY)
            self.assertNotIn('id', cc_mock.call_args[0][0])
            self.assertFalse(cc_mock.call_args[0][0]['public'])

    @mock.patch('magnum.api.attr_validator.validate_image')
    @mock.patch.object(magnum_policy, 'enforce')
    def test_create_cluster_template_hidden_success(self, mock_policy,
                                                    mock_image_data):
        with mock.patch.object(
                self.dbapi, 'create_cluster_template',
                wraps=self.dbapi.create_cluster_template) as cc_mock:
            mock_policy.return_value = True
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.cluster_template_post_data(hidden=True)
            response = self.post_json('/clustertemplates', bdict)
            self.assertTrue(response.json['hidden'])
            mock_policy.assert_called_with(mock.ANY,
                                           "clustertemplate:publish",
                                           None, do_raise=False)
            cc_mock.assert_called_once_with(mock.ANY)
            self.assertNotIn('id', cc_mock.call_args[0][0])
            self.assertTrue(cc_mock.call_args[0][0]['hidden'])

    @mock.patch('magnum.api.attr_validator.validate_image')
    @mock.patch.object(magnum_policy, 'enforce')
    def test_create_cluster_template_hidden_fail(self, mock_policy,
                                                 mock_image_data):
        with mock.patch.object(self.dbapi, 'create_cluster_template',
                               wraps=self.dbapi.create_cluster_template):
            # make policy enforcement fail
            mock_policy.return_value = False
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.cluster_template_post_data(hidden=True)
            self.assertRaises(AppError, self.post_json, '/clustertemplates',
                              bdict)

    @mock.patch('magnum.api.attr_validator.validate_image')
    def test_create_cluster_template_with_no_os_distro_image(self,
                                                             mock_image_data):
        mock_image_data.side_effect = exception.OSDistroFieldNotFound('img')
        bdict = apiutils.cluster_template_post_data()
        del bdict['uuid']
        response = self.post_json('/clustertemplates', bdict,
                                  expect_errors=True)
        self.assertEqual(400, response.status_int)

    @mock.patch('magnum.api.attr_validator.validate_image')
    def test_create_cluster_template_with_os_distro_image(self,
                                                          mock_image_data):
        mock_image_data.return_value = {'name': 'mock_name',
                                        'os_distro': 'fedora-atomic'}
        bdict = apiutils.cluster_template_post_data()
        del bdict['uuid']
        response = self.post_json('/clustertemplates', bdict,
                                  expect_errors=True)
        self.assertEqual(201, response.status_int)

    @mock.patch('magnum.api.attr_validator.validate_image')
    def test_create_cluster_template_with_image_name(self,
                                                     mock_image_data):
        mock_image = {'name': 'mock_name',
                      'os_distro': 'fedora-atomic'}
        mock_image_data.return_value = mock_image
        bdict = apiutils.cluster_template_post_data()
        del bdict['uuid']
        response = self.post_json('/clustertemplates', bdict,
                                  expect_errors=True)
        self.assertEqual(201, response.status_int)

    @mock.patch('magnum.api.attr_validator.validate_image')
    def test_create_cluster_template_with_no_exist_image_name(self,
                                                              mock_image_data):
        mock_image_data.side_effect = exception.ResourceNotFound('test-img')
        bdict = apiutils.cluster_template_post_data()
        del bdict['uuid']
        response = self.post_json('/clustertemplates', bdict,
                                  expect_errors=True)
        self.assertEqual(404, response.status_int)

    @mock.patch('magnum.api.attr_validator.validate_image')
    def test_create_cluster_template_with_multi_image_name(self,
                                                           mock_image_data):
        mock_image_data.side_effect = exception.Conflict('Multiple images')
        bdict = apiutils.cluster_template_post_data()
        del bdict['uuid']
        response = self.post_json('/clustertemplates', bdict,
                                  expect_errors=True)
        self.assertEqual(409, response.status_int)

    def test_create_cluster_template_without_image_id(self):
        bdict = apiutils.cluster_template_post_data()
        del bdict['image_id']
        response = self.post_json('/clustertemplates', bdict,
                                  expect_errors=True)
        self.assertEqual(400, response.status_int)

    @mock.patch('magnum.api.attr_validator.validate_image')
    def test_create_cluster_template_without_keypair_id(self,
                                                        mock_image_data):
        mock_image_data.return_value = {'name': 'mock_name',
                                        'os_distro': 'fedora-atomic'}
        bdict = apiutils.cluster_template_post_data()
        del bdict['keypair_id']
        response = self.post_json('/clustertemplates', bdict)
        self.assertEqual(201, response.status_int)

    @mock.patch('magnum.api.attr_validator.validate_image')
    def test_create_cluster_template_with_dns(self,
                                              mock_image_data):
        mock_image_data.return_value = {'name': 'mock_name',
                                        'os_distro': 'fedora-atomic'}
        bdict = apiutils.cluster_template_post_data()
        response = self.post_json('/clustertemplates', bdict)
        self.assertEqual(201, response.status_int)
        self.assertEqual(bdict['dns_nameserver'],
                         response.json['dns_nameserver'])

    @mock.patch('magnum.api.attr_validator.validate_image')
    def test_create_cluster_template_with_no_exist_keypair(self,
                                                           mock_image_data):
        self.mock_valid_os_res.side_effect = exception.KeyPairNotFound("Test")
        mock_image_data.return_value = {'name': 'mock_name',
                                        'os_distro': 'fedora-atomic'}
        bdict = apiutils.cluster_template_post_data()
        response = self.post_json('/clustertemplates', bdict,
                                  expect_errors=True)
        self.assertEqual(404, response.status_int)

    @mock.patch('magnum.api.attr_validator.validate_image')
    def test_create_cluster_template_with_flavor(self,
                                                 mock_image_data):
        mock_image_data.return_value = {'name': 'mock_name',
                                        'os_distro': 'fedora-atomic'}
        bdict = apiutils.cluster_template_post_data()
        response = self.post_json('/clustertemplates', bdict)
        self.assertEqual(201, response.status_int)
        self.assertEqual(bdict['flavor_id'],
                         response.json['flavor_id'])
        self.assertEqual(bdict['master_flavor_id'],
                         response.json['master_flavor_id'])

    @mock.patch('magnum.api.attr_validator.validate_image')
    def test_create_cluster_template_with_no_exist_flavor(self,
                                                          mock_image_data):
        self.mock_valid_os_res.side_effect = exception.FlavorNotFound("flavor")
        mock_image_data.return_value = {'name': 'mock_name',
                                        'os_distro': 'fedora-atomic'}
        bdict = apiutils.cluster_template_post_data()
        response = self.post_json('/clustertemplates', bdict,
                                  expect_errors=True)
        self.assertEqual(400, response.status_int)

    @mock.patch('magnum.api.attr_validator.validate_image')
    def test_create_cluster_template_with_external_network(self,
                                                           mock_image_data):
        mock_image_data.return_value = {'name': 'mock_name',
                                        'os_distro': 'fedora-atomic'}
        bdict = apiutils.cluster_template_post_data()
        response = self.post_json('/clustertemplates', bdict)
        self.assertEqual(201, response.status_int)
        self.assertEqual(bdict['external_network_id'],
                         response.json['external_network_id'])

    @mock.patch('magnum.api.attr_validator.validate_image')
    def test_create_cluster_template_no_exist_external_network(
            self, mock_image_data):
        self.mock_valid_os_res.side_effect = exception.ExternalNetworkNotFound(
            "test")
        mock_image_data.return_value = {'name': 'mock_name',
                                        'os_distro': 'fedora-atomic'}
        bdict = apiutils.cluster_template_post_data()
        response = self.post_json('/clustertemplates', bdict,
                                  expect_errors=True)
        self.assertEqual(400, response.status_int)

    @mock.patch('magnum.api.attr_validator.validate_image')
    def test_create_cluster_template_without_name(self, mock_image_data):
        with mock.patch.object(self.dbapi, 'create_cluster_template',
                               wraps=self.dbapi.create_cluster_template):
            mock_image_data.return_value = {'name': 'mock_name',
                                            'os_distro': 'fedora-atomic'}
            bdict = apiutils.cluster_template_post_data()
            bdict.pop('name')
            resp = self.post_json('/clustertemplates', bdict)
            self.assertEqual(201, resp.status_int)
            self.assertIsNotNone(resp.json['name'])

    def test_create_cluster_with_disabled_driver(self):
        cfg.CONF.set_override('disabled_drivers',
                              ['swarm_fedora_atomic_v1'],
                              group='drivers')
        bdict = apiutils.cluster_template_post_data(coe="swarm")
        self.assertRaises(AppError, self.post_json, '/clustertemplates',
                          bdict)

    @mock.patch('magnum.api.attr_validator.validate_image')
    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_cluster_template_with_multi_dns(self, mock_utcnow,
                                                    mock_image_data):
        bdict = apiutils.cluster_template_post_data(
            dns_nameserver="8.8.8.8,114.114.114.114")
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time
        mock_image_data.return_value = {'name': 'mock_name',
                                        'os_distro': 'fedora-atomic'}

        response = self.post_json('/clustertemplates', bdict)
        self.assertEqual(201, response.status_int)
        # Check location header
        self.assertIsNotNone(response.location)
        expected_location = '/v1/clustertemplates/%s' % bdict['uuid']
        self.assertEqual(expected_location,
                         urlparse.urlparse(response.location).path)
        self.assertEqual(bdict['uuid'], response.json['uuid'])
        self.assertNotIn('updated_at', response.json.keys)
        return_created_at = timeutils.parse_isotime(
            response.json['created_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_created_at)


class TestDelete(api_base.FunctionalTest):

    def test_delete_cluster_template(self):
        cluster_template = obj_utils.create_test_cluster_template(self.context)
        self.delete('/clustertemplates/%s' % cluster_template.uuid)
        response = self.get_json('/clustertemplates/%s' %
                                 cluster_template.uuid,
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_delete_cluster_template_with_cluster(self):
        cluster_template = obj_utils.create_test_cluster_template(self.context)
        obj_utils.create_test_cluster(
            self.context, cluster_template_id=cluster_template.uuid)
        response = self.delete('/clustertemplates/%s' % cluster_template.uuid,
                               expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])
        self.assertIn(cluster_template.uuid,
                      response.json['errors'][0]['detail'])

    def test_delete_cluster_template_not_found(self):
        uuid = uuidutils.generate_uuid()
        response = self.delete('/clustertemplates/%s' % uuid,
                               expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_delete_cluster_template_with_name(self):
        cluster_template = obj_utils.create_test_cluster_template(self.context)
        response = self.delete('/clustertemplates/%s' %
                               cluster_template['name'],
                               expect_errors=True)
        self.assertEqual(204, response.status_int)

    def test_delete_cluster_template_with_name_not_found(self):
        response = self.delete('/clustertemplates/not_found',
                               expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_delete_multiple_cluster_template_by_name(self):
        obj_utils.create_test_cluster_template(self.context,
                                               name='test_cluster_template',
                                               uuid=uuidutils.generate_uuid())
        obj_utils.create_test_cluster_template(self.context,
                                               name='test_cluster_template',
                                               uuid=uuidutils.generate_uuid())
        response = self.delete('/clustertemplates/test_cluster_template',
                               expect_errors=True)
        self.assertEqual(409, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    @mock.patch("magnum.common.policy.enforce")
    @mock.patch("magnum.common.context.make_context")
    def test_delete_cluster_template_as_admin(self, mock_context, mock_policy):
        temp_uuid = uuidutils.generate_uuid()
        obj_utils.create_test_cluster_template(self.context, uuid=temp_uuid,
                                               project_id=temp_uuid)
        self.context.is_admin = True
        response = self.delete('/clustertemplates/%s' % temp_uuid,
                               expect_errors=True)
        self.assertEqual(204, response.status_int)


class TestClusterTemplatePolicyEnforcement(api_base.FunctionalTest):

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules({rule: "project:non_fake"})
        response = func(*arg, **kwarg)
        self.assertEqual(403, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(
            "Policy doesn't allow %s to be performed." % rule,
            response.json['errors'][0]['detail'])

    def test_policy_disallow_get_all(self):
        self._common_policy_check(
            "cluster_template:get_all", self.get_json, '/clustertemplates',
            expect_errors=True)

    def test_policy_disallow_get_one(self):
        cluster_template = obj_utils.create_test_cluster_template(self.context)
        self._common_policy_check(
            "cluster_template:get", self.get_json,
            '/clustertemplates/%s' % cluster_template.uuid,
            expect_errors=True)

    def test_policy_disallow_detail(self):
        self._common_policy_check(
            "cluster_template:detail", self.get_json,
            '/clustertemplates/%s/detail' % uuidutils.generate_uuid(),
            expect_errors=True)

    def test_policy_disallow_update(self):
        cluster_template = obj_utils.create_test_cluster_template(
            self.context,
            name='example_A',
            uuid=uuidutils.generate_uuid())
        self._common_policy_check(
            "cluster_template:update", self.patch_json,
            '/clustertemplates/%s' % cluster_template.name,
            [{'path': '/name', 'value': "new_name", 'op': 'replace'}],
            expect_errors=True)

    def test_policy_disallow_create(self):
        bdict = apiutils.cluster_template_post_data(
            name='cluster_model_example_A')
        self._common_policy_check(
            "cluster_template:create", self.post_json, '/clustertemplates',
            bdict, expect_errors=True)

    def test_policy_disallow_delete(self):
        cluster_template = obj_utils.create_test_cluster_template(self.context)
        self._common_policy_check(
            "cluster_template:delete", self.delete,
            '/clustertemplates/%s' % cluster_template.uuid, expect_errors=True)

    def _owner_check(self, rule, func, *args, **kwargs):
        self.policy.set_rules({rule: "user_id:%(user_id)s"})
        response = func(*args, **kwargs)
        self.assertEqual(403, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(
            "Policy doesn't allow %s to be performed." % rule,
            response.json['errors'][0]['detail'])

    def test_policy_only_owner_get_one(self):
        cluster_template = obj_utils.create_test_cluster_template(
            self.context,
            user_id='another')
        self._owner_check("cluster_template:get", self.get_json,
                          '/clustertemplates/%s' % cluster_template.uuid,
                          expect_errors=True)

    def test_policy_only_owner_update(self):
        cluster_template = obj_utils.create_test_cluster_template(
            self.context,
            user_id='another')
        self._owner_check(
            "cluster_template:update", self.patch_json,
            '/clustertemplates/%s' % cluster_template.uuid,
            [{'path': '/name', 'value': "new_name", 'op': 'replace'}],
            expect_errors=True)

    def test_policy_only_owner_delete(self):
        cluster_template = obj_utils.create_test_cluster_template(
            self.context,
            user_id='another')
        self._owner_check(
            "cluster_template:delete", self.delete,
            '/clustertemplates/%s' % cluster_template.uuid,
            expect_errors=True)
