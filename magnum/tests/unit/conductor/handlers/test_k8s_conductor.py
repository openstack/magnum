# Copyright 2014 NEC Corporation.  All rights reserved.
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

from magnum.common import exception
from magnum.common.pythonk8sclient.swagger_client import rest
from magnum.conductor.handlers import k8s_conductor
from magnum import objects
from magnum.tests import base

import mock
from mock import patch


class TestK8sConductor(base.TestCase):
    def setUp(self):
        super(TestK8sConductor, self).setUp()
        self.kube_handler = k8s_conductor.Handler()

    def mock_pod(self):
        return objects.Pod({})

    def mock_service(self):
        return objects.Service({})

    def mock_rc(self):
        return objects.ReplicationController({})

    def mock_bay(self):
        return objects.Bay({})

    def mock_baymodel(self):
        return objects.BayModel({})

    @patch('ast.literal_eval')
    def test_pod_create_with_success(self, mock_ast):
        expected_pod = mock.MagicMock()
        expected_pod.uuid = 'test-uuid'
        expected_pod.name = 'test-name'
        expected_pod.bay_uuid = 'test-bay-uuid'
        manifest = {"key": "value"}
        expected_pod.manifest = '{"key": "value"}'
        mock_ast.return_value = {}

        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            self.kube_handler.pod_create(self.context, expected_pod)
            (mock_kube_api.return_value.create_namespaced_pod
                .assert_called_once_with(body=manifest, namespace='default'))

    def test_pod_create_with_fail(self):
        expected_pod = mock.MagicMock()
        manifest = {"key": "value"}
        expected_pod.manifest = '{"key": "value"}'

        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            err = rest.ApiException(status=500)
            mock_kube_api.return_value.create_namespaced_pod.side_effect = err

            self.assertRaises(exception.KubernetesAPIFailed,
                              self.kube_handler.pod_create,
                              self.context, expected_pod)
            (mock_kube_api.return_value
                .create_namespaced_pod
                .assert_called_once_with(body=manifest,
                                         namespace='default'))

    def test_pod_create_fail_on_existing_pod(self):
        expected_pod = mock.MagicMock()
        expected_pod.manifest = '{"key": "value"}'

        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            err = rest.ApiException(status=409)
            mock_kube_api.return_value.create_namespaced_pod.side_effect = err

            self.assertRaises(exception.KubernetesAPIFailed,
                              self.kube_handler.pod_create,
                              self.context, expected_pod)
            self.assertEqual('failed', expected_pod.status)

    @patch('magnum.conductor.utils.object_has_stack')
    @patch('magnum.objects.Pod.get_by_uuid')
    @patch('magnum.objects.Bay.get_by_name')
    def test_pod_delete_with_success(self,
                                     mock_bay_get_by_name,
                                     mock_pod_get_by_uuid,
                                     mock_object_has_stack):
        mock_bay = mock.MagicMock()
        mock_bay_get_by_name.return_value = mock_bay

        mock_pod = mock.MagicMock()
        mock_pod.name = 'test-pod'
        mock_pod.uuid = 'test-uuid'
        mock_pod.bay_uuid = 'test-bay-uuid'
        mock_pod_get_by_uuid.return_value = mock_pod

        mock_object_has_stack.return_value = True
        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            self.kube_handler.pod_delete(self.context,
                                         mock_pod.name,
                                         mock_pod.bay_uuid)

            (mock_kube_api.return_value.delete_namespaced_pod
                .assert_called_once_with(
                    name=mock_pod.name, body={}, namespace='default'))

    @patch('magnum.conductor.utils.object_has_stack')
    @patch('magnum.objects.Pod.get_by_uuid')
    @patch('magnum.objects.Bay.get_by_name')
    def test_pod_delete_with_failure(self, mock_bay_get_by_name,
                                     mock_pod_get_by_uuid,
                                     mock_object_has_stack):
        mock_bay = mock.MagicMock()
        mock_bay_get_by_name.return_value = mock_bay

        mock_pod = mock.MagicMock()
        mock_pod.name = 'test-pod'
        mock_pod.uuid = 'test-uuid'
        mock_pod_get_by_uuid.return_value = mock_pod

        mock_object_has_stack.return_value = True
        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            err = rest.ApiException(status=500)
            mock_kube_api.return_value.delete_namespaced_pod.side_effect = err

            self.assertRaises(exception.KubernetesAPIFailed,
                              self.kube_handler.pod_delete,
                              self.context, mock_pod.name,
                              mock_pod.bay_uuid)
            (mock_kube_api.return_value.delete_namespaced_pod
                .assert_called_once_with(
                    name=mock_pod.name, body={}, namespace='default'))

    @patch('magnum.conductor.utils.object_has_stack')
    @patch('magnum.objects.Pod.get_by_uuid')
    @patch('magnum.objects.Bay.get_by_name')
    def test_pod_delete_succeeds_when_not_found(
            self, mock_bay_get_by_name,
            mock_pod_get_by_uuid,
            mock_object_has_stack):
        mock_bay = mock.MagicMock()
        mock_bay_get_by_name.return_value = mock_bay

        mock_pod = mock.MagicMock()
        mock_pod.name = 'test-pod'
        mock_pod.uuid = 'test-uuid'
        mock_pod_get_by_uuid.return_value = mock_pod

        mock_object_has_stack.return_value = True
        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            err = rest.ApiException(status=404)
            mock_kube_api.return_value.delete_namespaced_pod.side_effect = err

            self.kube_handler.pod_delete(self.context, mock_pod.name,
                                         mock_pod.bay_uuid)

            (mock_kube_api.return_value.delete_namespaced_pod
                .assert_called_once_with(
                    name=mock_pod.name, body={}, namespace='default'))

    @patch('magnum.conductor.k8s_api.create_k8s_api')
    @patch('ast.literal_eval')
    def test_service_create_with_success(self, mock_ast, mock_kube_api):
        fake_service = mock.MagicMock()
        fake_service.name = 'test-name'

        expected_service = mock.MagicMock()
        expected_service.bay_uuid = 'test-bay-uuid'
        expected_service.name = 'test-name'
        expected_service.uuid = 'test-uuid'
        manifest = {"key": "value"}
        expected_service.manifest = '{"key": "value"}'
        mock_ast.return_value = {}

        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            self.kube_handler.service_create(self.context, expected_service)
            (mock_kube_api.return_value.create_namespaced_service
                .assert_called_once_with(body=manifest, namespace='default'))

    def test_service_create_with_failure(self):
        expected_service = mock.MagicMock()
        expected_service.create = mock.MagicMock()
        manifest = {"key": "value"}
        expected_service.manifest = '{"key": "value"}'

        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            err = rest.ApiException(status=404)
            (mock_kube_api.return_value.create_namespaced_service
                .side_effect) = err

            self.assertRaises(exception.KubernetesAPIFailed,
                              self.kube_handler.service_create,
                              self.context, expected_service)
            (mock_kube_api.return_value.create_namespaced_service
                .assert_called_once_with(body=manifest, namespace='default'))

    @patch('magnum.conductor.utils.object_has_stack')
    @patch('magnum.objects.Service.get_by_name')
    @patch('magnum.objects.Bay.get_by_name')
    def test_service_delete_with_success(
            self, mock_bay_get_by_name,
            mock_service_get_by_name,
            mock_object_has_stack):
        mock_bay = mock.MagicMock()
        mock_bay_get_by_name.return_value = mock_bay

        mock_service = mock.MagicMock()
        mock_service.name = 'test-service'
        mock_service.uuid = 'test-uuid'
        mock_service.bay_uuid = 'test-bay-uuid'
        mock_service_get_by_name.return_value = mock_service

        mock_object_has_stack.return_value = True
        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            self.kube_handler.service_delete(self.context,
                                             mock_service.name,
                                             mock_service.bay_uuid)
            (mock_kube_api.return_value.delete_namespaced_service
                .assert_called_once_with(
                    name=mock_service.name, namespace='default'))

    @patch('magnum.conductor.utils.object_has_stack')
    @patch('magnum.objects.Service.get_by_uuid')
    @patch('magnum.objects.Bay.get_by_name')
    def test_service_delete_with_failure(
            self, mock_bay_get_by_name,
            mock_service_get_by_uuid,
            mock_object_has_stack):
        mock_bay = mock.MagicMock()
        mock_bay_get_by_name.return_value = mock_bay

        mock_service = mock.MagicMock()
        mock_service.name = 'test-service'
        mock_service.uuid = 'test-uuid'
        mock_service.bay_uuid = 'test-bay-uuid'
        mock_service_get_by_uuid.return_value = mock_service

        mock_object_has_stack.return_value = True
        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            err = rest.ApiException(status=500)
            (mock_kube_api.return_value.delete_namespaced_service
                .side_effect) = err

            self.assertRaises(exception.KubernetesAPIFailed,
                              self.kube_handler.service_delete,
                              self.context, mock_service.name,
                              mock_service.bay_uuid)
            (mock_kube_api.return_value.delete_namespaced_service
                .assert_called_once_with(
                    name=mock_service.name, namespace='default'))
            self.assertFalse(mock_service.destroy.called)

    @patch('magnum.conductor.utils.object_has_stack')
    @patch('magnum.objects.Service.get_by_uuid')
    @patch('magnum.objects.Bay.get_by_name')
    def test_service_delete_succeeds_when_not_found(
            self, mock_bay_get_by_name,
            mock_service_get_by_uuid,
            mock_object_has_stack):
        mock_bay = mock.MagicMock()
        mock_bay_get_by_name.return_value = mock_bay

        mock_service = mock.MagicMock()
        mock_service.name = 'test-service'
        mock_service.uuid = 'test-uuid'
        mock_service.bay_uuid = 'test-bay-uuid'
        mock_service_get_by_uuid.return_value = mock_service

        mock_object_has_stack.return_value = True
        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            err = rest.ApiException(status=404)
            (mock_kube_api.return_value.delete_namespaced_service
                .side_effect) = err

            self.kube_handler.service_delete(self.context,
                                             mock_service.name,
                                             mock_service.bay_uuid)
            (mock_kube_api.return_value.delete_namespaced_service
                .assert_called_once_with(
                    name=mock_service.name, namespace='default'))

    @patch('ast.literal_eval')
    def test_rc_create_with_success(self, mock_ast):
        expected_rc = mock.MagicMock()
        manifest = {"key": "value"}
        expected_rc.name = 'test-name'
        expected_rc.uuid = 'test-uuid'
        expected_rc.bay_uuid = 'test-bay-uuid'
        expected_rc.manifest = '{"key": "value"}'
        mock_ast.return_value = {}

        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            self.kube_handler.rc_create({}, expected_rc)
            (mock_kube_api.return_value
                .create_namespaced_replication_controller
                .assert_called_once_with(body=manifest, namespace='default'))

    def test_rc_create_with_failure(self):
        expected_rc = mock.MagicMock()
        manifest = {"key": "value"}
        expected_rc.manifest = '{"key": "value"}'

        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            err = rest.ApiException(status=500)
            (mock_kube_api.return_value
                .create_namespaced_replication_controller.side_effect) = err

            self.assertRaises(exception.KubernetesAPIFailed,
                              self.kube_handler.rc_create,
                              self.context, expected_rc)
            (mock_kube_api.return_value
                .create_namespaced_replication_controller
                .assert_called_once_with(body=manifest, namespace='default'))

    @patch('magnum.conductor.utils.object_has_stack')
    @patch('magnum.objects.ReplicationController.get_by_name')
    @patch('magnum.objects.Bay.get_by_name')
    def test_rc_delete_with_success(self, mock_bay_get_by_name,
                                    mock_rc_get_by_name,
                                    mock_object_has_stack):
        mock_bay = mock.MagicMock()
        mock_bay_get_by_name.return_value = mock_bay

        mock_rc = mock.MagicMock()
        mock_rc.name = 'test-rc'
        mock_rc.uuid = 'test-uuid'
        mock_rc_get_by_name.return_value = mock_rc
        bay_uuid = 'test-bay-uuid'

        mock_object_has_stack.return_value = True
        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            self.kube_handler.rc_delete(self.context, mock_rc.name, bay_uuid)
            (mock_kube_api.return_value
                .delete_namespaced_replication_controller
                .assert_called_once_with(name=mock_rc.name, body={},
                                         namespace='default'))

    @patch('magnum.conductor.utils.object_has_stack')
    @patch('magnum.objects.ReplicationController.get_by_uuid')
    @patch('magnum.objects.Bay.get_by_name')
    def test_rc_delete_with_failure(self, mock_bay_get_by_name,
                                    mock_rc_get_by_uuid,
                                    mock_object_has_stack):
        mock_bay = mock.MagicMock()
        mock_bay_get_by_name.return_value = mock_bay

        mock_rc = mock.MagicMock()
        mock_rc.name = 'test-rc'
        mock_rc.uuid = 'test-uuid'
        mock_rc.bay_uuid = 'test-bay-uuid'
        mock_rc_get_by_uuid.return_value = mock_rc

        mock_object_has_stack.return_value = True
        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            err = rest.ApiException(status=500)
            (mock_kube_api.return_value
                .delete_namespaced_replication_controller.side_effect) = err

            self.assertRaises(exception.KubernetesAPIFailed,
                              self.kube_handler.rc_delete,
                              self.context, mock_rc.name,
                              mock_rc.bay_uuid)

            (mock_kube_api.return_value
                .delete_namespaced_replication_controller
                .assert_called_once_with(name=mock_rc.name, body={},
                                         namespace='default'))
            self.assertFalse(mock_rc.destroy.called)

    @patch('magnum.conductor.utils.object_has_stack')
    @patch('magnum.objects.ReplicationController.get_by_uuid')
    @patch('magnum.objects.Bay.get_by_name')
    def test_rc_delete_succeeds_when_not_found(
            self, mock_bay_get_by_name,
            mock_rc_get_by_uuid,
            mock_object_has_stack):
        mock_bay = mock.MagicMock()
        mock_bay_get_by_name.return_value = mock_bay

        mock_rc = mock.MagicMock()
        mock_rc.name = 'test-rc'
        mock_rc.uuid = 'test-uuid'
        mock_rc.bay_uuid = 'test-bay-uuid'
        mock_rc_get_by_uuid.return_value = mock_rc

        mock_object_has_stack.return_value = True
        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            err = rest.ApiException(status=404)
            (mock_kube_api.return_value
                .delete_namespaced_replication_controller.side_effect) = err

            self.kube_handler.rc_delete(self.context,
                                        mock_rc.name,
                                        mock_rc.bay_uuid)

            (mock_kube_api.return_value
                .delete_namespaced_replication_controller
                .assert_called_once_with(name=mock_rc.name, body={},
                                         namespace='default'))

    @patch('magnum.objects.ReplicationController.get_by_name')
    @patch('magnum.objects.ReplicationController.get_by_uuid')
    @patch('magnum.objects.Bay.get_by_name')
    @patch('ast.literal_eval')
    def test_rc_update_with_success(self, mock_ast,
                                    mock_bay_get_by_name,
                                    mock_rc_get_by_uuid,
                                    mock_rc_get_by_name):
        mock_bay = mock.MagicMock()
        mock_bay_get_by_name.return_value = mock_bay

        expected_rc = mock.MagicMock()
        expected_rc.uuid = 'test-uuid'
        expected_rc.name = 'test-name'
        expected_rc.bay_uuid = 'test-bay-uuid'
        expected_rc.manifest = '{"key": "value"}'
        mock_ast.return_value = {}
        mock_rc_get_by_uuid.return_value = expected_rc
        mock_rc_get_by_name.return_value = expected_rc
        name_rc = expected_rc.name

        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            self.kube_handler.rc_update(self.context, expected_rc.name,
                                        expected_rc.bay_uuid,
                                        expected_rc.manifest)
            (mock_kube_api.return_value
             .replace_namespaced_replication_controller
             .assert_called_once_with(body=expected_rc.manifest,
                                      name=name_rc,
                                      namespace='default'))

    @patch('magnum.objects.ReplicationController.get_by_name')
    @patch('magnum.objects.ReplicationController.get_by_uuid')
    @patch('magnum.objects.Bay.get_by_name')
    def test_rc_update_with_failure(self, mock_bay_get_by_name,
                                    mock_rc_get_by_uuid,
                                    mock_rc_get_by_name):
        mock_bay = mock.MagicMock()
        mock_bay_get_by_name.return_value = mock_bay

        expected_rc = mock.MagicMock()
        expected_rc.uuid = 'test-uuid'
        expected_rc.name = 'test-name'
        expected_rc.bay_uuid = 'test-bay-uuid'
        mock_rc_get_by_uuid.return_value = expected_rc
        mock_rc_get_by_name.return_value = expected_rc
        expected_rc.manifest = '{"key": "value"}'
        name_rc = expected_rc.name

        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            err = rest.ApiException(status=404)
            (mock_kube_api.return_value
                .replace_namespaced_replication_controller
                .side_effect) = err

            self.assertRaises(exception.KubernetesAPIFailed,
                              self.kube_handler.rc_update,
                              self.context, expected_rc.name,
                              expected_rc.bay_uuid,
                              expected_rc.manifest)
            (mock_kube_api.return_value
                .replace_namespaced_replication_controller
                .assert_called_once_with(body=expected_rc.manifest,
                                         name=name_rc,
                                         namespace='default'))

    @patch('magnum.objects.Service.get_by_name')
    @patch('magnum.objects.Service.get_by_uuid')
    @patch('magnum.objects.Bay.get_by_name')
    @patch('ast.literal_eval')
    def test_service_update_with_success(self, mock_ast,
                                         mock_bay_get_by_name,
                                         mock_service_get_by_uuid,
                                         mock_service_get_by_name):
        mock_bay = mock.MagicMock()
        mock_bay_get_by_name.return_value = mock_bay

        expected_service = mock.MagicMock()
        expected_service.uuid = 'test-uuid'
        expected_service.name = 'test-name'
        expected_service.bay_uuid = 'test-bay-uuid'
        expected_service.manifest = '{"key": "value"}'
        mock_ast.return_value = {}

        mock_service_get_by_name.return_value = expected_service
        mock_service_get_by_uuid.return_value = expected_service
        service_name = expected_service.name

        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            self.kube_handler.service_update(self.context,
                                             expected_service.name,
                                             expected_service.bay_uuid,
                                             expected_service.manifest)
            (mock_kube_api.return_value.replace_namespaced_service
                .assert_called_once_with(body=expected_service.manifest,
                                         name=service_name,
                                         namespace='default'))

    @patch('magnum.objects.Service.get_by_name')
    @patch('magnum.objects.Service.get_by_uuid')
    @patch('magnum.objects.Bay.get_by_name')
    def test_service_update_with_failure(self, mock_bay_get_by_name,
                                         mock_service_get_by_uuid,
                                         mock_service_get_by_name):
        mock_bay = mock.MagicMock()
        mock_bay_get_by_name.return_value = mock_bay

        expected_service = mock.MagicMock()
        expected_service.uuid = 'test-uuid'
        expected_service.name = 'test-name'
        expected_service.bay_uuid = 'test-bay-uuid'
        expected_service.manifest = '{"key": "value"}'
        mock_service_get_by_uuid.return_value = expected_service
        mock_service_get_by_name.return_value = expected_service
        service_name = expected_service.name

        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            err = rest.ApiException(status=404)
            (mock_kube_api.return_value.replace_namespaced_service
                .side_effect) = err

            self.assertRaises(exception.KubernetesAPIFailed,
                              self.kube_handler.service_update,
                              self.context, expected_service.name,
                              expected_service.bay_uuid,
                              expected_service.manifest)
            (mock_kube_api.return_value.replace_namespaced_service
                .assert_called_once_with(body=expected_service.manifest,
                                         name=service_name,
                                         namespace='default'))

    @patch('magnum.objects.Pod.get_by_name')
    @patch('magnum.objects.Pod.get_by_uuid')
    @patch('magnum.objects.Bay.get_by_name')
    @patch('ast.literal_eval')
    def test_pod_update_with_success(self, mock_ast,
                                     mock_bay_get_by_name,
                                     mock_pod_get_by_uuid,
                                     mock_pod_get_by_name):
        mock_bay = mock.MagicMock()
        mock_bay_get_by_name.return_value = mock_bay

        expected_pod = mock.MagicMock()
        expected_pod.uuid = 'test-uuid'
        expected_pod.name = 'test-name'
        expected_pod.bay_uuid = 'test-bay-uuid'
        expected_pod.manifest = '{"key": "value"}'
        mock_ast.return_value = {}

        mock_pod_get_by_uuid.return_value = expected_pod
        mock_pod_get_by_name.return_value = expected_pod
        name_pod = expected_pod.name

        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            self.kube_handler.pod_update(self.context, expected_pod.name,
                                         expected_pod.bay_uuid,
                                         expected_pod.manifest)
            (mock_kube_api.return_value.replace_namespaced_pod
                .assert_called_once_with(
                    body=expected_pod.manifest, name=name_pod,
                    namespace='default'))

    @patch('magnum.objects.Pod.get_by_name')
    @patch('magnum.objects.Pod.get_by_uuid')
    @patch('magnum.objects.Bay.get_by_name')
    def test_pod_update_with_failure(self, mock_bay_get_by_name,
                                     mock_pod_get_by_uuid,
                                     mock_pod_get_by_name):
        mock_bay = mock.MagicMock()
        mock_bay_get_by_name.return_value = mock_bay

        expected_pod = mock.MagicMock()
        expected_pod.uuid = 'test-uuid'
        expected_pod.name = 'test-name'
        expected_pod.bay_uuid = 'test-bay-uuid'
        mock_pod_get_by_uuid.return_value = expected_pod
        mock_pod_get_by_name.return_value = expected_pod
        expected_pod.manifest = '{"key": "value"}'
        name_pod = expected_pod.name

        with patch('magnum.conductor.k8s_api.create_k8s_api') as \
                mock_kube_api:
            err = rest.ApiException(status=404)
            mock_kube_api.return_value.replace_namespaced_pod.side_effect = err

            self.assertRaises(exception.KubernetesAPIFailed,
                              self.kube_handler.pod_update,
                              self.context, expected_pod.name,
                              expected_pod.bay_uuid,
                              expected_pod.manifest)
            (mock_kube_api.return_value.replace_namespaced_pod
                .assert_called_once_with(
                    body=expected_pod.manifest, name=name_pod,
                    namespace='default'))
