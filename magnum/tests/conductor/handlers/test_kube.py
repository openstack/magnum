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

from magnum.conductor.handlers import kube
from magnum import objects
from magnum.tests import base

import mock
from mock import patch


class TestKube(base.BaseTestCase):
    def setUp(self):
        super(TestKube, self).setUp()
        self.kube_handler = kube.Handler()

    def mock_pod(self):
        return objects.Pod({})

    def mock_service(self):
        return objects.Service({})

    def mock_bay(self):
        return objects.Bay({})

    def mock_baymodel(self):
        return objects.BayModel({})

    @patch('magnum.objects.Bay.get_by_uuid')
    def test_retrive_bay_from_pod(self,
                                  mock_bay_get_by_uuid):
        expected_context = 'context'
        expected_bay_uuid = 'bay_uuid'

        pod = self.mock_pod()
        pod.bay_uuid = expected_bay_uuid

        kube._retrive_bay(expected_context, pod)

        mock_bay_get_by_uuid.assert_called_once_with(expected_context,
                                                     expected_bay_uuid)

    @patch('magnum.objects.Bay.get_by_uuid')
    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_retrive_k8s_master_url_from_pod(self,
                                    mock_baymodel_get_by_uuid,
                                    mock_bay_get_by_uuid):
        expected_context = 'context'
        expected_master_address = 'master_address'
        expected_baymodel_id = 'e74c40e0-d825-11e2-a28f-0800200c9a61'
        expected_apiserver_port = 8080

        pod = self.mock_pod()
        pod.bay_uuid = 'bay_uuid'
        bay = self.mock_bay()
        bay.master_address = expected_master_address
        bay.baymodel_id = expected_baymodel_id
        baymodel = self.mock_baymodel()
        baymodel.apiserver_port = expected_apiserver_port

        mock_bay_get_by_uuid.return_value = bay
        mock_baymodel_get_by_uuid.return_value = baymodel

        actual_master_address = kube._retrive_k8s_master_url(expected_context,
                                                             pod)
        self.assertEqual("http://%s:%d" % (expected_master_address,
                                           expected_apiserver_port),
                         actual_master_address)

    @patch('magnum.conductor.handlers.kube._retrive_k8s_master_url')
    def test_pod_create_with_success(self,
                                     mock_retrive_k8s_master_url):
        expected_master_url = 'master_address'
        expected_pod = self.mock_pod()
        expected_pod.create = mock.MagicMock()

        mock_retrive_k8s_master_url.return_value = expected_master_url
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.pod_create.return_value = True

            self.kube_handler.pod_create({}, expected_pod)
            self.assertEqual('pending', expected_pod.status)

    @patch('magnum.conductor.handlers.kube._retrive_k8s_master_url')
    def test_pod_create_with_fail(self,
                                  mock_retrive_k8s_master_url):
        expected_master_url = 'master_address'
        expected_pod = self.mock_pod()
        expected_pod.create = mock.MagicMock()

        mock_retrive_k8s_master_url.return_value = expected_master_url
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.pod_create.return_value = False

            self.kube_handler.pod_create({}, expected_pod)
            self.assertEqual('failed', expected_pod.status)

    @patch('magnum.conductor.handlers.kube._retrive_k8s_master_url')
    def test_service_create_with_success(self,
                                         mock_retrive_k8s_master_url):
        expected_master_url = 'master_address'
        expected_service = self.mock_service()
        expected_service.create = mock.MagicMock()

        mock_retrive_k8s_master_url.return_value = expected_master_url
        with patch.object(self.kube_handler, 'kube_cli') as mock_kube_cli:
            mock_kube_cli.service_create.return_value = True

            self.kube_handler.service_create({}, expected_service)
            mock_kube_cli.service_create.assert_called_once_with(
                expected_master_url, expected_service)
