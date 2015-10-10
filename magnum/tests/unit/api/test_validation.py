# Copyright 2015 Huawei Technologies Co.,LTD.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock

from magnum.api import validation as v
from magnum.common import exception
from magnum.tests import base


class TestValidation(base.BaseTestCase):

    def _test_enforce_bay_types(
            self,
            mock_bay_get_by_uuid,
            mock_baymodel_get_by_uuid,
            mock_pecan_request,
            bay_type,
            allowed_bay_types,
            assert_raised=False):

        @v.enforce_bay_types(*allowed_bay_types)
        def test(self, obj):
            return obj.name

        context = mock_pecan_request.context
        obj = mock.MagicMock()
        obj.name = 'test_object'
        obj.bay_uuid = 'bay_uuid'
        bay = mock.MagicMock()
        bay.baymodel_id = 'baymodel_id'
        baymodel = mock.MagicMock()
        baymodel.coe = bay_type

        mock_bay_get_by_uuid.return_value = bay
        mock_baymodel_get_by_uuid.return_value = baymodel

        if assert_raised:
            self.assertRaises(exception.InvalidParameterValue, test, self, obj)
        else:
            ret = test(self, obj)
            mock_bay_get_by_uuid.assert_called_once_with(context, 'bay_uuid')
            mock_baymodel_get_by_uuid.assert_called_once_with(
                context, 'baymodel_id')
            self.assertEqual(ret, 'test_object')

    @mock.patch('pecan.request')
    @mock.patch('magnum.objects.BayModel.get_by_uuid')
    @mock.patch('magnum.objects.Bay.get_by_uuid')
    def test_enforce_bay_types_one_allowed(
            self,
            mock_bay_get_by_uuid,
            mock_baymodel_get_by_uuid,
            mock_pecan_request):

        bay_type = 'type1'
        allowed_bay_types = ['type1']
        self._test_enforce_bay_types(
            mock_bay_get_by_uuid, mock_baymodel_get_by_uuid,
            mock_pecan_request, bay_type, allowed_bay_types)

    @mock.patch('pecan.request')
    @mock.patch('magnum.objects.BayModel.get_by_uuid')
    @mock.patch('magnum.objects.Bay.get_by_uuid')
    def test_enforce_bay_types_two_allowed(
            self,
            mock_bay_get_by_uuid,
            mock_baymodel_get_by_uuid,
            mock_pecan_request):

        bay_type = 'type1'
        allowed_bay_types = ['type1', 'type2']
        self._test_enforce_bay_types(
            mock_bay_get_by_uuid, mock_baymodel_get_by_uuid,
            mock_pecan_request, bay_type, allowed_bay_types)

    @mock.patch('pecan.request')
    @mock.patch('magnum.objects.BayModel.get_by_uuid')
    @mock.patch('magnum.objects.Bay.get_by_uuid')
    def test_enforce_bay_types_not_allowed(
            self,
            mock_bay_get_by_uuid,
            mock_baymodel_get_by_uuid,
            mock_pecan_request):

        bay_type = 'type1'
        allowed_bay_types = ['type2']
        self._test_enforce_bay_types(
            mock_bay_get_by_uuid, mock_baymodel_get_by_uuid,
            mock_pecan_request, bay_type, allowed_bay_types,
            assert_raised=True)

    def _test_enforce_network_driver_types_post(
            self,
            network_driver_type,
            allowed_network_driver_types,
            assert_raised=False):

        @v.enforce_network_driver_types(allowed_network_driver_types)
        def test(self, baymodel):
            pass

        baymodel = mock.MagicMock()
        baymodel.name = 'test_baymodel'
        baymodel.network_driver = network_driver_type
        baymodel.coe = 'kubernetes'
        if assert_raised:
            self.assertRaises(exception.InvalidParameterValue,
                              test, self, baymodel)
        else:
            test(self, baymodel)

    def test_enforce_network_driver_types_one_allowed_post(self):
        self._test_enforce_network_driver_types_post(
            network_driver_type='type1',
            allowed_network_driver_types={'kubernetes': ['type1']})

    def test_enforce_network_driver_types_two_allowed_post(self):
        self._test_enforce_network_driver_types_post(
            network_driver_type='type1',
            allowed_network_driver_types={'kubernetes': ['type1', 'type2']})

    def test_enforce_network_driver_types_not_allowed_post(self):
        self._test_enforce_network_driver_types_post(
            network_driver_type='type1',
            allowed_network_driver_types={'kubernetes': ['type2']},
            assert_raised=True)

    @mock.patch('pecan.request')
    @mock.patch('magnum.objects.BayModel.get_by_uuid')
    def _test_enforce_network_driver_types_patch(
            self,
            mock_baymodel_get_by_uuid,
            mock_pecan_request,
            network_driver_type,
            allowed_network_driver_types,
            assert_raised=False):

        @v.enforce_network_driver_types(allowed_network_driver_types)
        def test(self, baymodel_uuid):
            pass

        context = mock_pecan_request.context
        baymodel_uuid = 'test_uuid'
        baymodel = mock.MagicMock()
        baymodel.network_driver = network_driver_type
        baymodel.coe = 'kubernetes'
        mock_baymodel_get_by_uuid.return_value = baymodel

        if assert_raised:
            self.assertRaises(exception.InvalidParameterValue,
                              test, self, baymodel_uuid)
        else:
            test(self, baymodel_uuid)
            mock_baymodel_get_by_uuid.assert_called_once_with(
                context, baymodel_uuid)

    def test_enforce_network_driver_types_one_allowed_patch(self):
        self._test_enforce_network_driver_types_patch(
            network_driver_type='type1',
            allowed_network_driver_types={'kubernetes': ['type1']})

    def test_enforce_network_driver_types_two_allowed_patch(self):
        self._test_enforce_network_driver_types_patch(
            network_driver_type='type1',
            allowed_network_driver_types={'kubernetes': ['type1', 'type2']})

    def test_enforce_network_driver_types_not_allowed_patch(self):
        self._test_enforce_network_driver_types_patch(
            network_driver_type='type1',
            allowed_network_driver_types={'kubernetes': ['type2']},
            assert_raised=True)
