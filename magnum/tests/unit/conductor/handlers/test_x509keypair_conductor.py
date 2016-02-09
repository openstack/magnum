# Copyright 2015 NEC Corporation.  All rights reserved.
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

import mock
from mock import patch

from magnum.conductor.handlers import x509keypair_conductor
from magnum import objects
from magnum.tests import base


class TestX509KeyPairConductor(base.TestCase):
    def setUp(self):
        super(TestX509KeyPairConductor, self).setUp()
        self.x509keypair_handler = x509keypair_conductor.Handler()

    def test_x509keypair_create(self):
        expected_x509keypair = objects.X509KeyPair({})
        expected_x509keypair.create = mock.MagicMock()

        self.x509keypair_handler.x509keypair_create(self.context,
                                                    expected_x509keypair)
        expected_x509keypair.create.assert_called_once_with(self.context)

    @patch('magnum.objects.X509KeyPair.get_by_uuid')
    def test_x509keypair_delete(self, mock_x509keypair_get_by_uuid):
        mock_x509keypair = mock.MagicMock()
        mock_x509keypair.name = 'test-x509keypair'
        mock_x509keypair.uuid = 'test-uuid'
        mock_x509keypair_get_by_uuid.return_value = mock_x509keypair
        self.x509keypair_handler.x509keypair_delete(self.context, "test-uuid")
        mock_x509keypair.destroy.assert_called_once_with(self.context)
