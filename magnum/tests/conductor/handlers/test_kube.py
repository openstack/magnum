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

from oslo_config import cfg

from magnum.common import exception
from magnum.conductor.handlers import kube
from magnum import objects
from magnum.tests import base

import mock
from mock import patch


cfg.CONF.import_opt('k8s_protocol', 'magnum.conductor.handlers.kube',
                    group='kubernetes')
cfg.CONF.import_opt('k8s_port', 'magnum.conductor.handlers.kube',
                    group='kubernetes')


class TestKube(base.TestCase):
    def setUp(self):
        super(TestKube, self).setUp()
        self.kube_handler = kube.Handler()

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

    @patch('magnum.objects.Bay.get_by_uuid')
    def test_retrieve_bay_from_pod(self,
                                  mock_bay_get_by_uuid):
        expected_context = 'context'
        expected_bay_uuid = 'bay_uuid'

        pod = self.mock_pod()
        pod.bay_uuid = expected_bay_uuid

        kube._retrieve_bay(expected_context, pod)

        mock_bay_get_by_uuid.assert_called_once_with(expected_context,
                                                     expected_bay_uuid)

    @patch('magnum.objects.Bay.get_by_uuid')
    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_retrieve_k8s_master_url_from_pod(self,
                                    mock_baymodel_get_by_uuid,
                                    mock_bay_get_by_uuid):
        expected_context = 'context'
        expected_api_address = 'api_address'
        expected_baymodel_id = 'e74c40e0-d825-11e2-a28f-0800200c9a61'
        expected_apiserver_port = 9999

        pod = self.mock_pod()
        pod.bay_uuid = 'bay_uuid'
        bay = self.mock_bay()
        bay.api_address = expected_api_address
        bay.baymodel_id = expected_baymodel_id
        baymodel = self.mock_baymodel()
        baymodel.apiserver_port = expected_apiserver_port

        mock_bay_get_by_uuid.return_value = bay
        mock_baymodel_get_by_uuid.return_value = baymodel

        actual_api_address = kube._retrieve_k8s_master_url(expected_context,
                                                             pod)
        self.assertEqual("http://%s:%d" % (expected_api_address,
                                           expected_apiserver_port),
                         actual_api_address)

    @patch('magnum.objects.Bay.get_by_uuid')
    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_retrieve_k8s_master_url_without_baymodel_apiserver_port(self,
                                                    mock_baymodel_get_by_uuid,
                                                    mock_bay_get_by_uuid):
        expected_context = 'context'
        expected_api_address = 'api_address'
        expected_baymodel_id = 'e74c40e0-d825-11e2-a28f-0800200c9a61'
        expected_protocol = cfg.CONF.kubernetes.k8s_protocol
        expected_apiserver_port = cfg.CONF.kubernetes.k8s_port

        resource = self.mock_pod()
        resource.bay_uuid = 'bay_uuid'
        bay = self.mock_bay()
        bay.api_address = expected_api_address
        bay.baymodel_id = expected_baymodel_id
        baymodel = self.mock_baymodel()
        baymodel.apiserver_port = None

        mock_bay_get_by_uuid.return_value = bay
        mock_baymodel_get_by_uuid.return_value = baymodel

        actual_api_address = kube._retrieve_k8s_master_url(expected_context,
                                                             resource)
        self.assertEqual("%s://%s:%d" % (expected_protocol,
                                         expected_api_address,
                                         expected_apiserver_port),
                                         actual_api_address)

    @patch('magnum.conductor.handlers.kube._retrieve_k8s_master_url')
    def test_pod_create_with_success(self,
                                     mock_retrieve_k8s_master_url):
        expected_master_url = 'api_address'
        expected_pod = self.mock_pod()
        expected_pod.create = mock.MagicMock()

        mock_retrieve_k8s_master_url.return_value = expected_master_url
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.pod_create.return_value = True

            self.kube_handler.pod_create({}, expected_pod)
            self.assertEqual('pending', expected_pod.status)

    @patch('magnum.conductor.handlers.kube._retrieve_k8s_master_url')
    def test_pod_create_with_fail(self,
                                  mock_retrieve_k8s_master_url):
        expected_master_url = 'api_address'
        expected_pod = self.mock_pod()
        expected_pod.create = mock.MagicMock()

        mock_retrieve_k8s_master_url.return_value = expected_master_url
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.pod_create.return_value = False

            self.kube_handler.pod_create({}, expected_pod)
            self.assertEqual('failed', expected_pod.status)

    @patch('magnum.conductor.handlers.kube._object_has_stack')
    @patch('magnum.conductor.handlers.kube._retrieve_k8s_master_url')
    @patch('magnum.objects.Pod.get_by_uuid')
    def test_pod_delete_with_success(self,
                                     mock_pod_get_by_uuid,
                                     mock_retrieve_k8s_master_url,
                                     mock_object_has_stack):
        expected_master_url = 'api_address'
        mock_pod = mock.MagicMock()
        mock_pod.name = 'test-pod'
        mock_pod.uuid = 'test-uuid'
        mock_pod_get_by_uuid.return_value = mock_pod

        mock_retrieve_k8s_master_url.return_value = expected_master_url
        mock_object_has_stack.return_value = True
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.pod_delete.return_value = True

            self.kube_handler.pod_delete(self.context, mock_pod.uuid)

            mock_kube_cli.pod_delete.assert_called_once_with(
                expected_master_url, mock_pod.name)
            mock_pod.destroy.assert_called_once_with(self.context)

    @patch('magnum.conductor.handlers.kube._object_has_stack')
    @patch('magnum.conductor.handlers.kube._retrieve_k8s_master_url')
    @patch('magnum.objects.Pod.get_by_uuid')
    def test_pod_delete_with_failure(self,
                                     mock_pod_get_by_uuid,
                                     mock_retrieve_k8s_master_url,
                                     mock_object_has_stack):
        expected_master_url = 'api_address'
        mock_pod = mock.MagicMock()
        mock_pod.name = 'test-pod'
        mock_pod.uuid = 'test-uuid'
        mock_pod_get_by_uuid.return_value = mock_pod

        mock_retrieve_k8s_master_url.return_value = expected_master_url
        mock_object_has_stack.return_value = True
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.pod_delete.return_value = False

            self.kube_handler.pod_delete(self.context, mock_pod.uuid)

            mock_kube_cli.pod_delete.assert_called_once_with(
                expected_master_url, mock_pod.name)
            self.assertFalse(mock_pod.destroy.called)

    @patch('magnum.conductor.handlers.kube._object_has_stack')
    @patch('magnum.conductor.handlers.kube._retrieve_k8s_master_url')
    @patch('magnum.objects.Pod.get_by_uuid')
    def test_pod_delete_succeeds_when_not_found(self,
                                     mock_pod_get_by_uuid,
                                     mock_retrieve_k8s_master_url,
                                     mock_object_has_stack):
        expected_master_url = 'api_address'
        mock_pod = mock.MagicMock()
        mock_pod.name = 'test-pod'
        mock_pod.uuid = 'test-uuid'
        mock_pod_get_by_uuid.return_value = mock_pod

        mock_retrieve_k8s_master_url.return_value = expected_master_url
        mock_object_has_stack.return_value = True
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.pod_delete.side_effect = exception.PodNotFound()

            self.kube_handler.pod_delete(self.context, mock_pod.uuid)

            mock_kube_cli.pod_delete.assert_called_once_with(
                expected_master_url, mock_pod.name)
            mock_pod.destroy.assert_called_once_with(self.context)

    @patch('magnum.conductor.handlers.kube._retrieve_k8s_master_url')
    def test_service_create_with_success(self,
                                         mock_retrieve_k8s_master_url):
        expected_master_url = 'api_address'
        expected_service = self.mock_service()
        expected_service.create = mock.MagicMock()

        mock_retrieve_k8s_master_url.return_value = expected_master_url
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.service_create.return_value = True

            self.kube_handler.service_create(self.context, expected_service)
            mock_kube_cli.service_create.assert_called_once_with(
                expected_master_url, expected_service)
            expected_service.create.assert_called_once_with(self.context)

    @patch('magnum.conductor.handlers.kube._retrieve_k8s_master_url')
    def test_service_create_with_failure(self,
                                         mock_retrieve_k8s_master_url):
        expected_master_url = 'api_address'
        expected_service = self.mock_service()
        expected_service.create = mock.MagicMock()

        mock_retrieve_k8s_master_url.return_value = expected_master_url
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.service_create.return_value = False

            self.kube_handler.service_create(self.context, expected_service)
            mock_kube_cli.service_create.assert_called_once_with(
                expected_master_url, expected_service)
            self.assertFalse(expected_service.create.called)

    @patch('magnum.conductor.handlers.kube._object_has_stack')
    @patch('magnum.conductor.handlers.kube._retrieve_k8s_master_url')
    @patch('magnum.objects.Service.get_by_uuid')
    def test_service_delete_with_success(self,
                                     mock_service_get_by_uuid,
                                     mock_retrieve_k8s_master_url,
                                     mock_object_has_stack):
        expected_master_url = 'api_address'
        mock_service = mock.MagicMock()
        mock_service.name = 'test-service'
        mock_service.uuid = 'test-uuid'
        mock_service_get_by_uuid.return_value = mock_service

        mock_retrieve_k8s_master_url.return_value = expected_master_url
        mock_object_has_stack.return_value = True
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.service_delete.return_value = True

            self.kube_handler.service_delete(self.context, mock_service.uuid)

            mock_kube_cli.service_delete.assert_called_once_with(
                expected_master_url, mock_service.name)
            mock_service.destroy.assert_called_once_with(self.context)

    @patch('magnum.conductor.handlers.kube._object_has_stack')
    @patch('magnum.conductor.handlers.kube._retrieve_k8s_master_url')
    @patch('magnum.objects.Service.get_by_uuid')
    def test_service_delete_with_failure(self,
                                     mock_service_get_by_uuid,
                                     mock_retrieve_k8s_master_url,
                                     mock_object_has_stack):
        expected_master_url = 'api_address'
        mock_service = mock.MagicMock()
        mock_service.name = 'test-service'
        mock_service.uuid = 'test-uuid'
        mock_service_get_by_uuid.return_value = mock_service

        mock_retrieve_k8s_master_url.return_value = expected_master_url
        mock_object_has_stack.return_value = True
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.service_delete.return_value = False

            self.kube_handler.service_delete(self.context, mock_service.uuid)

            mock_kube_cli.service_delete.assert_called_once_with(
                expected_master_url, mock_service.name)
            self.assertFalse(mock_service.destroy.called)

    @patch('magnum.conductor.handlers.kube._retrieve_k8s_master_url')
    def test_rc_create_with_success(self,
                                    mock_retrieve_k8s_master_url):
        expected_master_url = 'api_address'
        expected_rc = self.mock_rc()
        expected_rc.create = mock.MagicMock()

        mock_retrieve_k8s_master_url.return_value = expected_master_url
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.rc_create.return_value = True

            self.kube_handler.rc_create({}, expected_rc)
            mock_kube_cli.rc_create.assert_called_once_with(
                expected_master_url, expected_rc)

    @patch('magnum.conductor.handlers.kube._retrieve_k8s_master_url')
    def test_rc_create_with_failure(self,
                                    mock_retrieve_k8s_master_url):
        expected_master_url = 'api_address'
        expected_rc = self.mock_rc()
        expected_rc.create = mock.MagicMock()

        mock_retrieve_k8s_master_url.return_value = expected_master_url
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.rc_create.return_value = False

            self.kube_handler.rc_create(self.context, expected_rc)
            mock_kube_cli.rc_create.assert_called_once_with(
                expected_master_url, expected_rc)
            self.assertFalse(expected_rc.create.called)

    @patch('magnum.conductor.handlers.kube._object_has_stack')
    @patch('magnum.conductor.handlers.kube._retrieve_k8s_master_url')
    @patch('magnum.objects.ReplicationController.get_by_uuid')
    def test_rc_delete_with_success(self,
                                    mock_rc_get_by_uuid,
                                    mock_retrieve_k8s_master_url,
                                    mock_object_has_stack):
        expected_master_url = 'api_address'
        mock_rc = mock.MagicMock()
        mock_rc.name = 'test-rc'
        mock_rc.uuid = 'test-uuid'
        mock_rc_get_by_uuid.return_value = mock_rc

        mock_retrieve_k8s_master_url.return_value = expected_master_url
        mock_object_has_stack.return_value = True
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.rc_delete.return_value = True

            self.kube_handler.rc_delete(self.context, mock_rc.uuid)

            mock_kube_cli.rc_delete.assert_called_once_with(
                expected_master_url, mock_rc.name)
            mock_rc.destroy.assert_called_once_with(self.context)

    @patch('magnum.conductor.handlers.kube._object_has_stack')
    @patch('magnum.conductor.handlers.kube._retrieve_k8s_master_url')
    @patch('magnum.objects.ReplicationController.get_by_uuid')
    def test_rc_delete_with_failure(self,
                                    mock_rc_get_by_uuid,
                                    mock_retrieve_k8s_master_url,
                                    mock_object_has_stack):
        expected_master_url = 'api_address'
        mock_rc = mock.MagicMock()
        mock_rc.name = 'test-rc'
        mock_rc.uuid = 'test-uuid'
        mock_rc_get_by_uuid.return_value = mock_rc

        mock_retrieve_k8s_master_url.return_value = expected_master_url
        mock_object_has_stack.return_value = True
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.rc_delete.return_value = False

            self.kube_handler.rc_delete(self.context, mock_rc.uuid)

            mock_kube_cli.rc_delete.assert_called_once_with(
                expected_master_url, mock_rc.name)
            self.assertFalse(mock_rc.destroy.called)

    @patch('magnum.conductor.handlers.kube._retrieve_k8s_master_url')
    def test_rc_update_with_success(self,
                                    mock_retrieve_k8s_master_url):
        expected_master_url = 'api_address'
        expected_rc = self.mock_rc()
        expected_rc.uuid = 'test-uuid'
        expected_rc.refresh = mock.MagicMock()

        mock_retrieve_k8s_master_url.return_value = expected_master_url
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.rc_update.return_value = True

            self.kube_handler.rc_update(self.context, expected_rc)
            mock_kube_cli.rc_update.assert_called_once_with(
                expected_master_url, expected_rc)
            expected_rc.refresh.assert_called_once_with(self.context)

    @patch('magnum.conductor.handlers.kube._retrieve_k8s_master_url')
    def test_rc_update_with_failure(self,
                                    mock_retrieve_k8s_master_url):
        expected_master_url = 'api_address'
        expected_rc = self.mock_rc()
        expected_rc.uuid = 'test-uuid'
        expected_rc.update = mock.MagicMock()

        mock_retrieve_k8s_master_url.return_value = expected_master_url
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.rc_update.return_value = False

            self.kube_handler.rc_update(self.context, expected_rc)
            mock_kube_cli.rc_update.assert_called_once_with(
                expected_master_url, expected_rc)
            self.assertFalse(expected_rc.update.called)

    @patch('magnum.conductor.handlers.kube._retrieve_k8s_master_url')
    def test_service_update_with_success(self,
                                    mock_retrieve_k8s_master_url):
        expected_master_url = 'api_address'
        expected_service = self.mock_service()
        expected_service.uuid = 'test-uuid'
        expected_service.refresh = mock.MagicMock()

        mock_retrieve_k8s_master_url.return_value = expected_master_url
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.service_update.return_value = True

            self.kube_handler.service_update(self.context, expected_service)
            mock_kube_cli.service_update.assert_called_once_with(
                expected_master_url, expected_service)
            expected_service.refresh.assert_called_once_with(self.context)

    @patch('magnum.conductor.handlers.kube._retrieve_k8s_master_url')
    def test_service_update_with_failure(self,
                                    mock_retrieve_k8s_master_url):
        expected_master_url = 'api_address'
        expected_service = self.mock_service()
        expected_service.uuid = 'test-uuid'
        expected_service.refresh = mock.MagicMock()

        mock_retrieve_k8s_master_url.return_value = expected_master_url
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.service_update.return_value = False

            self.kube_handler.service_update(self.context, expected_service)
            mock_kube_cli.service_update.assert_called_once_with(
                expected_master_url, expected_service)
            self.assertFalse(expected_service.refresh.called)

    @patch('magnum.conductor.handlers.kube._retrieve_k8s_master_url')
    def test_pod_update_with_success(self,
                                    mock_retrieve_k8s_master_url):
        expected_master_url = 'api_address'
        expected_pod = self.mock_pod()
        expected_pod.uuid = 'test-uuid'
        expected_pod.refresh = mock.MagicMock()

        mock_retrieve_k8s_master_url.return_value = expected_master_url
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.pod_update.return_value = True

            self.kube_handler.pod_update(self.context, expected_pod)
            mock_kube_cli.pod_update.assert_called_once_with(
                expected_master_url, expected_pod)
            expected_pod.refresh.assert_called_once_with(self.context)

    @patch('magnum.conductor.handlers.kube._retrieve_k8s_master_url')
    def test_pod_update_with_failure(self,
                                    mock_retrieve_k8s_master_url):
        expected_master_url = 'api_address'
        expected_pod = self.mock_pod()
        expected_pod.uuid = 'test-uuid'
        expected_pod.refresh = mock.MagicMock()

        mock_retrieve_k8s_master_url.return_value = expected_master_url
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.pod_update.return_value = False

            self.kube_handler.pod_update(self.context, expected_pod)
            mock_kube_cli.pod_update.assert_called_once_with(
                expected_master_url, expected_pod)
            self.assertFalse(expected_pod.refresh.called)
