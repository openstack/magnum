# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock
from mock import patch

import magnum.conf
from magnum.drivers.heat import driver as heat_driver
from magnum.drivers.swarm_fedora_atomic_v1 import driver as swarm_dr
from magnum import objects
from magnum.objects.fields import ClusterStatus as cluster_status
from magnum.tests import base

CONF = magnum.conf.CONF


class TestClusterConductorWithSwarm(base.TestCase):
    def setUp(self):
        super(TestClusterConductorWithSwarm, self).setUp()
        self.cluster_template_dict = {
            'image_id': 'image_id',
            'flavor_id': 'flavor_id',
            'master_flavor_id': 'master_flavor_id',
            'keypair_id': 'keypair_id',
            'dns_nameserver': 'dns_nameserver',
            'docker_volume_size': 20,
            'docker_storage_driver': 'devicemapper',
            'external_network_id': 'external_network_id',
            'cluster_distro': 'fedora-atomic',
            'coe': 'swarm',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'tls_disabled': False,
            'registry_enabled': False,
            'server_type': 'vm',
            'network_driver': 'network_driver',
            'labels': {'flannel_network_cidr': '10.101.0.0/16',
                       'flannel_network_subnetlen': '26',
                       'flannel_backend': 'vxlan',
                       'rexray_preempt': 'False',
                       'swarm_strategy': 'spread'},
            'master_lb_enabled': False,
            'volume_driver': 'rexray'
        }
        self.cluster_dict = {
            'id': 1,
            'uuid': '5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            'cluster_template_id': 'xx-xx-xx-xx',
            'keypair': 'keypair_id',
            'name': 'cluster1',
            'stack_id': 'xx-xx-xx-xx',
            'api_address': '172.17.2.3',
            'node_addresses': ['172.17.2.4'],
            'master_count': 1,
            'node_count': 1,
            'discovery_url': 'https://discovery.test.io/123456789',
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': 'bd11efc5-d4e2-4dac-bbce-25e348ddf7de',
            'coe_version': 'fake-version'
        }
        osc_patcher = mock.patch('magnum.common.clients.OpenStackClients')
        self.mock_osc_class = osc_patcher.start()
        self.addCleanup(osc_patcher.stop)
        self.mock_osc = mock.MagicMock()
        self.mock_osc.magnum_url.return_value = 'http://127.0.0.1:9511/v1'
        self.mock_keystone = mock.MagicMock()
        self.mock_keystone.trustee_domain_id = 'trustee_domain_id'
        self.mock_osc.keystone.return_value = self.mock_keystone
        self.mock_osc_class.return_value = self.mock_osc
        self.context.auth_url = 'http://192.168.10.10:5000/v3'

    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_extract_template_definition_all_values(
            self,
            mock_driver,
            mock_objects_cluster_template_get_by_uuid,
            mock_get):
        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_objects_cluster_template_get_by_uuid.return_value = \
            cluster_template
        expected_result = str('{"action":"get","node":{"key":"test","value":'
                              '"1","modifiedIndex":10,"createdIndex":10}}')
        mock_resp = mock.MagicMock()
        mock_resp.text = expected_result
        mock_get.return_value = mock_resp
        mock_driver.return_value = swarm_dr.Driver()
        cluster = objects.Cluster(self.context, **self.cluster_dict)

        (template_path,
         definition,
         env_files) = mock_driver()._extract_template_definition(self.context,
                                                                 cluster)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'master_flavor': 'master_flavor_id',
            'node_flavor': 'flavor_id',
            'number_of_masters': 1,
            'number_of_nodes': 1,
            'docker_volume_size': 20,
            'docker_storage_driver': 'devicemapper',
            'discovery_url': 'https://discovery.test.io/123456789',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'cluster_uuid': '5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'tls_disabled': False,
            'registry_enabled': False,
            'network_driver': 'network_driver',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_backend': 'vxlan',
            'trustee_domain_id': self.mock_keystone.trustee_domain_id,
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': 'bd11efc5-d4e2-4dac-bbce-25e348ddf7de',
            'auth_url': 'http://192.168.10.10:5000/v3',
            'swarm_version': 'fake-version',
            'swarm_strategy': u'spread',
            'volume_driver': 'rexray',
            'rexray_preempt': 'False'
        }
        self.assertEqual(expected, definition)
        self.assertEqual(
            ['../../common/templates/environments/with_volume.yaml',
             '../../common/templates/environments/no_master_lb.yaml'],
            env_files)

    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_extract_template_definition_with_registry(
            self,
            mock_driver,
            mock_objects_cluster_template_get_by_uuid,
            mock_get):
        self.cluster_template_dict['registry_enabled'] = True
        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_objects_cluster_template_get_by_uuid.return_value = \
            cluster_template
        expected_result = str('{"action":"get","node":{"key":"test","value":'
                              '"1","modifiedIndex":10,"createdIndex":10}}')
        mock_resp = mock.MagicMock()
        mock_resp.text = expected_result
        mock_get.return_value = mock_resp
        mock_driver.return_value = swarm_dr.Driver()
        cluster = objects.Cluster(self.context, **self.cluster_dict)

        CONF.set_override('swift_region',
                          'RegionOne',
                          group='docker_registry')

        (template_path,
         definition,
         env_files) = mock_driver()._extract_template_definition(self.context,
                                                                 cluster)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'master_flavor': 'master_flavor_id',
            'node_flavor': 'flavor_id',
            'number_of_masters': 1,
            'number_of_nodes': 1,
            'docker_volume_size': 20,
            'discovery_url': 'https://discovery.test.io/123456789',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'cluster_uuid': '5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'tls_disabled': False,
            'registry_enabled': True,
            'registry_container': 'docker_registry',
            'swift_region': 'RegionOne',
            'network_driver': 'network_driver',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_backend': 'vxlan',
            'trustee_domain_id': self.mock_keystone.trustee_domain_id,
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': 'bd11efc5-d4e2-4dac-bbce-25e348ddf7de',
            'auth_url': 'http://192.168.10.10:5000/v3',
            'docker_storage_driver': 'devicemapper',
            'swarm_version': 'fake-version',
            'swarm_strategy': u'spread',
            'volume_driver': 'rexray',
            'rexray_preempt': 'False'
        }
        self.assertEqual(expected, definition)
        self.assertEqual(
            ['../../common/templates/environments/with_volume.yaml',
             '../../common/templates/environments/no_master_lb.yaml'],
            env_files)

    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_extract_template_definition_only_required(
            self,
            mock_driver,
            mock_objects_cluster_template_get_by_uuid,
            mock_get):

        not_required = ['image_id', 'flavor_id', 'dns_nameserver',
                        'docker_volume_size', 'fixed_network', 'http_proxy',
                        'https_proxy', 'no_proxy', 'network_driver',
                        'master_flavor_id', 'docker_storage_driver',
                        'volume_driver', 'rexray_preempt']
        for key in not_required:
            self.cluster_template_dict[key] = None
        self.cluster_dict['discovery_url'] = 'https://discovery.etcd.io/test'

        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_objects_cluster_template_get_by_uuid.return_value = \
            cluster_template
        expected_result = str('{"action":"get","node":{"key":"test","value":'
                              '"1","modifiedIndex":10,"createdIndex":10}}')
        mock_resp = mock.MagicMock()
        mock_resp.text = expected_result
        mock_get.return_value = mock_resp
        mock_driver.return_value = swarm_dr.Driver()
        cluster = objects.Cluster(self.context, **self.cluster_dict)

        (template_path,
         definition,
         env_files) = mock_driver()._extract_template_definition(self.context,
                                                                 cluster)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'number_of_masters': 1,
            'number_of_nodes': 1,
            'discovery_url': 'https://discovery.etcd.io/test',
            'cluster_uuid': '5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'tls_disabled': False,
            'registry_enabled': False,
            'flannel_network_cidr': u'10.101.0.0/16',
            'flannel_network_subnetlen': u'26',
            'flannel_backend': u'vxlan',
            'trustee_domain_id': self.mock_keystone.trustee_domain_id,
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': 'bd11efc5-d4e2-4dac-bbce-25e348ddf7de',
            'auth_url': 'http://192.168.10.10:5000/v3',
            'swarm_version': 'fake-version',
            'swarm_strategy': u'spread',
            'rexray_preempt': 'False'
        }
        self.assertEqual(expected, definition)
        self.assertEqual(
            ['../../common/templates/environments/no_volume.yaml',
             '../../common/templates/environments/no_master_lb.yaml'],
            env_files)

    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_extract_template_definition_with_lb(
            self,
            mock_driver,
            mock_objects_cluster_template_get_by_uuid,
            mock_get):
        self.cluster_template_dict['master_lb_enabled'] = True
        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_objects_cluster_template_get_by_uuid.return_value = \
            cluster_template
        expected_result = str('{"action":"get","node":{"key":"test","value":'
                              '"1","modifiedIndex":10,"createdIndex":10}}')
        mock_resp = mock.MagicMock()
        mock_resp.text = expected_result
        mock_get.return_value = mock_resp
        mock_driver.return_value = swarm_dr.Driver()
        cluster = objects.Cluster(self.context, **self.cluster_dict)

        (template_path,
         definition,
         env_files) = mock_driver()._extract_template_definition(self.context,
                                                                 cluster)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'master_flavor': 'master_flavor_id',
            'node_flavor': 'flavor_id',
            'number_of_masters': 1,
            'number_of_nodes': 1,
            'docker_volume_size': 20,
            'docker_storage_driver': 'devicemapper',
            'discovery_url': 'https://discovery.test.io/123456789',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'cluster_uuid': '5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'tls_disabled': False,
            'registry_enabled': False,
            'network_driver': 'network_driver',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_backend': 'vxlan',
            'trustee_domain_id': self.mock_keystone.trustee_domain_id,
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': 'bd11efc5-d4e2-4dac-bbce-25e348ddf7de',
            'auth_url': 'http://192.168.10.10:5000/v3',
            'swarm_version': 'fake-version',
            'swarm_strategy': u'spread',
            'volume_driver': 'rexray',
            'rexray_preempt': 'False'
        }
        self.assertEqual(expected, definition)
        self.assertEqual(
            ['../../common/templates/environments/with_volume.yaml',
             '../../common/templates/environments/with_master_lb.yaml'],
            env_files)

    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_extract_template_definition_multi_master(
            self,
            mock_driver,
            mock_objects_cluster_template_get_by_uuid,
            mock_get):
        self.cluster_template_dict['master_lb_enabled'] = True
        self.cluster_dict['master_count'] = 2
        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_objects_cluster_template_get_by_uuid.return_value = \
            cluster_template
        expected_result = str('{"action":"get","node":{"key":"test","value":'
                              '"2","modifiedIndex":10,"createdIndex":10}}')
        mock_resp = mock.MagicMock()
        mock_resp.text = expected_result
        mock_get.return_value = mock_resp
        mock_driver.return_value = swarm_dr.Driver()
        cluster = objects.Cluster(self.context, **self.cluster_dict)

        (template_path,
         definition,
         env_files) = mock_driver()._extract_template_definition(self.context,
                                                                 cluster)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'master_flavor': 'master_flavor_id',
            'node_flavor': 'flavor_id',
            'number_of_masters': 2,
            'number_of_nodes': 1,
            'docker_volume_size': 20,
            'docker_storage_driver': 'devicemapper',
            'discovery_url': 'https://discovery.test.io/123456789',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'cluster_uuid': '5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'tls_disabled': False,
            'registry_enabled': False,
            'network_driver': 'network_driver',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_backend': 'vxlan',
            'trustee_domain_id': self.mock_keystone.trustee_domain_id,
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': 'bd11efc5-d4e2-4dac-bbce-25e348ddf7de',
            'auth_url': 'http://192.168.10.10:5000/v3',
            'swarm_version': 'fake-version',
            'swarm_strategy': u'spread',
            'volume_driver': 'rexray',
            'rexray_preempt': 'False'
        }
        self.assertEqual(expected, definition)
        self.assertEqual(
            ['../../common/templates/environments/with_volume.yaml',
             '../../common/templates/environments/with_master_lb.yaml'],
            env_files)

    @patch('magnum.conductor.utils.retrieve_cluster_template')
    @patch('magnum.conf.CONF')
    @patch('magnum.common.clients.OpenStackClients')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def setup_poll_test(self, mock_driver, mock_openstack_client, mock_conf,
                        mock_retrieve_cluster_template):
        mock_conf.cluster_heat.max_attempts = 10

        cluster = mock.MagicMock()
        mock_heat_stack = mock.MagicMock()
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client.heat.return_value = mock_heat_client
        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_retrieve_cluster_template.return_value = \
            cluster_template
        mock_driver.return_value = swarm_dr.Driver()
        poller = heat_driver.HeatPoller(mock_openstack_client,
                                        mock.MagicMock(), cluster,
                                        swarm_dr.Driver())
        poller.get_version_info = mock.MagicMock()
        return (mock_heat_stack, cluster, poller)

    def test_poll_node_count(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.parameters = {'number_of_nodes': 1}
        mock_heat_stack.stack_status = cluster_status.CREATE_IN_PROGRESS
        poller.poll_and_check()

        self.assertEqual(1, cluster.node_count)

    def test_poll_node_count_by_update(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.parameters = {'number_of_nodes': 2}
        mock_heat_stack.stack_status = cluster_status.UPDATE_COMPLETE
        poller.poll_and_check()

        self.assertEqual(2, cluster.node_count)
