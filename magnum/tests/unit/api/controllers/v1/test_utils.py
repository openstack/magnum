# Copyright 2013 Red Hat, Inc.
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

import jsonpatch
from unittest import mock

from oslo_utils import uuidutils
import wsme

from magnum.api import utils
from magnum.common import exception
import magnum.conf
from magnum.tests.unit.api import base


CONF = magnum.conf.CONF


class TestApiUtils(base.FunctionalTest):

    def test_validate_limit(self):
        limit = utils.validate_limit(10)
        self.assertEqual(10, 10)

        # max limit
        limit = utils.validate_limit(999999999)
        self.assertEqual(CONF.api.max_limit, limit)

        # negative
        self.assertRaises(wsme.exc.ClientSideError, utils.validate_limit, -1)

        # zero
        self.assertRaises(wsme.exc.ClientSideError, utils.validate_limit, 0)

    def test_validate_sort_dir(self):
        sort_dir = utils.validate_sort_dir('asc')
        self.assertEqual('asc', sort_dir)

        # invalid sort_dir parameter
        self.assertRaises(wsme.exc.ClientSideError,
                          utils.validate_sort_dir,
                          'fake-sort')

    @mock.patch('pecan.request')
    @mock.patch('magnum.objects.Cluster.get_by_name')
    @mock.patch('magnum.objects.Cluster.get_by_uuid')
    def test_get_resource_with_uuid(
            self,
            mock_get_by_uuid,
            mock_get_by_name,
            mock_request):
        mock_cluster = mock.MagicMock
        mock_get_by_uuid.return_value = mock_cluster
        uuid = uuidutils.generate_uuid()

        returned_cluster = utils.get_resource('Cluster', uuid)

        mock_get_by_uuid.assert_called_once_with(mock_request.context, uuid)
        self.assertFalse(mock_get_by_name.called)
        self.assertEqual(mock_cluster, returned_cluster)

    @mock.patch('pecan.request')
    @mock.patch('magnum.objects.Cluster.get_by_name')
    @mock.patch('magnum.objects.Cluster.get_by_uuid')
    def test_get_resource_with_name(
            self,
            mock_get_by_uuid,
            mock_get_by_name,
            mock_request):
        mock_cluster = mock.MagicMock
        mock_get_by_name.return_value = mock_cluster

        returned_cluster = utils.get_resource('Cluster', 'fake-name')

        self.assertFalse(mock_get_by_uuid.called)
        mock_get_by_name.assert_called_once_with(mock_request.context,
                                                 'fake-name')
        self.assertEqual(mock_cluster, returned_cluster)

    @mock.patch.object(uuidutils, 'is_uuid_like', return_value=True)
    def test_get_openstack_resource_by_uuid(self, fake_is_uuid_like):
        fake_manager = mock.MagicMock()
        fake_manager.get.return_value = 'fake_resource_data'
        resource_data = utils.get_openstack_resource(fake_manager,
                                                     'fake_resource',
                                                     'fake_resource_type')
        self.assertEqual('fake_resource_data', resource_data)

    @mock.patch.object(uuidutils, 'is_uuid_like', return_value=False)
    def test_get_openstack_resource_by_name(self, fake_is_uuid_like):
        fake_manager = mock.MagicMock()
        fake_manager.list.return_value = ['fake_resource_data']
        resource_data = utils.get_openstack_resource(fake_manager,
                                                     'fake_resource',
                                                     'fake_resource_type')
        self.assertEqual('fake_resource_data', resource_data)

    @mock.patch.object(uuidutils, 'is_uuid_like', return_value=False)
    def test_get_openstack_resource_non_exist(self, fake_is_uuid_like):
        fake_manager = mock.MagicMock()
        fake_manager.list.return_value = []
        self.assertRaises(exception.ResourceNotFound,
                          utils.get_openstack_resource,
                          fake_manager, 'fake_resource', 'fake_resource_type')

    @mock.patch.object(uuidutils, 'is_uuid_like', return_value=False)
    def test_get_openstack_resource_multi_exist(self, fake_is_uuid_like):
        fake_manager = mock.MagicMock()
        fake_manager.list.return_value = ['fake_resource_data1',
                                          'fake_resource_data2']
        self.assertRaises(exception.Conflict,
                          utils.get_openstack_resource,
                          fake_manager, 'fake_resource', 'fake_resource_type')

    @mock.patch.object(jsonpatch, 'apply_patch')
    def test_apply_jsonpatch(self, mock_jsonpatch):
        doc = {'cluster_uuid': 'id', 'node_count': 1}
        patch = [{"path": "/node_count", "value": 2, "op": "replace"}]
        utils.apply_jsonpatch(doc, patch)
        mock_jsonpatch.assert_called_once_with(doc, patch)

    def test_apply_jsonpatch_add_attr_not_exist(self):
        doc = {'cluster_uuid': 'id', 'node_count': 1}
        patch = [{"path": "/fake", "value": 2, "op": "add"}]
        exc = self.assertRaises(wsme.exc.ClientSideError,
                                utils.apply_jsonpatch,
                                doc, patch)
        self.assertEqual(
            "Adding a new attribute /fake to the root of the resource is "
            "not allowed.", exc.faultstring)

    def test_apply_jsonpatch_add_attr_already_exist(self):
        doc = {'cluster_uuid': 'id', 'node_count': 1}
        patch = [{"path": "/node_count", "value": 2, "op": "add"}]
        exc = self.assertRaises(wsme.exc.ClientSideError,
                                utils.apply_jsonpatch,
                                doc, patch)

        self.assertEqual(
            "The attribute /node_count has existed, please use "
            "'replace' operation instead.", exc.faultstring)

    def test_validate_docker_memory(self):
        utils.validate_docker_memory('512m')
        utils.validate_docker_memory('512g')
        self.assertRaises(wsme.exc.ClientSideError,
                          utils.validate_docker_memory, "512gg")
        # Docker require that Minimum memory limit >= 4M
        self.assertRaises(wsme.exc.ClientSideError,
                          utils.validate_docker_memory, "3m")
