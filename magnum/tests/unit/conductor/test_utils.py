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

from magnum.conductor import utils
from magnum import objects
from magnum.tests import base


class TestConductorUtils(base.TestCase):

    def _test_retrieve_bay(self, obj, mock_bay_get_by_uuid):
        expected_context = 'context'
        expected_bay_uuid = 'bay_uuid'

        obj.bay_uuid = expected_bay_uuid
        utils.retrieve_bay(expected_context, obj)
        mock_bay_get_by_uuid.assert_called_once_with(expected_context,
                                                     expected_bay_uuid)

    @patch('magnum.objects.Bay.get_by_uuid')
    def test_retrieve_bay_from_pod(self,
                                   mock_bay_get_by_uuid):
        self._test_retrieve_bay(objects.Pod({}), mock_bay_get_by_uuid)

    @patch('magnum.objects.Bay.get_by_uuid')
    def test_retrieve_bay_from_service(self,
                                       mock_bay_get_by_uuid):
        self._test_retrieve_bay(objects.Service({}), mock_bay_get_by_uuid)

    @patch('magnum.objects.Bay.get_by_uuid')
    def test_retrieve_bay_from_rc(self,
                                  mock_bay_get_by_uuid):
        self._test_retrieve_bay(objects.ReplicationController({}),
                                mock_bay_get_by_uuid)

    @patch('magnum.objects.Bay.get_by_uuid')
    def test_retrieve_bay_from_container(self,
                                         mock_bay_get_by_uuid):
        self._test_retrieve_bay(objects.Container({}), mock_bay_get_by_uuid)

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_retrieve_baymodel(self, mock_baymodel_get_by_uuid):
        expected_context = 'context'
        expected_baymodel_uuid = 'baymodel_uuid'

        bay = objects.Bay({})
        bay.baymodel_id = expected_baymodel_uuid

        utils.retrieve_baymodel(expected_context, bay)

        mock_baymodel_get_by_uuid.assert_called_once_with(
            expected_context,
            expected_baymodel_uuid)
