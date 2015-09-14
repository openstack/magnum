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

from magnum.conductor import k8s_api
from magnum import objects
from magnum.tests import base


class TestK8sAPI(base.TestCase):

    @patch('magnum.objects.Bay.get_by_uuid')
    def test_retrieve_k8s_api_endpoint(self, mock_bay_get_by_uuid):
        expected_context = 'context'
        expected_api_address = 'api_address'

        resource = objects.Pod({})
        resource.bay_uuid = 'bay_uuid'
        bay = objects.Bay({})
        bay.api_address = expected_api_address

        mock_bay_get_by_uuid.return_value = bay

        actual_api_endpoint = k8s_api.K8sAPI._retrieve_k8s_api_endpoint(
            expected_context, resource)
        self.assertEqual(expected_api_address, actual_api_endpoint)

    @patch('magnum.conductor.k8s_api.K8sAPI')
    def test_create_k8s_api(self, mock_k8s_api_cls):
        context = 'context'
        bay = objects.Bay({})
        k8s_api.create_k8s_api(context, bay)
        mock_k8s_api_cls.assert_called_once_with(context, bay)
