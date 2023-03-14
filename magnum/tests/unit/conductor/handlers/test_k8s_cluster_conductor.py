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

import magnum.conf
from magnum.drivers.k8s_coreos_v1 import driver as k8s_coreos_dr
from magnum.drivers.k8s_fedora_atomic_v1 import driver as k8s_dr
from magnum import objects
from magnum.tests import base

CONF = magnum.conf.CONF


class TestClusterConductorWithK8s(base.TestCase):
    def setUp(self):
        super(TestClusterConductorWithK8s, self).setUp()
        self.keystone_auth_default_policy = ('[{"match": [{"type": "role", '
                                             '"values": ["member"]}, {"type": '
                                             '"project", "values": '
                                             '["project_id"]}], "resource": '
                                             '{"namespace": "default", '
                                             '"resources": ["pods", '
                                             '"services", "deployments", '
                                             '"pvc"], "verbs": ["list"], '
                                             '"version": "*"}}]')
        self.cluster_template_dict = {
            'image_id': 'image_id',
            'flavor_id': 'flavor_id',
            'master_flavor_id': 'master_flavor_id',
            'keypair_id': 'keypair_id',
            'dns_nameserver': 'dns_nameserver',
            'external_network_id': 'e2a6c8b0-a3c2-42a3-b3f4-01400a30896e',
            'fixed_network': 'fixed_network',
            'fixed_subnet': 'c2a6c8b0-a3c2-42a3-b3f4-01400a30896f',
            'network_driver': 'network_driver',
            'volume_driver': 'volume_driver',
            'docker_volume_size': 20,
            'docker_storage_driver': 'devicemapper',
            'cluster_distro': 'fedora-atomic',
            'coe': 'kubernetes',
            'token': None,
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'labels': {'flannel_network_cidr': '10.101.0.0/16',
                       'flannel_network_subnetlen': '26',
                       'flannel_backend': 'vxlan',
                       'system_pods_initial_delay': '15',
                       'system_pods_timeout': '1',
                       'admission_control_list': 'fake_list',
                       'prometheus_monitoring': 'False',
                       'grafana_admin_passwd': 'fake_pwd',
                       'kube_dashboard_enabled': 'True',
                       'influx_grafana_dashboard_enabled': 'True',
                       'docker_volume_type': 'lvmdriver-1',
                       'etcd_volume_size': 0,
                       'availability_zone': 'az_1',
                       'service_cluster_ip_range': '10.254.0.0/16'},
            'tls_disabled': False,
            'server_type': 'vm',
            'registry_enabled': False,
            'insecure_registry': '10.0.0.1:5000',
            'master_lb_enabled': False,
            'floating_ip_enabled': False,
        }
        self.cluster_dict = {
            'uuid': '5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            'cluster_template_id': 'xx-xx-xx-xx',
            'keypair': 'keypair_id',
            'name': 'cluster1',
            'stack_id': 'xx-xx-xx-xx',
            'api_address': '172.17.2.3',
            'discovery_url': 'https://discovery.etcd.io/test',
            'docker_volume_size': 20,
            'flavor_id': 'flavor_id',
            'ca_cert_ref': 'http://barbican/v1/containers/xx-xx-xx-xx',
            'magnum_cert_ref': 'http://barbican/v1/containers/xx-xx-xx-xx',
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': 'bd11efc5-d4e2-4dac-bbce-25e348ddf7de',
            'coe_version': 'fake-version',
            'labels': {'flannel_network_cidr': '10.101.0.0/16',
                       'flannel_network_subnetlen': '26',
                       'flannel_backend': 'vxlan',
                       'system_pods_initial_delay': '15',
                       'system_pods_timeout': '1',
                       'admission_control_list': 'fake_list',
                       'prometheus_monitoring': 'False',
                       'grafana_admin_passwd': 'fake_pwd',
                       'kube_dashboard_enabled': 'True',
                       'docker_volume_type': 'lvmdriver-1',
                       'availability_zone': 'az_1',
                       'cert_manager_api': 'False',
                       'ingress_controller': 'i-controller',
                       'ingress_controller_role': 'i-controller-role',
                       'kubelet_options': '--kubelet',
                       'kubeapi_options': '--kubeapi',
                       'kubecontroller_options': '--kubecontroller',
                       'kubescheduler_options': '--kubescheduler',
                       'kubeproxy_options': '--kubeproxy',
                       'influx_grafana_dashboard_enabled': 'True',
                       'service_cluster_ip_range': '10.254.0.0/16',
                       'boot_volume_size': '60'},
            'master_flavor_id': 'master_flavor_id',
            'project_id': 'project_id',
            'keystone_auth_default_policy': self.keystone_auth_default_policy,
            'fixed_network': 'fixed_network',
            'fixed_subnet': 'c2a6c8b0-a3c2-42a3-b3f4-01400a30896f',
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
        self.context.user_name = 'fake_user'
        self.context.project_id = 'fake_tenant'
        osc_patcher = mock.patch('magnum.common.clients.OpenStackClients')
        self.mock_osc_class = osc_patcher.start()
        self.addCleanup(osc_patcher.stop)
        self.mock_osc = mock.MagicMock()

        mock_keypair = mock.MagicMock()
        mock_keypair.public_key = 'ssh-rsa AAAAB3Nz'
        self.mock_nova = mock.MagicMock()
        self.mock_nova.keypairs.get.return_value = mock_keypair
        self.mock_osc.nova.return_value = self.mock_nova

        self.mock_osc.url_for.return_value = 'http://192.168.10.10:5000/v3'
        self.mock_osc.magnum_url.return_value = 'http://127.0.0.1:9511/v1'
        self.mock_osc.cinder_region_name.return_value = 'RegionOne'
        self.mock_keystone = mock.MagicMock()
        self.mock_keystone.trustee_domain_id = 'trustee_domain_id'
        self.mock_osc.keystone.return_value = self.mock_keystone
        self.mock_osc_class.return_value = self.mock_osc

        octavia_patcher = mock.patch(
            'magnum.common.keystone.is_octavia_enabled'
        )
        self.mock_enable_octavia = octavia_patcher.start()
        self.mock_enable_octavia.return_value = False
        self.addCleanup(octavia_patcher.stop)
        CONF.set_override('default_boot_volume_type',
                          'lvmdriver-1', group='cinder')
        CONF.set_override('default_etcd_volume_type',
                          'lvmdriver-1', group='cinder')
        self.fixed_subnet_cidr = '20.200.0.0/16'

    @patch('magnum.common.neutron.get_subnet')
    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    @patch('magnum.objects.NodeGroup.list')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    @patch('magnum.conductor.handlers.common.cert_manager'
           '.sign_node_certificate')
    @patch('magnum.common.x509.operations.generate_csr_and_key')
    def test_extract_template_definition(
            self,
            mock_generate_csr_and_key,
            mock_sign_node_certificate,
            mock_driver,
            mock_objects_nodegroup_list,
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            mock_get_subnet):
        self._test_extract_template_definition(
            mock_generate_csr_and_key, mock_sign_node_certificate,
            mock_driver, mock_objects_cluster_template_get_by_uuid, mock_get,
            mock_objects_nodegroup_list, mock_get_subnet)

    def _test_extract_template_definition(
            self,
            mock_generate_csr_and_key,
            mock_sign_node_certificate,
            mock_driver,
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            mock_objects_nodegroup_list,
            mock_get_subnet,
            missing_attr=None):
        if missing_attr in self.cluster_template_dict:
            self.cluster_template_dict[missing_attr] = None
        elif missing_attr in self.cluster_dict:
            self.cluster_dict[missing_attr] = None
        if missing_attr == 'image_id':
            del self.worker_ng_dict['image_id']
            del self.master_ng_dict['image_id']
        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_generate_csr_and_key.return_value = {'csr': 'csr',
                                                  'private_key': 'private_key',
                                                  'public_key': 'public_key'}
        mock_sign_node_certificate.return_value = 'signed_cert'
        mock_objects_cluster_template_get_by_uuid.return_value = \
            cluster_template
        expected_result = str('{"action":"get","node":{"key":"test","value":'
                              '"1","modifiedIndex":10,"createdIndex":10}}')
        mock_resp = mock.MagicMock()
        mock_resp.text = expected_result
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        cluster = objects.Cluster(self.context, **self.cluster_dict)
        worker_ng = objects.NodeGroup(self.context, **self.worker_ng_dict)
        master_ng = objects.NodeGroup(self.context, **self.master_ng_dict)
        mock_objects_nodegroup_list.return_value = [master_ng, worker_ng]
        mock_driver.return_value = k8s_dr.Driver()

        mock_get_subnet.return_value = self.fixed_subnet_cidr

        (template_path,
         definition,
         env_files) = mock_driver()._extract_template_definition(self.context,
                                                                 cluster)

        mapping = {
            'dns_nameserver': 'dns_nameserver',
            'flavor_id': 'minion_flavor',
            'docker_volume_size': 'docker_volume_size',
            'docker_storage_driver': 'docker_storage_driver',
            'network_driver': 'network_driver',
            'volume_driver': 'volume_driver',
            'master_flavor_id': 'master_flavor',
            'apiserver_port': '',
            'node_count': 'number_of_minions',
            'master_count': 'number_of_masters',
            'discovery_url': 'discovery_url',
            'labels': {'flannel_network_cidr': '10.101.0.0/16',
                       'flannel_network_subnetlen': '26',
                       'flannel_backend': 'vxlan',
                       'system_pods_initial_delay': '15',
                       'system_pods_timeout': '1',
                       'admission_control_list': 'fake_list',
                       'prometheus_monitoring': 'False',
                       'grafana_admin_passwd': 'fake_pwd',
                       'kube_dashboard_enabled': 'True',
                       'influx_grafana_dashboard_enabled': 'True',
                       'docker_volume_type': 'lvmdriver-1',
                       'boot_volume_type': 'lvmdriver-1',
                       'etcd_volume_size': None,
                       'etcd_volume_type': '',
                       'availability_zone': 'az_1',
                       'cert_manager_api': 'False',
                       'ingress_controller': 'i-controller',
                       'ingress_controller_role': 'i-controller-role',
                       'kubelet_options': '--kubelet',
                       'kubeapi_options': '--kubeapi',
                       'kubecontroller_options': '--kubecontroller',
                       'kubescheduler_options': '--kubescheduler',
                       'kubeproxy_options': '--kubeproxy',
                       'service_cluster_ip_range': '10.254.0.0/16',
                       },
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'cluster_uuid': self.cluster_dict['uuid'],
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'tls_disabled': False,
            'insecure_registry': '10.0.0.1:5000',
            'image_id': ['master_image', 'minion_image']
        }
        expected = {
            'cloud_provider_enabled': 'false',
            'ssh_key_name': 'keypair_id',
            'external_network': 'e2a6c8b0-a3c2-42a3-b3f4-01400a30896e',
            'fixed_network': 'fixed_network',
            'fixed_network_name': 'fixed_network',
            'fixed_subnet': 'c2a6c8b0-a3c2-42a3-b3f4-01400a30896f',
            'network_driver': 'network_driver',
            'volume_driver': 'volume_driver',
            'dns_nameserver': 'dns_nameserver',
            'master_image': 'image_id',
            'minion_image': 'image_id',
            'minion_flavor': 'flavor_id',
            'master_flavor': 'master_flavor_id',
            'number_of_minions': 1,
            'number_of_masters': 1,
            'docker_volume_size': 20,
            'docker_volume_type': 'lvmdriver-1',
            'docker_storage_driver': 'devicemapper',
            'discovery_url': 'https://discovery.etcd.io/test',
            'etcd_volume_size': None,
            'etcd_volume_type': '',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_backend': 'vxlan',
            'system_pods_initial_delay': '15',
            'system_pods_timeout': '1',
            'admission_control_list': 'fake_list',
            'prometheus_monitoring': 'False',
            'grafana_admin_passwd': 'fake_pwd',
            'kube_dashboard_enabled': 'True',
            'influx_grafana_dashboard_enabled': 'True',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy,20.200.0.0/16',
            'username': 'fake_user',
            'cluster_uuid': self.cluster_dict['uuid'],
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'region_name': self.mock_osc.cinder_region_name.return_value,
            'tls_disabled': False,
            'registry_enabled': False,
            'trustee_domain_id': self.mock_keystone.trustee_domain_id,
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': '',
            'auth_url': 'http://192.168.10.10:5000/v3',
            'insecure_registry_url': '10.0.0.1:5000',
            'kube_version': 'fake-version',
            'verify_ca': True,
            'openstack_ca': '',
            'ssh_public_key': 'ssh-rsa AAAAB3Nz',
            "nodes_affinity_policy": "soft-anti-affinity",
            'availability_zone': 'az_1',
            'cert_manager_api': 'False',
            'ingress_controller': 'i-controller',
            'ingress_controller_role': 'i-controller-role',
            'octavia_ingress_controller_tag': None,
            'kubelet_options': '--kubelet',
            'kubeapi_options': '--kubeapi',
            'kubecontroller_options': '--kubecontroller',
            'kubescheduler_options': '--kubescheduler',
            'kubeproxy_options': '--kubeproxy',
            'octavia_enabled': False,
            'kube_service_account_key': 'public_key',
            'kube_service_account_private_key': 'private_key',
            'portal_network_cidr': '10.254.0.0/16',
            'project_id': 'project_id',
            'max_node_count': 2,
            'keystone_auth_default_policy': self.keystone_auth_default_policy,
            'boot_volume_size': '60',
            'boot_volume_type': 'lvmdriver-1',
            'master_role': 'master',
            'worker_role': 'worker',
            'master_nodegroup_name': 'master_ng',
            'worker_nodegroup_name': 'worker_ng',
            'post_install_manifest_url': '',
            'master_lb_allowed_cidrs': None,
            'fixed_subnet_cidr': self.fixed_subnet_cidr,
            'octavia_provider': None,
            'octavia_lb_algorithm': None,
            'octavia_lb_healthcheck': None,
        }

        if missing_attr is not None:
            attrs = mapping[missing_attr]
            if not isinstance(attrs, list):
                attrs = [attrs]
            for attr in attrs:
                expected.pop(attr, None)

        if missing_attr == 'node_count':
            expected['max_node_count'] = None

        self.assertEqual(expected, definition)
        self.assertEqual(
            ['../../common/templates/environments/no_private_network.yaml',
             '../../common/templates/environments/no_etcd_volume.yaml',
             '../../common/templates/environments/with_volume.yaml',
             '../../common/templates/environments/no_master_lb.yaml',
             '../../common/templates/environments/disable_floating_ip.yaml',
             '../../common/templates/environments/disable_lb_floating_ip.yaml',
             ],
            env_files)

    @patch('magnum.common.neutron.get_subnet')
    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    @patch('magnum.objects.NodeGroup.list')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    @patch('magnum.conductor.handlers.common.cert_manager'
           '.sign_node_certificate')
    @patch('magnum.common.x509.operations.generate_csr_and_key')
    def test_extract_template_definition_with_registry(
            self,
            mock_generate_csr_and_key,
            mock_sign_node_certificate,
            mock_driver,
            mock_objects_nodegroup_list,
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            mock_get_subnet):
        self.cluster_template_dict['registry_enabled'] = True
        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_generate_csr_and_key.return_value = {'csr': 'csr',
                                                  'private_key': 'private_key',
                                                  'public_key': 'public_key'}
        mock_sign_node_certificate.return_value = 'signed_cert'
        mock_objects_cluster_template_get_by_uuid.return_value = \
            cluster_template
        expected_result = str('{"action":"get","node":{"key":"test","value":'
                              '"1","modifiedIndex":10,"createdIndex":10}}')
        mock_resp = mock.MagicMock()
        mock_resp.text = expected_result
        mock_get.return_value = mock_resp
        cluster = objects.Cluster(self.context, **self.cluster_dict)
        worker_ng = objects.NodeGroup(self.context, **self.worker_ng_dict)
        master_ng = objects.NodeGroup(self.context, **self.master_ng_dict)
        mock_objects_nodegroup_list.return_value = [master_ng, worker_ng]
        mock_driver.return_value = k8s_dr.Driver()
        mock_get_subnet.return_value = self.fixed_subnet_cidr

        CONF.set_override('swift_region',
                          'RegionOne',
                          group='docker_registry')

        CONF.set_override('cluster_user_trust',
                          True,
                          group='trust')

        (template_path,
         definition,
         env_files) = mock_driver()._extract_template_definition(self.context,
                                                                 cluster)

        expected = {
            'auth_url': 'http://192.168.10.10:5000/v3',
            'cloud_provider_enabled': 'true',
            'cluster_uuid': '5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            'discovery_url': 'https://discovery.etcd.io/test',
            'dns_nameserver': 'dns_nameserver',
            'docker_storage_driver': 'devicemapper',
            'docker_volume_size': 20,
            'docker_volume_type': 'lvmdriver-1',
            'etcd_volume_size': None,
            'etcd_volume_type': '',
            'external_network': 'e2a6c8b0-a3c2-42a3-b3f4-01400a30896e',
            'fixed_network': 'fixed_network',
            'fixed_network_name': 'fixed_network',
            'fixed_subnet': 'c2a6c8b0-a3c2-42a3-b3f4-01400a30896f',
            'flannel_backend': 'vxlan',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'system_pods_initial_delay': '15',
            'system_pods_timeout': '1',
            'admission_control_list': 'fake_list',
            'prometheus_monitoring': 'False',
            'grafana_admin_passwd': 'fake_pwd',
            'kube_dashboard_enabled': 'True',
            'influx_grafana_dashboard_enabled': 'True',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'magnum_url': 'http://127.0.0.1:9511/v1',
            'master_flavor': 'master_flavor_id',
            'minion_flavor': 'flavor_id',
            'network_driver': 'network_driver',
            'no_proxy': 'no_proxy,20.200.0.0/16',
            'number_of_masters': 1,
            'number_of_minions': 1,
            'region_name': 'RegionOne',
            'registry_container': 'docker_registry',
            'registry_enabled': True,
            'master_image': 'image_id',
            'minion_image': 'image_id',
            'ssh_key_name': 'keypair_id',
            'swift_region': 'RegionOne',
            'tls_disabled': False,
            'trust_id': 'bd11efc5-d4e2-4dac-bbce-25e348ddf7de',
            'trustee_domain_id': self.mock_keystone.trustee_domain_id,
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trustee_username': 'fake_trustee',
            'username': 'fake_user',
            'volume_driver': 'volume_driver',
            'insecure_registry_url': '10.0.0.1:5000',
            'kube_version': 'fake-version',
            'verify_ca': True,
            'openstack_ca': '',
            'ssh_public_key': 'ssh-rsa AAAAB3Nz',
            "nodes_affinity_policy": "soft-anti-affinity",
            'availability_zone': 'az_1',
            'cert_manager_api': 'False',
            'ingress_controller': 'i-controller',
            'ingress_controller_role': 'i-controller-role',
            'octavia_ingress_controller_tag': None,
            'kubelet_options': '--kubelet',
            'kubeapi_options': '--kubeapi',
            'kubecontroller_options': '--kubecontroller',
            'kubescheduler_options': '--kubescheduler',
            'kubeproxy_options': '--kubeproxy',
            'octavia_enabled': False,
            'kube_service_account_key': 'public_key',
            'kube_service_account_private_key': 'private_key',
            'portal_network_cidr': '10.254.0.0/16',
            'project_id': 'project_id',
            'max_node_count': 2,
            'keystone_auth_default_policy': self.keystone_auth_default_policy,
            'boot_volume_size': '60',
            'boot_volume_type': 'lvmdriver-1',
            'master_role': 'master',
            'worker_role': 'worker',
            'master_nodegroup_name': 'master_ng',
            'worker_nodegroup_name': 'worker_ng',
            'post_install_manifest_url': '',
            'master_lb_allowed_cidrs': None,
            'fixed_subnet_cidr': self.fixed_subnet_cidr,
            'octavia_provider': None,
            'octavia_lb_algorithm': None,
            'octavia_lb_healthcheck': None,
        }

        self.assertEqual(expected, definition)
        self.assertEqual(
            ['../../common/templates/environments/no_private_network.yaml',
             '../../common/templates/environments/no_etcd_volume.yaml',
             '../../common/templates/environments/with_volume.yaml',
             '../../common/templates/environments/no_master_lb.yaml',
             '../../common/templates/environments/disable_floating_ip.yaml',
             '../../common/templates/environments/disable_lb_floating_ip.yaml'
             ],
            env_files)

    @patch('magnum.common.neutron.get_subnet')
    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    @patch('magnum.objects.NodeGroup.list')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    @patch('magnum.conductor.handlers.common.cert_manager'
           '.sign_node_certificate')
    @patch('magnum.common.x509.operations.generate_csr_and_key')
    def test_extract_template_definition_only_required(
            self,
            mock_generate_csr_and_key,
            mock_sign_node_certificate,
            mock_driver,
            mock_objects_nodegroup_list,
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            mock_get_subnet):

        not_required = ['image_id', 'flavor_id', 'dns_nameserver',
                        'docker_volume_size', 'http_proxy',
                        'https_proxy', 'no_proxy', 'network_driver',
                        'master_flavor_id', 'docker_storage_driver',
                        'volume_driver', 'fixed_subnet']
        for key in not_required:
            self.cluster_template_dict[key] = None
        self.cluster_dict['discovery_url'] = 'https://discovery.etcd.io/test'

        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_generate_csr_and_key.return_value = {'csr': 'csr',
                                                  'private_key': 'private_key',
                                                  'public_key': 'public_key'}
        mock_sign_node_certificate.return_value = 'signed_cert'
        mock_objects_cluster_template_get_by_uuid.return_value = \
            cluster_template
        expected_result = str('{"action":"get","node":{"key":"test","value":'
                              '"1","modifiedIndex":10,"createdIndex":10}}')
        mock_resp = mock.MagicMock()
        mock_resp.text = expected_result
        mock_get.return_value = mock_resp
        mock_driver.return_value = k8s_dr.Driver()
        cluster = objects.Cluster(self.context, **self.cluster_dict)
        del self.worker_ng_dict['image_id']
        worker_ng = objects.NodeGroup(self.context, **self.worker_ng_dict)
        del self.master_ng_dict['image_id']
        master_ng = objects.NodeGroup(self.context, **self.master_ng_dict)
        master_ng.image_id = None
        mock_objects_nodegroup_list.return_value = [master_ng, worker_ng]
        mock_get_subnet.return_value = self.fixed_subnet_cidr

        (template_path,
         definition,
         env_files) = mock_driver()._extract_template_definition(self.context,
                                                                 cluster)

        expected = {
            'auth_url': 'http://192.168.10.10:5000/v3',
            'cloud_provider_enabled': 'false',
            'cluster_uuid': '5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            'discovery_url': 'https://discovery.etcd.io/test',
            'docker_volume_size': 20,
            'docker_volume_type': 'lvmdriver-1',
            'master_flavor': 'master_flavor_id',
            'minion_flavor': 'flavor_id',
            'fixed_network': 'fixed_network',
            'fixed_network_name': 'fixed_network',
            'fixed_subnet': 'c2a6c8b0-a3c2-42a3-b3f4-01400a30896f',
            'external_network': 'e2a6c8b0-a3c2-42a3-b3f4-01400a30896e',
            'flannel_backend': 'vxlan',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'system_pods_initial_delay': '15',
            'system_pods_timeout': '1',
            'admission_control_list': 'fake_list',
            'prometheus_monitoring': 'False',
            'grafana_admin_passwd': 'fake_pwd',
            'kube_dashboard_enabled': 'True',
            'influx_grafana_dashboard_enabled': 'True',
            'etcd_volume_size': None,
            'etcd_volume_type': '',
            'insecure_registry_url': '10.0.0.1:5000',
            'kube_version': 'fake-version',
            'magnum_url': 'http://127.0.0.1:9511/v1',
            'number_of_masters': 1,
            'number_of_minions': 1,
            'region_name': 'RegionOne',
            'registry_enabled': False,
            'ssh_key_name': 'keypair_id',
            'tls_disabled': False,
            'trust_id': '',
            'trustee_domain_id': 'trustee_domain_id',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trustee_username': 'fake_trustee',
            'username': 'fake_user',
            'verify_ca': True,
            'openstack_ca': '',
            'ssh_public_key': 'ssh-rsa AAAAB3Nz',
            "nodes_affinity_policy": "soft-anti-affinity",
            'availability_zone': 'az_1',
            'cert_manager_api': 'False',
            'ingress_controller': 'i-controller',
            'ingress_controller_role': 'i-controller-role',
            'octavia_ingress_controller_tag': None,
            'kubelet_options': '--kubelet',
            'kubeapi_options': '--kubeapi',
            'kubecontroller_options': '--kubecontroller',
            'kubescheduler_options': '--kubescheduler',
            'kubeproxy_options': '--kubeproxy',
            'octavia_enabled': False,
            'kube_service_account_key': 'public_key',
            'kube_service_account_private_key': 'private_key',
            'portal_network_cidr': '10.254.0.0/16',
            'project_id': 'project_id',
            'max_node_count': 2,
            'boot_volume_size': '60',
            'boot_volume_type': 'lvmdriver-1',
            'keystone_auth_default_policy': self.keystone_auth_default_policy,
            'master_role': 'master',
            'worker_role': 'worker',
            'master_nodegroup_name': 'master_ng',
            'worker_nodegroup_name': 'worker_ng',
            'post_install_manifest_url': '',
            'master_lb_allowed_cidrs': None,
            'fixed_subnet_cidr': self.fixed_subnet_cidr,
            'octavia_provider': None,
            'octavia_lb_algorithm': None,
            'octavia_lb_healthcheck': None,
        }
        self.assertEqual(expected, definition)
        self.assertEqual(
            ['../../common/templates/environments/no_private_network.yaml',
             '../../common/templates/environments/no_etcd_volume.yaml',
             '../../common/templates/environments/with_volume.yaml',
             '../../common/templates/environments/no_master_lb.yaml',
             '../../common/templates/environments/disable_floating_ip.yaml',
             '../../common/templates/environments/disable_lb_floating_ip.yaml'
             ],
            env_files)

    @patch('magnum.common.neutron.get_subnet')
    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    @patch('magnum.objects.NodeGroup.list')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_extract_template_definition_coreos_with_disovery(
            self,
            mock_driver,
            mock_objects_nodegroup_list,
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            mock_get_subnet):
        self.cluster_template_dict['cluster_distro'] = 'coreos'
        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_objects_cluster_template_get_by_uuid.return_value = \
            cluster_template
        expected_result = str('{"action":"get","node":{"key":"test","value":'
                              '"1","modifiedIndex":10,"createdIndex":10}}')
        mock_resp = mock.MagicMock()
        mock_resp.text = expected_result
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        cluster = objects.Cluster(self.context, **self.cluster_dict)
        worker_ng = objects.NodeGroup(self.context, **self.worker_ng_dict)
        master_ng = objects.NodeGroup(self.context, **self.master_ng_dict)
        mock_objects_nodegroup_list.return_value = [master_ng, worker_ng]
        mock_driver.return_value = k8s_coreos_dr.Driver()
        mock_get_subnet.return_value = self.fixed_subnet_cidr

        (template_path,
         definition,
         env_files) = mock_driver()._extract_template_definition(self.context,
                                                                 cluster)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'e2a6c8b0-a3c2-42a3-b3f4-01400a30896e',
            'fixed_network': 'fixed_network',
            'fixed_network_name': 'fixed_network',
            'fixed_subnet': 'c2a6c8b0-a3c2-42a3-b3f4-01400a30896f',
            'availability_zone': 'az_1',
            'nodes_affinity_policy': 'soft-anti-affinity',
            'dns_nameserver': 'dns_nameserver',
            'docker_storage_driver': 'devicemapper',
            'docker_volume_size': 20,
            'docker_volume_type': 'lvmdriver-1',
            'minion_flavor': 'flavor_id',
            'master_flavor': 'master_flavor_id',
            'master_image': 'image_id',
            'minion_image': 'image_id',
            'number_of_minions': 1,
            'number_of_masters': 1,
            'network_driver': 'network_driver',
            'volume_driver': 'volume_driver',
            'discovery_url': 'https://discovery.etcd.io/test',
            'etcd_volume_size': None,
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy,20.200.0.0/16',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_backend': 'vxlan',
            'system_pods_initial_delay': '15',
            'system_pods_timeout': '1',
            'admission_control_list': 'fake_list',
            'prometheus_monitoring': 'False',
            'region_name': 'RegionOne',
            'grafana_admin_passwd': 'fake_pwd',
            'kube_dashboard_enabled': 'True',
            'influx_grafana_dashboard_enabled': 'True',
            'tls_disabled': False,
            'registry_enabled': False,
            'trustee_domain_id': self.mock_keystone.trustee_domain_id,
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'username': 'fake_user',
            'trust_id': '',
            'auth_url': 'http://192.168.10.10:5000/v3',
            'cluster_uuid': self.cluster_dict['uuid'],
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'insecure_registry_url': '10.0.0.1:5000',
            'kube_version': 'fake-version',
            'verify_ca': True,
            'openstack_ca': '',
            'ssh_public_key': 'ssh-rsa AAAAB3Nz',
            'openstack_ca_coreos': '',
            'cert_manager_api': 'False',
            'ingress_controller': 'i-controller',
            'ingress_controller_role': 'i-controller-role',
            'octavia_ingress_controller_tag': None,
            'kubelet_options': '--kubelet',
            'kubeapi_options': '--kubeapi',
            'kubecontroller_options': '--kubecontroller',
            'kubescheduler_options': '--kubescheduler',
            'kubeproxy_options': '--kubeproxy',
            'octavia_enabled': False,
            'portal_network_cidr': '10.254.0.0/16',
            'master_role': 'master',
            'worker_role': 'worker',
            'master_nodegroup_name': 'master_ng',
            'worker_nodegroup_name': 'worker_ng',
            'master_lb_allowed_cidrs': None,
            'fixed_subnet_cidr': self.fixed_subnet_cidr,
            'octavia_provider': None,
            'octavia_lb_algorithm': None,
            'octavia_lb_healthcheck': None,
        }
        self.assertEqual(expected, definition)
        self.assertEqual(
            ['../../common/templates/environments/no_private_network.yaml',
             '../../common/templates/environments/no_etcd_volume.yaml',
             '../../common/templates/environments/with_volume.yaml',
             '../../common/templates/environments/no_master_lb.yaml',
             '../../common/templates/environments/disable_floating_ip.yaml',
             '../../common/templates/environments/disable_lb_floating_ip.yaml'
             ],
            env_files)

    @patch('magnum.common.neutron.get_subnet')
    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    @patch('magnum.objects.NodeGroup.list')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_extract_template_definition_coreos_no_discoveryurl(
            self,
            mock_driver,
            mock_objects_nodegroup_list,
            mock_objects_cluster_template_get_by_uuid,
            reqget,
            mock_get_subnet):
        self.cluster_template_dict['cluster_distro'] = 'coreos'
        self.cluster_dict['discovery_url'] = None
        mock_req = mock.MagicMock(text='http://tokentest/h1/h2/h3',
                                  status_code=200)
        reqget.return_value = mock_req
        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_objects_cluster_template_get_by_uuid.return_value = \
            cluster_template
        cluster = objects.Cluster(self.context, **self.cluster_dict)
        worker_ng = objects.NodeGroup(self.context, **self.worker_ng_dict)
        master_ng = objects.NodeGroup(self.context, **self.master_ng_dict)
        mock_objects_nodegroup_list.return_value = [master_ng, worker_ng]
        mock_driver.return_value = k8s_coreos_dr.Driver()
        mock_get_subnet.return_value = self.fixed_subnet_cidr

        (template_path,
         definition,
         env_files) = mock_driver()._extract_template_definition(self.context,
                                                                 cluster)

        expected = {
            'ssh_key_name': 'keypair_id',
            'availability_zone': 'az_1',
            'external_network': 'e2a6c8b0-a3c2-42a3-b3f4-01400a30896e',
            'fixed_network': 'fixed_network',
            'fixed_network_name': 'fixed_network',
            'fixed_subnet': 'c2a6c8b0-a3c2-42a3-b3f4-01400a30896f',
            'dns_nameserver': 'dns_nameserver',
            'docker_storage_driver': u'devicemapper',
            'docker_volume_size': 20,
            'docker_volume_type': u'lvmdriver-1',
            'master_image': 'image_id',
            'minion_image': 'image_id',
            'minion_flavor': 'flavor_id',
            'master_flavor': 'master_flavor_id',
            'number_of_minions': 1,
            'number_of_masters': 1,
            'network_driver': 'network_driver',
            'volume_driver': 'volume_driver',
            'discovery_url': 'http://tokentest/h1/h2/h3',
            'etcd_volume_size': None,
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy,20.200.0.0/16',
            'nodes_affinity_policy': 'soft-anti-affinity',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_backend': 'vxlan',
            'system_pods_initial_delay': '15',
            'system_pods_timeout': '1',
            'admission_control_list': 'fake_list',
            'prometheus_monitoring': 'False',
            'region_name': self.mock_osc.cinder_region_name.return_value,
            'grafana_admin_passwd': 'fake_pwd',
            'kube_dashboard_enabled': 'True',
            'influx_grafana_dashboard_enabled': 'True',
            'tls_disabled': False,
            'registry_enabled': False,
            'trustee_domain_id': self.mock_keystone.trustee_domain_id,
            'trustee_username': 'fake_trustee',
            'username': 'fake_user',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': '',
            'auth_url': 'http://192.168.10.10:5000/v3',
            'cluster_uuid': self.cluster_dict['uuid'],
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'insecure_registry_url': '10.0.0.1:5000',
            'kube_version': 'fake-version',
            'verify_ca': True,
            'openstack_ca': '',
            'ssh_public_key': 'ssh-rsa AAAAB3Nz',
            'openstack_ca_coreos': '',
            'cert_manager_api': 'False',
            'ingress_controller': 'i-controller',
            'ingress_controller_role': 'i-controller-role',
            'octavia_ingress_controller_tag': None,
            'kubelet_options': '--kubelet',
            'kubeapi_options': '--kubeapi',
            'kubecontroller_options': '--kubecontroller',
            'kubescheduler_options': '--kubescheduler',
            'kubeproxy_options': '--kubeproxy',
            'octavia_enabled': False,
            'portal_network_cidr': '10.254.0.0/16',
            'master_role': 'master',
            'worker_role': 'worker',
            'master_nodegroup_name': 'master_ng',
            'worker_nodegroup_name': 'worker_ng',
            'master_lb_allowed_cidrs': None,
            'fixed_subnet_cidr': self.fixed_subnet_cidr,
            'octavia_provider': None,
            'octavia_lb_algorithm': None,
            'octavia_lb_healthcheck': None,
        }
        self.assertEqual(expected, definition)
        self.assertEqual(
            ['../../common/templates/environments/no_private_network.yaml',
             '../../common/templates/environments/no_etcd_volume.yaml',
             '../../common/templates/environments/with_volume.yaml',
             '../../common/templates/environments/no_master_lb.yaml',
             '../../common/templates/environments/disable_floating_ip.yaml',
             '../../common/templates/environments/disable_lb_floating_ip.yaml'
             ],
            env_files)

    @patch('magnum.common.neutron.get_subnet')
    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    @patch('magnum.objects.NodeGroup.list')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    @patch('magnum.conductor.handlers.common.cert_manager'
           '.sign_node_certificate')
    @patch('magnum.common.x509.operations.generate_csr_and_key')
    def test_extract_template_definition_without_dns(
            self,
            mock_generate_csr_and_key,
            mock_sign_node_certificate,
            mock_driver,
            mock_objects_nodegroup_list,
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            mock_get_subnet):
        mock_driver.return_value = k8s_dr.Driver()
        self._test_extract_template_definition(
            mock_generate_csr_and_key,
            mock_sign_node_certificate,
            mock_driver,
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            mock_objects_nodegroup_list,
            mock_get_subnet,
            missing_attr='dns_nameserver')

    @patch('magnum.common.neutron.get_subnet')
    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    @patch('magnum.objects.NodeGroup.list')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    @patch('magnum.conductor.handlers.common.cert_manager'
           '.sign_node_certificate')
    @patch('magnum.common.x509.operations.generate_csr_and_key')
    def test_extract_template_definition_without_server_image(
            self,
            mock_generate_csr_and_key,
            mock_sign_node_certificate,
            mock_driver,
            mock_objects_nodegroup_list,
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            mock_get_subnet):
        mock_driver.return_value = k8s_dr.Driver()
        self._test_extract_template_definition(
            mock_generate_csr_and_key,
            mock_sign_node_certificate,
            mock_driver,
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            mock_objects_nodegroup_list,
            mock_get_subnet,
            missing_attr='image_id')

    @patch('magnum.common.neutron.get_subnet')
    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    @patch('magnum.objects.NodeGroup.list')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    @patch('magnum.conductor.handlers.common.cert_manager'
           '.sign_node_certificate')
    @patch('magnum.common.x509.operations.generate_csr_and_key')
    def test_extract_template_definition_without_docker_storage_driver(
            self,
            mock_generate_csr_and_key,
            mock_sign_node_certificate,
            mock_driver,
            mock_objects_nodegroup_list,
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            mock_get_subnet):
        mock_driver.return_value = k8s_dr.Driver()
        self._test_extract_template_definition(
            mock_generate_csr_and_key,
            mock_sign_node_certificate,
            mock_driver,
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            mock_objects_nodegroup_list,
            mock_get_subnet,
            missing_attr='docker_storage_driver')

    @patch('magnum.common.neutron.get_subnet')
    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    @patch('magnum.objects.NodeGroup.list')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    @patch('magnum.conductor.handlers.common.cert_manager'
           '.sign_node_certificate')
    @patch('magnum.common.x509.operations.generate_csr_and_key')
    def test_extract_template_definition_without_apiserver_port(
            self,
            mock_generate_csr_and_key,
            mock_sign_node_certificate,
            mock_driver,
            mock_objects_nodegroup_list,
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            mock_get_subnet):
        mock_driver.return_value = k8s_dr.Driver()
        self._test_extract_template_definition(
            mock_generate_csr_and_key,
            mock_sign_node_certificate,
            mock_driver,
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            mock_objects_nodegroup_list,
            mock_get_subnet,
            missing_attr='apiserver_port')

    @patch('magnum.common.neutron.get_subnet')
    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    @patch('magnum.objects.NodeGroup.list')
    @patch('magnum.drivers.common.driver.Driver.get_driver')
    @patch('magnum.conductor.handlers.common.cert_manager'
           '.sign_node_certificate')
    @patch('magnum.common.x509.operations.generate_csr_and_key')
    def test_extract_template_definition_without_discovery_url(
            self,
            mock_generate_csr_and_key,
            mock_sign_node_certificate,
            mock_driver,
            mock_objects_nodegroup_list,
            mock_objects_cluster_template_get_by_uuid,
            reqget,
            mock_get_subnet):
        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_generate_csr_and_key.return_value = {'csr': 'csr',
                                                  'private_key': 'private_key',
                                                  'public_key': 'public_key'}
        mock_sign_node_certificate.return_value = 'signed_cert'
        mock_objects_cluster_template_get_by_uuid.return_value = \
            cluster_template
        cluster_dict = self.cluster_dict
        cluster_dict['discovery_url'] = None
        cluster = objects.Cluster(self.context, **cluster_dict)
        worker_ng = objects.NodeGroup(self.context, **self.worker_ng_dict)
        master_ng = objects.NodeGroup(self.context, **self.master_ng_dict)
        mock_objects_nodegroup_list.return_value = [master_ng, worker_ng]
        mock_driver.return_value = k8s_dr.Driver()

        CONF.set_override('etcd_discovery_service_endpoint_format',
                          'http://etcd/test?size=%(size)d',
                          group='cluster')
        mock_req = mock.MagicMock(text='https://address/token',
                                  status_code=200)
        reqget.return_value = mock_req
        mock_get_subnet.return_value = self.fixed_subnet_cidr

        (template_path,
         definition,
         env_files) = mock_driver()._extract_template_definition(self.context,
                                                                 cluster)

        expected = {
            'cloud_provider_enabled': 'false',
            'ssh_key_name': 'keypair_id',
            'external_network': 'e2a6c8b0-a3c2-42a3-b3f4-01400a30896e',
            'fixed_network': 'fixed_network',
            'fixed_network_name': 'fixed_network',
            'fixed_subnet': 'c2a6c8b0-a3c2-42a3-b3f4-01400a30896f',
            'dns_nameserver': 'dns_nameserver',
            'master_image': 'image_id',
            'minion_image': 'image_id',
            'master_flavor': 'master_flavor_id',
            'minion_flavor': 'flavor_id',
            'number_of_minions': 1,
            'number_of_masters': 1,
            'network_driver': 'network_driver',
            'volume_driver': 'volume_driver',
            'docker_volume_size': 20,
            'docker_volume_type': 'lvmdriver-1',
            'docker_storage_driver': 'devicemapper',
            'discovery_url': 'https://address/token',
            'etcd_volume_size': None,
            'etcd_volume_type': '',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy,20.200.0.0/16',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_backend': 'vxlan',
            'system_pods_initial_delay': '15',
            'system_pods_timeout': '1',
            'admission_control_list': 'fake_list',
            'prometheus_monitoring': 'False',
            'grafana_admin_passwd': 'fake_pwd',
            'kube_dashboard_enabled': 'True',
            'influx_grafana_dashboard_enabled': 'True',
            'username': 'fake_user',
            'cluster_uuid': self.cluster_dict['uuid'],
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'region_name': self.mock_osc.cinder_region_name.return_value,
            'tls_disabled': False,
            'registry_enabled': False,
            'trustee_domain_id': self.mock_keystone.trustee_domain_id,
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': '',
            'auth_url': 'http://192.168.10.10:5000/v3',
            'insecure_registry_url': '10.0.0.1:5000',
            'kube_version': 'fake-version',
            'verify_ca': True,
            'openstack_ca': '',
            'ssh_public_key': 'ssh-rsa AAAAB3Nz',
            "nodes_affinity_policy": "soft-anti-affinity",
            'availability_zone': 'az_1',
            'cert_manager_api': 'False',
            'ingress_controller': 'i-controller',
            'ingress_controller_role': 'i-controller-role',
            'octavia_ingress_controller_tag': None,
            'kubelet_options': '--kubelet',
            'kubeapi_options': '--kubeapi',
            'kubecontroller_options': '--kubecontroller',
            'kubescheduler_options': '--kubescheduler',
            'kubeproxy_options': '--kubeproxy',
            'octavia_enabled': False,
            'kube_service_account_key': 'public_key',
            'kube_service_account_private_key': 'private_key',
            'portal_network_cidr': '10.254.0.0/16',
            'project_id': 'project_id',
            'max_node_count': 2,
            'keystone_auth_default_policy': self.keystone_auth_default_policy,
            'boot_volume_size': '60',
            'boot_volume_type': 'lvmdriver-1',
            'master_role': 'master',
            'worker_role': 'worker',
            'master_nodegroup_name': 'master_ng',
            'worker_nodegroup_name': 'worker_ng',
            'post_install_manifest_url': '',
            'master_lb_allowed_cidrs': None,
            'fixed_subnet_cidr': self.fixed_subnet_cidr,
            'octavia_provider': None,
            'octavia_lb_algorithm': None,
            'octavia_lb_healthcheck': None,
        }
        self.assertEqual(expected, definition)
        self.assertEqual(
            ['../../common/templates/environments/no_private_network.yaml',
             '../../common/templates/environments/no_etcd_volume.yaml',
             '../../common/templates/environments/with_volume.yaml',
             '../../common/templates/environments/no_master_lb.yaml',
             '../../common/templates/environments/disable_floating_ip.yaml',
             '../../common/templates/environments/disable_lb_floating_ip.yaml',
             ],
            env_files)
        reqget.assert_called_once_with('http://etcd/test?size=1', timeout=60)

    @patch('magnum.common.short_id.generate_id')
    @patch('heatclient.common.template_utils.get_template_contents')
    @patch('magnum.drivers.k8s_fedora_atomic_v1.driver.Driver.'
           '_extract_template_definition')
    @patch('magnum.common.clients.OpenStackClients')
    def test_create_stack(self,
                          mock_osc,
                          mock_extract_template_definition,
                          mock_get_template_contents,
                          mock_generate_id):

        mock_generate_id.return_value = 'xx-xx-xx-xx'
        expected_stack_name = 'expected-stack-name-xx-xx-xx-xx'
        expected_template_contents = 'template_contents'
        dummy_cluster_name = 'expected_stack_name'
        expected_timeout = 15

        mock_tpl_files = {}
        mock_get_template_contents.return_value = [
            mock_tpl_files, expected_template_contents]
        mock_extract_template_definition.return_value = ('template/path',
                                                         {}, [])
        mock_heat_client = mock.MagicMock()
        mock_osc.return_value.heat.return_value = mock_heat_client
        mock_cluster = mock.MagicMock()
        mock_cluster.name = dummy_cluster_name

        k8s_dr.Driver().create_cluster(self.context, mock_cluster,
                                       expected_timeout)

        expected_args = {
            'stack_name': expected_stack_name,
            'parameters': {'is_cluster_stack': True},
            'template': expected_template_contents,
            'files': {},
            'environment_files': [],
            'timeout_mins': expected_timeout
        }
        mock_heat_client.stacks.create.assert_called_once_with(**expected_args)

    @patch('magnum.common.short_id.generate_id')
    @patch('heatclient.common.template_utils.get_template_contents')
    @patch('magnum.drivers.k8s_fedora_atomic_v1.driver.Driver.'
           '_extract_template_definition')
    @patch('magnum.common.clients.OpenStackClients')
    def test_create_stack_no_timeout_specified(
            self,
            mock_osc,
            mock_extract_template_definition,
            mock_get_template_contents,
            mock_generate_id):

        mock_generate_id.return_value = 'xx-xx-xx-xx'
        expected_stack_name = 'expected-stack-name-xx-xx-xx-xx'
        expected_template_contents = 'template_contents'
        dummy_cluster_name = 'expected_stack_name'
        expected_timeout = CONF.cluster_heat.create_timeout

        mock_tpl_files = {}
        mock_get_template_contents.return_value = [
            mock_tpl_files, expected_template_contents]
        mock_extract_template_definition.return_value = ('template/path',
                                                         {}, [])
        mock_heat_client = mock.MagicMock()
        mock_osc.return_value.heat.return_value = mock_heat_client
        mock_cluster = mock.MagicMock()
        mock_cluster.name = dummy_cluster_name

        k8s_dr.Driver().create_cluster(self.context, mock_cluster, None)

        expected_args = {
            'stack_name': expected_stack_name,
            'parameters': {'is_cluster_stack': True},
            'template': expected_template_contents,
            'files': {},
            'environment_files': [],
            'timeout_mins': expected_timeout
        }
        mock_heat_client.stacks.create.assert_called_once_with(**expected_args)

    @patch('magnum.common.short_id.generate_id')
    @patch('heatclient.common.template_utils.get_template_contents')
    @patch('magnum.drivers.k8s_fedora_atomic_v1.driver.Driver.'
           '_extract_template_definition')
    @patch('magnum.common.clients.OpenStackClients')
    def test_create_stack_timeout_is_zero(
            self,
            mock_osc,
            mock_extract_template_definition,
            mock_get_template_contents,
            mock_generate_id):

        mock_generate_id.return_value = 'xx-xx-xx-xx'
        expected_stack_name = 'expected-stack-name-xx-xx-xx-xx'
        expected_template_contents = 'template_contents'
        dummy_cluster_name = 'expected_stack_name'
        cluster_timeout = 0
        expected_timeout = CONF.cluster_heat.create_timeout

        mock_tpl_files = {}
        mock_get_template_contents.return_value = [
            mock_tpl_files, expected_template_contents]
        mock_extract_template_definition.return_value = ('template/path',
                                                         {}, [])
        mock_heat_client = mock.MagicMock()
        mock_osc.return_value.heat.return_value = mock_heat_client
        mock_cluster = mock.MagicMock()
        mock_cluster.name = dummy_cluster_name

        k8s_dr.Driver().create_cluster(self.context, mock_cluster,
                                       cluster_timeout)

        expected_args = {
            'stack_name': expected_stack_name,
            'parameters': {'is_cluster_stack': True},
            'template': expected_template_contents,
            'files': {},
            'environment_files': [],
            'timeout_mins': expected_timeout
        }
        mock_heat_client.stacks.create.assert_called_once_with(**expected_args)

    @patch('heatclient.common.template_utils.get_template_contents')
    @patch('magnum.drivers.k8s_fedora_atomic_v1.driver.Driver.'
           '_extract_template_definition')
    @patch('magnum.common.clients.OpenStackClients')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    @patch('magnum.objects.NodeGroup.list')
    def test_update_stack(self,
                          mock_objects_nodegroup_list,
                          mock_objects_cluster_template_get_by_uuid,
                          mock_osc,
                          mock_extract_template_definition,
                          mock_get_template_contents):

        mock_stack_id = 'xx-xx-xx-xx'
        mock_stack = mock.MagicMock(parameters={'number_of_minions': 1})
        mock_stacks = mock.MagicMock()
        mock_stacks.get.return_value = mock_stack
        mock_heat_client = mock.MagicMock(stacks=mock_stacks)
        mock_osc.return_value.heat.return_value = mock_heat_client
        mock_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_objects_cluster_template_get_by_uuid.return_value = mock_template
        mock_cluster = objects.Cluster(self.context, **self.cluster_dict)
        mock_cluster.cluster_template = mock_template
        self.worker_ng_dict['node_count'] = 2
        worker_ng = objects.NodeGroup(self.context, **self.worker_ng_dict)
        worker_ng.stack_id = mock_stack_id
        master_ng = objects.NodeGroup(self.context, **self.master_ng_dict)
        mock_objects_nodegroup_list.return_value = [master_ng, worker_ng]

        k8s_dr.Driver().update_cluster({}, mock_cluster)

        expected_args = {
            'parameters': {'number_of_minions': 2},
            'existing': True,
            'disable_rollback': True
        }
        mock_heat_client.stacks.update.assert_called_once_with(mock_stack_id,
                                                               **expected_args)
