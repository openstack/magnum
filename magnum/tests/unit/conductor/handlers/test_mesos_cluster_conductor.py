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

from unittest import mock
from unittest.mock import patch

from magnum.drivers.heat import driver as heat_driver
from magnum.drivers.mesos_ubuntu_v1 import driver as mesos_dr
from magnum import objects
from magnum.objects.fields import ClusterStatus as cluster_status
from magnum.tests import base


class TestClusterConductorWithMesos(base.TestCase):
    def setUp(self):
        super(TestClusterConductorWithMesos, self).setUp()
        self.cluster_template_dict = {
            'image_id': 'image_id',
            'flavor_id': 'flavor_id',
            'master_flavor_id': 'master_flavor_id',
            'keypair_id': 'keypair_id',
            'dns_nameserver': 'dns_nameserver',
            'external_network_id': 'external_network_id',
            'cluster_distro': 'ubuntu',
            'coe': 'mesos',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'registry_enabled': False,
            'server_type': 'vm',
            'volume_driver': 'volume_driver',
            'labels': {'rexray_preempt': 'False',
                       'mesos_slave_isolation':
                       'docker/runtime,filesystem/linux',
                       'mesos_slave_image_providers': 'docker',
                       'mesos_slave_executor_env_variables': '{}',
                       'mesos_slave_work_dir': '/tmp/mesos/slave'
                       },
            'master_lb_enabled': False,
            'fixed_network': 'fixed_network',
            'fixed_subnet': 'fixed_subnet',
        }
        self.cluster_dict = {
            'id': 1,
            'uuid': '5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            'cluster_template_id': 'xx-xx-xx-xx',
            'keypair': 'keypair_id',
            'master_flavor_id': 'master_flavor_id',
            'flavor_id': 'flavor_id',
            'name': 'cluster1',
            'stack_id': 'xx-xx-xx-xx',
            'api_address': '172.17.2.3',
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': 'bd11efc5-d4e2-4dac-bbce-25e348ddf7de',
            'labels': {'rexray_preempt': 'False',
                       'mesos_slave_isolation':
                       'docker/runtime,filesystem/linux',
                       'mesos_slave_image_providers': 'docker',
                       'mesos_slave_executor_env_variables': '{}',
                       'mesos_slave_work_dir': '/tmp/mesos/slave'
                       },
            'fixed_network': '',
            'fixed_subnet': '',
            'floating_ip_enabled': False,
            'master_lb_enabled': False,
        }
        self.worker_ng_dict = {
            'uuid': '5d12f6fd-a196-4bf0-ae4c-1f639a523a53',
            'name': 'worker_ng',
            'cluster_id': '5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            'project_id': 'project_id',
            'docker_volume_size': 20,
            'labels': self.cluster_dict['labels'],
            'flavor_id': 'flavor_id',
            'image_id': 'image_id',
            'node_addresses': ['172.17.2.4'],
            'node_count': 1,
            'role': 'worker',
            'max_nodes': 5,
            'min_nodes': 1,
            'is_default': True
        }
        self.master_ng_dict = {
            'uuid': '5d12f6fd-a196-4bf0-ae4c-1f639a523a54',
            'name': 'master_ng',
            'cluster_id': '5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            'project_id': 'project_id',
            'docker_volume_size': 20,
            'labels': self.cluster_dict['labels'],
            'flavor_id': 'master_flavor_id',
            'image_id': 'image_id',
            'node_addresses': ['172.17.2.18'],
            'node_count': 1,
            'role': 'master',
            'max_nodes': 5,
            'min_nodes': 1,
            'is_default': True
        }
        self.context.user_name = 'mesos_user'
        self.context.project_id = 'admin'
        self.context.domain_name = 'domainname'
        osc_patcher = mock.patch('magnum.common.clients.OpenStackClients')
        self.mock_osc_class = osc_patcher.start()
        self.addCleanup(osc_patcher.stop)
        self.mock_osc = mock.MagicMock()
        self.mock_osc.cinder_region_name.return_value = 'RegionOne'

        mock_keypair = mock.MagicMock()
        mock_keypair.public_key = 'ssh-rsa AAAAB3Nz'
        self.mock_nova = mock.MagicMock()
        self.mock_nova.keypairs.get.return_value = mock_keypair
        self.mock_osc.nova.return_value = self.mock_nova

        self.mock_keystone = mock.MagicMock()
        self.mock_keystone.trustee_domain_id = 'trustee_domain_id'
        self.mock_osc.keystone.return_value = self.mock_keystone
        self.mock_osc_class.return_value = self.mock_osc
        self.mock_osc.url_for.return_value = 'http://192.168.10.10:5000/v3'

    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    @patch('magnum.objects.NodeGroup.list')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_extract_template_definition_all_values(
            self,
            mock_driver,
            mock_objects_nodegroup_list,
            mock_objects_cluster_template_get_by_uuid):
        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_objects_cluster_template_get_by_uuid.return_value = \
            cluster_template
        cluster = objects.Cluster(self.context, **self.cluster_dict)
        worker_ng = objects.NodeGroup(self.context, **self.worker_ng_dict)
        master_ng = objects.NodeGroup(self.context, **self.master_ng_dict)
        mock_objects_nodegroup_list.return_value = [master_ng, worker_ng]
        mock_driver.return_value = mesos_dr.Driver()

        (template_path,
         definition,
         env_files) = mock_driver()._extract_template_definition(self.context,
                                                                 cluster)

        expected = {
            'ssh_key_name': 'keypair_id',
            'ssh_public_key': 'ssh-rsa AAAAB3Nz',
            'external_network': 'external_network_id',
            'fixed_network': 'fixed_network',
            'fixed_subnet': 'fixed_subnet',
            'dns_nameserver': 'dns_nameserver',
            'master_image': 'image_id',
            'slave_image': 'image_id',
            'master_flavor': 'master_flavor_id',
            'slave_flavor': 'flavor_id',
            'number_of_slaves': 1,
            'number_of_masters': 1,
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'cluster_name': 'cluster1',
            'trustee_domain_id': self.mock_keystone.trustee_domain_id,
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': '',
            'volume_driver': 'volume_driver',
            'auth_url': 'http://192.168.10.10:5000/v3',
            'region_name': self.mock_osc.cinder_region_name.return_value,
            'username': 'mesos_user',
            'tenant_name': 'admin',
            'domain_name': 'domainname',
            'rexray_preempt': 'False',
            'mesos_slave_executor_env_variables': '{}',
            'mesos_slave_isolation': 'docker/runtime,filesystem/linux',
            'mesos_slave_work_dir': '/tmp/mesos/slave',
            'mesos_slave_image_providers': 'docker',
            'verify_ca': True,
            'openstack_ca': '',
            'nodes_affinity_policy': 'soft-anti-affinity',
        }
        self.assertEqual(expected, definition)
        self.assertEqual(
            ['../../common/templates/environments/no_private_network.yaml',
             '../../common/templates/environments/no_master_lb.yaml'],
            env_files)

    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    @patch('magnum.objects.NodeGroup.list')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_extract_template_definition_only_required(
            self,
            mock_driver,
            mock_objects_nodegroup_list,
            mock_objects_cluster_template_get_by_uuid):
        not_required = ['image_id', 'master_flavor_id', 'flavor_id',
                        'dns_nameserver', 'fixed_network', 'http_proxy',
                        'https_proxy', 'no_proxy', 'volume_driver',
                        'fixed_subnet']
        for key in not_required:
            self.cluster_template_dict[key] = None

        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_objects_cluster_template_get_by_uuid.return_value = \
            cluster_template
        cluster = objects.Cluster(self.context, **self.cluster_dict)
        del self.worker_ng_dict['image_id']
        del self.master_ng_dict['image_id']
        worker_ng = objects.NodeGroup(self.context, **self.worker_ng_dict)
        master_ng = objects.NodeGroup(self.context, **self.master_ng_dict)
        mock_objects_nodegroup_list.return_value = [master_ng, worker_ng]
        mock_driver.return_value = mesos_dr.Driver()

        (template_path,
         definition,
         env_files) = mock_driver()._extract_template_definition(self.context,
                                                                 cluster)

        expected = {
            'ssh_key_name': 'keypair_id',
            'ssh_public_key': 'ssh-rsa AAAAB3Nz',
            'external_network': 'external_network_id',
            'number_of_slaves': 1,
            'number_of_masters': 1,
            'cluster_name': 'cluster1',
            'trustee_domain_id': self.mock_keystone.trustee_domain_id,
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': '',
            'auth_url': 'http://192.168.10.10:5000/v3',
            'region_name': self.mock_osc.cinder_region_name.return_value,
            'username': 'mesos_user',
            'tenant_name': 'admin',
            'domain_name': 'domainname',
            'rexray_preempt': 'False',
            'mesos_slave_isolation': 'docker/runtime,filesystem/linux',
            'mesos_slave_executor_env_variables': '{}',
            'mesos_slave_work_dir': '/tmp/mesos/slave',
            'mesos_slave_image_providers': 'docker',
            'master_flavor': 'master_flavor_id',
            'verify_ca': True,
            'slave_flavor': 'flavor_id',
            'openstack_ca': '',
            'nodes_affinity_policy': 'soft-anti-affinity',
        }
        self.assertEqual(expected, definition)
        self.assertEqual(
            ['../../common/templates/environments/with_private_network.yaml',
             '../../common/templates/environments/no_master_lb.yaml'],
            env_files)

    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    @patch('magnum.objects.NodeGroup.list')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    @patch('magnum.common.keystone.KeystoneClientV3')
    def test_extract_template_definition_with_lb_neutron(
            self,
            mock_kc,
            mock_driver,
            mock_objects_nodegroup_list,
            mock_objects_cluster_template_get_by_uuid):
        self.cluster_template_dict['master_lb_enabled'] = True
        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_objects_cluster_template_get_by_uuid.return_value = \
            cluster_template
        self.cluster_dict["master_lb_enabled"] = True
        cluster = objects.Cluster(self.context, **self.cluster_dict)
        worker_ng = objects.NodeGroup(self.context, **self.worker_ng_dict)
        master_ng = objects.NodeGroup(self.context, **self.master_ng_dict)
        mock_objects_nodegroup_list.return_value = [master_ng, worker_ng]
        mock_driver.return_value = mesos_dr.Driver()

        mock_kc.return_value.client.services.list.return_value = []

        (template_path,
         definition,
         env_files) = mock_driver()._extract_template_definition(self.context,
                                                                 cluster)

        expected = {
            'ssh_key_name': 'keypair_id',
            'ssh_public_key': 'ssh-rsa AAAAB3Nz',
            'external_network': 'external_network_id',
            'fixed_network': 'fixed_network',
            'fixed_subnet': 'fixed_subnet',
            'dns_nameserver': 'dns_nameserver',
            'master_image': 'image_id',
            'slave_image': 'image_id',
            'master_flavor': 'master_flavor_id',
            'slave_flavor': 'flavor_id',
            'number_of_slaves': 1,
            'number_of_masters': 1,
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'cluster_name': 'cluster1',
            'trustee_domain_id': self.mock_keystone.trustee_domain_id,
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': '',
            'volume_driver': 'volume_driver',
            'auth_url': 'http://192.168.10.10:5000/v3',
            'region_name': self.mock_osc.cinder_region_name.return_value,
            'username': 'mesos_user',
            'tenant_name': 'admin',
            'domain_name': 'domainname',
            'rexray_preempt': 'False',
            'mesos_slave_executor_env_variables': '{}',
            'mesos_slave_isolation': 'docker/runtime,filesystem/linux',
            'mesos_slave_work_dir': '/tmp/mesos/slave',
            'mesos_slave_image_providers': 'docker',
            'verify_ca': True,
            'openstack_ca': '',
            'nodes_affinity_policy': 'soft-anti-affinity',
        }
        self.assertEqual(expected, definition)
        self.assertEqual(
            ['../../common/templates/environments/no_private_network.yaml',
             '../../common/templates/environments/with_master_lb.yaml'],
            env_files)

    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    @patch('magnum.objects.NodeGroup.list')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    @patch('magnum.common.keystone.KeystoneClientV3')
    def test_extract_template_definition_with_lb_octavia(
            self,
            mock_kc,
            mock_driver,
            mock_objects_nodegroup_list,
            mock_objects_cluster_template_get_by_uuid):
        self.cluster_template_dict['master_lb_enabled'] = True
        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_objects_cluster_template_get_by_uuid.return_value = \
            cluster_template
        self.cluster_dict["master_lb_enabled"] = True
        cluster = objects.Cluster(self.context, **self.cluster_dict)
        worker_ng = objects.NodeGroup(self.context, **self.worker_ng_dict)
        master_ng = objects.NodeGroup(self.context, **self.master_ng_dict)
        mock_objects_nodegroup_list.return_value = [master_ng, worker_ng]
        mock_driver.return_value = mesos_dr.Driver()

        class Service(object):
            def __init__(self):
                self.enabled = True

        mock_kc.return_value.client.services.list.return_value = [Service()]

        (template_path,
         definition,
         env_files) = mock_driver()._extract_template_definition(self.context,
                                                                 cluster)

        expected = {
            'ssh_key_name': 'keypair_id',
            'ssh_public_key': 'ssh-rsa AAAAB3Nz',
            'external_network': 'external_network_id',
            'fixed_network': 'fixed_network',
            'fixed_subnet': 'fixed_subnet',
            'dns_nameserver': 'dns_nameserver',
            'master_image': 'image_id',
            'slave_image': 'image_id',
            'master_flavor': 'master_flavor_id',
            'slave_flavor': 'flavor_id',
            'number_of_slaves': 1,
            'number_of_masters': 1,
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'cluster_name': 'cluster1',
            'trustee_domain_id': self.mock_keystone.trustee_domain_id,
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': '',
            'volume_driver': 'volume_driver',
            'auth_url': 'http://192.168.10.10:5000/v3',
            'region_name': self.mock_osc.cinder_region_name.return_value,
            'username': 'mesos_user',
            'tenant_name': 'admin',
            'domain_name': 'domainname',
            'rexray_preempt': 'False',
            'mesos_slave_executor_env_variables': '{}',
            'mesos_slave_isolation': 'docker/runtime,filesystem/linux',
            'mesos_slave_work_dir': '/tmp/mesos/slave',
            'mesos_slave_image_providers': 'docker',
            'verify_ca': True,
            'openstack_ca': '',
            'nodes_affinity_policy': 'soft-anti-affinity',
        }
        self.assertEqual(expected, definition)
        self.assertEqual(
            ['../../common/templates/environments/no_private_network.yaml',
             '../../common/templates/environments/with_master_lb_octavia.yaml'
             ],
            env_files)

    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    @patch('magnum.objects.NodeGroup.list')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    @patch('magnum.common.keystone.KeystoneClientV3')
    def test_extract_template_definition_multi_master(
            self,
            mock_kc,
            mock_driver,
            mock_objects_nodegroup_list,
            mock_objects_cluster_template_get_by_uuid):
        self.cluster_template_dict['master_lb_enabled'] = True
        self.master_ng_dict['node_count'] = 2
        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_objects_cluster_template_get_by_uuid.return_value = \
            cluster_template
        self.cluster_dict["master_lb_enabled"] = True
        cluster = objects.Cluster(self.context, **self.cluster_dict)
        worker_ng = objects.NodeGroup(self.context, **self.worker_ng_dict)
        master_ng = objects.NodeGroup(self.context, **self.master_ng_dict)
        mock_objects_nodegroup_list.return_value = [master_ng, worker_ng]
        mock_driver.return_value = mesos_dr.Driver()

        mock_kc.return_value.client.services.list.return_value = []

        (template_path,
         definition,
         env_files) = mock_driver()._extract_template_definition(self.context,
                                                                 cluster)

        expected = {
            'ssh_key_name': 'keypair_id',
            'ssh_public_key': 'ssh-rsa AAAAB3Nz',
            'external_network': 'external_network_id',
            'fixed_network': 'fixed_network',
            'fixed_subnet': 'fixed_subnet',
            'dns_nameserver': 'dns_nameserver',
            'master_image': 'image_id',
            'slave_image': 'image_id',
            'master_flavor': 'master_flavor_id',
            'slave_flavor': 'flavor_id',
            'number_of_slaves': 1,
            'number_of_masters': 2,
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'cluster_name': 'cluster1',
            'trustee_domain_id': self.mock_keystone.trustee_domain_id,
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': '',
            'volume_driver': 'volume_driver',
            'auth_url': 'http://192.168.10.10:5000/v3',
            'region_name': self.mock_osc.cinder_region_name.return_value,
            'username': 'mesos_user',
            'tenant_name': 'admin',
            'domain_name': 'domainname',
            'rexray_preempt': 'False',
            'mesos_slave_executor_env_variables': '{}',
            'mesos_slave_isolation': 'docker/runtime,filesystem/linux',
            'mesos_slave_work_dir': '/tmp/mesos/slave',
            'mesos_slave_image_providers': 'docker',
            'verify_ca': True,
            'openstack_ca': '',
            'nodes_affinity_policy': 'soft-anti-affinity',
        }
        self.assertEqual(expected, definition)
        self.assertEqual(
            ['../../common/templates/environments/no_private_network.yaml',
             '../../common/templates/environments/with_master_lb.yaml'],
            env_files)

    @patch('magnum.conductor.utils.retrieve_cluster_template')
    @patch('magnum.conf.CONF')
    @patch('magnum.common.clients.OpenStackClients')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def setup_poll_test(self, mock_driver, mock_openstack_client,
                        mock_conf, mock_retrieve_cluster_template):
        mock_conf.cluster_heat.max_attempts = 10

        worker_ng = mock.MagicMock(
            uuid='5d12f6fd-a196-4bf0-ae4c-1f639a523a53',
            role='worker',
            node_count=1,
        )
        master_ng = mock.MagicMock(
            uuid='5d12f6fd-a196-4bf0-ae4c-1f639a523a54',
            role='master',
            node_count=1,
        )
        cluster = mock.MagicMock(nodegroups=[worker_ng, master_ng],
                                 default_ng_worker=worker_ng,
                                 default_ng_master=master_ng)
        mock_heat_stack = mock.MagicMock()
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client.heat.return_value = mock_heat_client
        mock_driver.return_value = mesos_dr.Driver()
        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_retrieve_cluster_template.return_value = cluster_template
        poller = heat_driver.HeatPoller(mock_openstack_client,
                                        mock.MagicMock(), cluster,
                                        mesos_dr.Driver())
        poller.template_def.add_nodegroup_params(cluster)
        poller.get_version_info = mock.MagicMock()
        return (mock_heat_stack, cluster, poller)

    def test_poll_node_count(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.parameters = {
            'number_of_slaves': 1,
            'number_of_masters': 1
        }
        mock_heat_stack.stack_status = cluster_status.CREATE_IN_PROGRESS
        poller.poll_and_check()

        self.assertEqual(1, cluster.default_ng_worker.node_count)

    def test_poll_node_count_by_update(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.parameters = {
            'number_of_slaves': 2,
            'number_of_masters': 1
        }
        mock_heat_stack.stack_status = cluster_status.UPDATE_COMPLETE
        poller.poll_and_check()

        self.assertEqual(2, cluster.default_ng_worker.node_count)
