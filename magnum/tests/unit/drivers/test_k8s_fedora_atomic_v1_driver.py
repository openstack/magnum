# Copyright (c) 2018 European Organization for Nuclear Research.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from unittest.mock import patch

from magnum.common import exception
from magnum.drivers.k8s_fedora_atomic_v1 import driver
from magnum.tests.unit.db import base
from magnum.tests.unit.objects import utils as obj_utils


class K8sFedoraAtomicV1DriverTest(base.DbTestCase):

    def setUp(self):
        super(K8sFedoraAtomicV1DriverTest, self).setUp()
        self.driver = driver.Driver()
        self.cluster_template = obj_utils.create_test_cluster_template(
            self.context, uuid='94889aa4-e686-11e9-81b4-2a2ae2dbcce4',
            name='test_2', id=2, labels={'kube_tag': 'v1.14.7'},
            image_id='test-image2')
        self.cluster_obj = obj_utils.create_test_cluster(
            self.context, name='cluster_example_A', image_id='test-image1')
        self.cluster_obj.refresh()
        self.nodegroup_obj = obj_utils.create_test_nodegroup(
            self.context, name='test_ng', cluster_id=self.cluster_obj.uuid,
            uuid='27e3153e-d5bf-4b7e-b517-fb518e17f34c',
            project_id=self.cluster_obj.project_id, is_default=False,
            image_id='test-image1')
        self.nodegroup_obj.refresh()

    @patch('magnum.common.keystone.KeystoneClientV3')
    @patch('magnum.common.clients.OpenStackClients')
    def test_upgrade_default_worker_ng(self, mock_osc, mock_keystone):
        mock_keystone.is_octavia_enabled.return_value = False
        def_ng = self.cluster_obj.default_ng_worker
        self.driver.upgrade_cluster(self.context, self.cluster_obj,
                                    self.cluster_template, 1, def_ng)
        # make sure that the kube_tag is reflected correctly to the cluster
        # and the default nodegroups.
        self.assertEqual(self.cluster_template.labels['kube_tag'],
                         self.cluster_obj.labels['kube_tag'])
        self.assertEqual(self.cluster_template.labels['kube_tag'],
                         self.cluster_obj.default_ng_master.labels['kube_tag'])
        self.assertEqual(self.cluster_template.labels['kube_tag'],
                         def_ng.labels['kube_tag'])
        # make sure that the image from the cluster
        # template is NOT set to the default nodegroups.
        self.assertEqual('test-image1',
                         self.cluster_obj.default_ng_master.image_id)
        self.assertEqual('test-image1', def_ng.image_id)
        # check that the non-default nodegroup was not changed
        self.assertNotIn('kube_tag', self.nodegroup_obj.labels)
        self.assertEqual('test-image1', self.nodegroup_obj.image_id)

    @patch('magnum.common.keystone.KeystoneClientV3')
    @patch('magnum.common.clients.OpenStackClients')
    def test_upgrade_default_master_ng(self, mock_osc, mock_keystone):
        mock_keystone.is_octavia_enabled.return_value = False
        def_ng = self.cluster_obj.default_ng_master
        self.driver.upgrade_cluster(self.context, self.cluster_obj,
                                    self.cluster_template, 1, def_ng)
        # make sure that the kube_tag is reflected correctly to the cluster
        # and the default nodegroups.
        self.assertEqual(self.cluster_template.labels['kube_tag'],
                         self.cluster_obj.labels['kube_tag'])
        self.assertEqual(self.cluster_template.labels['kube_tag'],
                         self.cluster_obj.default_ng_worker.labels['kube_tag'])
        self.assertEqual(self.cluster_template.labels['kube_tag'],
                         def_ng.labels['kube_tag'])
        # make sure that the image from the cluster
        # template is NOT set to the default nodegroups.
        self.assertEqual('test-image1',
                         self.cluster_obj.default_ng_worker.image_id)
        self.assertEqual('test-image1', def_ng.image_id)
        # check that the non-default nodegroup was not changed
        self.assertNotIn('kube_tag', self.nodegroup_obj.labels)
        self.assertEqual('test-image1', self.nodegroup_obj.image_id)

    @patch('magnum.common.keystone.KeystoneClientV3')
    @patch('magnum.common.clients.OpenStackClients')
    def test_upgrade_non_default_ng(self, mock_osc, mock_keystone):
        mock_keystone.is_octavia_enabled.return_value = False
        self.driver.upgrade_cluster(self.context, self.cluster_obj,
                                    self.cluster_template, 1,
                                    self.nodegroup_obj)
        # check that the cluster and default nodegroups were not changed
        self.assertNotIn('kube_tag', self.cluster_obj.labels)
        self.assertNotIn('kube_tag', self.cluster_obj.default_ng_master.labels)
        self.assertNotIn('kube_tag', self.cluster_obj.default_ng_worker.labels)
        # make sure that the image from the cluster template
        # is not reflected to the default nodegroups.
        self.assertEqual('test-image1',
                         self.cluster_obj.default_ng_master.image_id)
        self.assertEqual('test-image1',
                         self.cluster_obj.default_ng_worker.image_id)
        # check that the non-default nodegroup reflects the cluster template.
        self.assertEqual(self.cluster_template.labels['kube_tag'],
                         self.nodegroup_obj.labels['kube_tag'])
        self.assertEqual('test-image1',
                         self.nodegroup_obj.image_id)

    @patch('magnum.common.keystone.KeystoneClientV3')
    @patch('magnum.common.clients.OpenStackClients')
    def test_downgrade_not_supported(self, mock_osc, mock_keystone):
        # Scenario, a user creates a nodegroup with kube_tag
        # greater that the one set in cluster's template. Check
        # that downgrading is not supported.
        self.nodegroup_obj.labels = {'kube_tag': 'v1.14.7'}
        self.nodegroup_obj.save()
        self.cluster_template.labels = {'kube_tag': 'v1.14.3'}
        self.cluster_template.save()
        mock_keystone.is_octavia_enabled.return_value = False
        self.assertRaises(exception.InvalidVersion,
                          self.driver.upgrade_cluster, self.context,
                          self.cluster_obj, self.cluster_template, 1,
                          self.nodegroup_obj)

    @patch('magnum.common.keystone.KeystoneClientV3')
    @patch('magnum.common.clients.OpenStackClients')
    def test_invalid_ct(self, mock_osc, mock_keystone):
        # Scenario, a user creates a nodegroup with kube_tag
        # greater that the one set in cluster's template. Check
        # that downgrading is not supported.
        self.cluster_template.labels = {}
        self.cluster_template.save()
        mock_keystone.is_octavia_enabled.return_value = False
        self.assertRaises(exception.InvalidClusterTemplateForUpgrade,
                          self.driver.upgrade_cluster, self.context,
                          self.cluster_obj, self.cluster_template, 1,
                          self.nodegroup_obj)

    @patch('magnum.common.keystone.KeystoneClientV3')
    @patch('magnum.common.clients.OpenStackClients')
    def test_ca_rotate_not_supported(self, mock_osc, mock_keystone):
        self.cluster_template.cluster_distro = 'fedora-atomic'
        self.cluster_template.save()
        mock_keystone.is_octavia_enabled.return_value = False
        self.assertRaises(exception.NotSupported,
                          self.driver.rotate_ca_certificate,
                          self.context,
                          self.cluster_obj)
