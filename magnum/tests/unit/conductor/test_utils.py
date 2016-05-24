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

    def _test_retrieve_bay(self, expected_bay_uuid, mock_bay_get_by_uuid):
        expected_context = 'context'
        utils.retrieve_bay(expected_context, expected_bay_uuid)
        mock_bay_get_by_uuid.assert_called_once_with(expected_context,
                                                     expected_bay_uuid)

    @patch('magnum.objects.Bay.get_by_uuid')
    def test_retrieve_bay_from_rc(self,
                                  mock_bay_get_by_uuid):
        rc = objects.ReplicationController({})
        rc.bay_uuid = '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'
        self._test_retrieve_bay(rc.bay_uuid,
                                mock_bay_get_by_uuid)

    @patch('magnum.objects.Bay.get_by_uuid')
    def test_retrieve_bay_from_container(self,
                                         mock_bay_get_by_uuid):
        container = objects.Container({})
        container.bay_uuid = '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'
        self._test_retrieve_bay(container.bay_uuid, mock_bay_get_by_uuid)

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

    @patch('oslo_utils.uuidutils.is_uuid_like')
    @patch('magnum.objects.Bay.get_by_name')
    def test_retrieve_bay_uuid_from_name(self, mock_bay_get_by_name,
                                         mock_uuid_like):
        bay = objects.Bay(uuid='5d12f6fd-a196-4bf0-ae4c-1f639a523a52')
        mock_uuid_like.return_value = False
        mock_bay_get_by_name.return_value = bay
        bay_uuid = utils.retrieve_bay_uuid('context', 'fake_name')
        self.assertEqual('5d12f6fd-a196-4bf0-ae4c-1f639a523a52', bay_uuid)

        mock_uuid_like.assert_called_once_with('fake_name')
        mock_bay_get_by_name.assert_called_once_with('context', 'fake_name')

    @patch('oslo_utils.uuidutils.is_uuid_like')
    @patch('magnum.objects.Bay.get_by_name')
    def test_retrieve_bay_uuid_from_uuid(self, mock_bay_get_by_name,
                                         mock_uuid_like):
        bay_uuid = utils.retrieve_bay_uuid(
            'context',
            '5d12f6fd-a196-4bf0-ae4c-1f639a523a52')
        self.assertEqual('5d12f6fd-a196-4bf0-ae4c-1f639a523a52', bay_uuid)
        mock_uuid_like.return_value = True
        mock_bay_get_by_name.assert_not_called()
