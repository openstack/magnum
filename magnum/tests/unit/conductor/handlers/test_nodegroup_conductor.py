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

from unittest import mock
from unittest.mock import patch

from heatclient import exc

from magnum.common import exception
from magnum.conductor.handlers import nodegroup_conductor
from magnum.objects import fields
from magnum.tests.unit.db import base as db_base
from magnum.tests.unit.objects import utils as obj_utils


class TestHandler(db_base.DbTestCase):

    def setUp(self):
        super(TestHandler, self).setUp()
        self.handler = nodegroup_conductor.Handler()
        self.cluster = obj_utils.create_test_cluster(self.context)
        self.nodegroup = obj_utils.create_test_nodegroup(
            self.context, cluster_id=self.cluster.uuid)

    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_nodegroup_create(self, mock_get_driver):
        mock_driver = mock.MagicMock()
        mock_get_driver.return_value = mock_driver
        nodegroup = mock.MagicMock()
        self.handler.nodegroup_create(self.context, self.cluster, nodegroup)
        mock_driver.create_nodegroup.assert_called_once_with(self.context,
                                                             self.cluster,
                                                             nodegroup)
        nodegroup.create.assert_called_once()
        nodegroup.save.assert_called_once()
        self.assertEqual(fields.ClusterStatus.UPDATE_IN_PROGRESS,
                         self.cluster.status)
        self.assertEqual(fields.ClusterStatus.CREATE_IN_PROGRESS,
                         nodegroup.status)

    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_nodegroup_create_failed(self, mock_get_driver):
        mock_driver = mock.MagicMock()
        mock_get_driver.return_value = mock_driver
        side_effect = NotImplementedError("Test failure")
        mock_driver.create_nodegroup.side_effect = side_effect
        nodegroup = mock.MagicMock()
        self.assertRaises(NotImplementedError, self.handler.nodegroup_create,
                          self.context, self.cluster, nodegroup)
        mock_driver.create_nodegroup.assert_called_once_with(self.context,
                                                             self.cluster,
                                                             nodegroup)
        nodegroup.create.assert_called_once()
        nodegroup.save.assert_called_once()
        self.assertEqual(fields.ClusterStatus.UPDATE_FAILED,
                         self.cluster.status)
        self.assertEqual(fields.ClusterStatus.CREATE_FAILED,
                         nodegroup.status)
        self.assertEqual("Test failure", nodegroup.status_reason)

    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_nodegroup_create_failed_bad_request(self, mock_get_driver):
        mock_driver = mock.MagicMock()
        mock_get_driver.return_value = mock_driver
        side_effect = exc.HTTPBadRequest("Bad request")
        mock_driver.create_nodegroup.side_effect = side_effect
        nodegroup = mock.MagicMock()
        self.assertRaises(exception.InvalidParameterValue,
                          self.handler.nodegroup_create,
                          self.context, self.cluster, nodegroup)
        mock_driver.create_nodegroup.assert_called_once_with(self.context,
                                                             self.cluster,
                                                             nodegroup)
        nodegroup.create.assert_called_once()
        nodegroup.save.assert_called_once()
        self.assertEqual(fields.ClusterStatus.UPDATE_FAILED,
                         self.cluster.status)
        self.assertEqual(fields.ClusterStatus.CREATE_FAILED,
                         nodegroup.status)
        self.assertEqual("ERROR: Bad request", nodegroup.status_reason)

    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_nodegroup_udpate(self, mock_get_driver):
        mock_driver = mock.MagicMock()
        mock_get_driver.return_value = mock_driver
        self.handler.nodegroup_update(self.context, self.cluster,
                                      self.nodegroup)
        mock_driver.update_nodegroup.assert_called_once_with(self.context,
                                                             self.cluster,
                                                             self.nodegroup)
        self.assertEqual(fields.ClusterStatus.UPDATE_IN_PROGRESS,
                         self.cluster.status)
        self.assertEqual(fields.ClusterStatus.UPDATE_IN_PROGRESS,
                         self.nodegroup.status)

    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_nodegroup_update_failed(self, mock_get_driver):
        mock_driver = mock.MagicMock()
        mock_get_driver.return_value = mock_driver
        side_effect = NotImplementedError("Update failed")
        mock_driver.update_nodegroup.side_effect = side_effect
        self.assertRaises(NotImplementedError, self.handler.nodegroup_update,
                          self.context, self.cluster, self.nodegroup)
        mock_driver.update_nodegroup.assert_called_once_with(self.context,
                                                             self.cluster,
                                                             self.nodegroup)
        self.assertEqual(fields.ClusterStatus.UPDATE_FAILED,
                         self.cluster.status)
        self.assertEqual(fields.ClusterStatus.UPDATE_FAILED,
                         self.nodegroup.status)
        self.assertEqual("Update failed", self.nodegroup.status_reason)

    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_nodegroup_update_failed_bad_request(self, mock_get_driver):
        mock_driver = mock.MagicMock()
        mock_get_driver.return_value = mock_driver
        side_effect = exc.HTTPBadRequest("Bad request")
        mock_driver.update_nodegroup.side_effect = side_effect
        self.assertRaises(exception.InvalidParameterValue,
                          self.handler.nodegroup_update,
                          self.context, self.cluster, self.nodegroup)
        mock_driver.update_nodegroup.assert_called_once_with(self.context,
                                                             self.cluster,
                                                             self.nodegroup)
        self.assertEqual(fields.ClusterStatus.UPDATE_FAILED,
                         self.cluster.status)
        self.assertEqual(fields.ClusterStatus.UPDATE_FAILED,
                         self.nodegroup.status)
        self.assertEqual("ERROR: Bad request", self.nodegroup.status_reason)

    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_nodegroup_delete(self, mock_get_driver):
        mock_driver = mock.MagicMock()
        mock_get_driver.return_value = mock_driver
        self.handler.nodegroup_delete(self.context, self.cluster,
                                      self.nodegroup)
        mock_driver.delete_nodegroup.assert_called_once_with(self.context,
                                                             self.cluster,
                                                             self.nodegroup)
        self.assertEqual(fields.ClusterStatus.UPDATE_IN_PROGRESS,
                         self.cluster.status)
        self.assertEqual(fields.ClusterStatus.DELETE_IN_PROGRESS,
                         self.nodegroup.status)

    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_nodegroup_delete_stack_not_found(self, mock_get_driver):
        mock_driver = mock.MagicMock()
        mock_get_driver.return_value = mock_driver
        nodegroup = mock.MagicMock()
        mock_driver.delete_nodegroup.side_effect = exc.HTTPNotFound()
        self.handler.nodegroup_delete(self.context, self.cluster, nodegroup)
        mock_driver.delete_nodegroup.assert_called_once_with(self.context,
                                                             self.cluster,
                                                             nodegroup)
        self.assertEqual(fields.ClusterStatus.UPDATE_IN_PROGRESS,
                         self.cluster.status)
        nodegroup.destroy.assert_called_once()

    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_nodegroup_delete_stack_and_ng_not_found(self, mock_get_driver):
        mock_driver = mock.MagicMock()
        mock_get_driver.return_value = mock_driver
        nodegroup = mock.MagicMock()
        mock_driver.delete_nodegroup.side_effect = exc.HTTPNotFound()
        nodegroup.destroy.side_effect = exception.NodeGroupNotFound()
        self.handler.nodegroup_delete(self.context, self.cluster, nodegroup)
        mock_driver.delete_nodegroup.assert_called_once_with(self.context,
                                                             self.cluster,
                                                             nodegroup)
        self.assertEqual(fields.ClusterStatus.UPDATE_IN_PROGRESS,
                         self.cluster.status)
        nodegroup.destroy.assert_called_once()

    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_nodegroup_delete_stack_operation_ongoing(self, mock_get_driver):
        mock_driver = mock.MagicMock()
        mock_get_driver.return_value = mock_driver
        mock_driver.delete_nodegroup.side_effect = exc.HTTPConflict()
        self.assertRaises(exception.NgOperationInProgress,
                          self.handler.nodegroup_delete,
                          self.context, self.cluster, self.nodegroup)
        mock_driver.delete_nodegroup.assert_called_once_with(self.context,
                                                             self.cluster,
                                                             self.nodegroup)
        self.assertEqual(fields.ClusterStatus.UPDATE_IN_PROGRESS,
                         self.cluster.status)
        self.assertEqual(fields.ClusterStatus.DELETE_IN_PROGRESS,
                         self.nodegroup.status)

    @patch('magnum.drivers.common.driver.Driver.get_driver')
    def test_nodegroup_delete_failed(self, mock_get_driver):
        mock_driver = mock.MagicMock()
        mock_get_driver.return_value = mock_driver
        side_effect = NotImplementedError("Delete failed")
        mock_driver.delete_nodegroup.side_effect = side_effect
        self.assertRaises(NotImplementedError,
                          self.handler.nodegroup_delete,
                          self.context, self.cluster, self.nodegroup)
        mock_driver.delete_nodegroup.assert_called_once_with(self.context,
                                                             self.cluster,
                                                             self.nodegroup)
        self.assertEqual(fields.ClusterStatus.UPDATE_FAILED,
                         self.cluster.status)
        self.assertEqual(fields.ClusterStatus.DELETE_FAILED,
                         self.nodegroup.status)
        self.assertEqual("Delete failed", self.nodegroup.status_reason)
