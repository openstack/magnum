# Copyright 2015 Huawei Technologies Co.,LTD.
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

from mock import patch
from oslo_config import cfg

from magnum.conductor import k8s_api
from magnum import objects
from magnum.tests import base


class TestK8sAPI(base.TestCase):

    def _test_retrieve_k8s_api_endpoint(self, mock_baymodel_get_by_uuid,
                                        mock_bay_get_by_uuid,
                                        apiserver_port=None):
        expected_context = 'context'
        expected_api_address = 'api_address'
        expected_baymodel_id = 'e74c40e0-d825-11e2-a28f-0800200c9a61'
        expected_protocol = cfg.CONF.kubernetes.k8s_protocol
        if apiserver_port is None:
            expected_apiserver_port = cfg.CONF.kubernetes.k8s_port
        else:
            expected_apiserver_port = apiserver_port

        resource = objects.Pod({})
        resource.bay_uuid = 'bay_uuid'
        bay = objects.Bay({})
        bay.api_address = expected_api_address
        bay.baymodel_id = expected_baymodel_id
        baymodel = objects.BayModel({})
        baymodel.apiserver_port = apiserver_port

        mock_bay_get_by_uuid.return_value = bay
        mock_baymodel_get_by_uuid.return_value = baymodel

        actual_api_endpoint = k8s_api.K8sAPI._retrieve_k8s_api_endpoint(
            expected_context, resource)
        self.assertEqual("%s://%s:%d" % (expected_protocol,
                                         expected_api_address,
                                         expected_apiserver_port),
                         actual_api_endpoint)

    @patch('magnum.objects.Bay.get_by_uuid')
    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_retrieve_k8s_api_endpoint(
            self,
            mock_baymodel_get_by_uuid,
            mock_bay_get_by_uuid):
        self._test_retrieve_k8s_api_endpoint(mock_baymodel_get_by_uuid,
                                             mock_bay_get_by_uuid,
                                             apiserver_port=9999)

    @patch('magnum.objects.Bay.get_by_uuid')
    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_retrieve_k8s_api_endpoint_without_baymodel_apiserver_port(
            self,
            mock_baymodel_get_by_uuid,
            mock_bay_get_by_uuid):
        self._test_retrieve_k8s_api_endpoint(mock_baymodel_get_by_uuid,
                                             mock_bay_get_by_uuid)

    @patch('magnum.conductor.k8s_api.K8sAPI')
    def test_create_k8s_api(self, mock_k8s_api_cls):
        context = 'context'
        bay = objects.Bay({})
        k8s_api.create_k8s_api(context, bay)
        mock_k8s_api_cls.assert_called_once_with(context, bay)
