# Copyright 2016 NEC Corporation.  All rights reserved.
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

from unittest import mock
from unittest.mock import patch

from magnum.common import exception
from magnum.conductor.handlers.common import trust_manager
from magnum.tests import base


class TrustManagerTestCase(base.BaseTestCase):
    def setUp(self):
        super(TrustManagerTestCase, self).setUp()

        osc_class_patcher = patch('magnum.common.clients.OpenStackClients')
        osc_class = osc_class_patcher.start()
        self.addCleanup(osc_class_patcher.stop)

        self.osc = mock.MagicMock()
        osc_class.return_value = self.osc

    @patch('magnum.common.utils.generate_password')
    def test_create_trustee_and_trust(self, mock_generate_password):
        mock_password = "password_mock"
        mock_generate_password.return_value = mock_password
        mock_cluster = mock.MagicMock()
        mock_cluster.uuid = 'mock_cluster_uuid'
        mock_cluster.project_id = 'mock_cluster_project_id'
        mock_keystone = mock.MagicMock()
        mock_trustee = mock.MagicMock()
        mock_trustee.id = 'mock_trustee_id'
        mock_trustee.name = 'mock_trustee_username'
        mock_trust = mock.MagicMock()
        mock_trust.id = 'mock_trust_id'

        self.osc.keystone.return_value = mock_keystone

        mock_keystone.create_trustee.return_value = mock_trustee
        mock_keystone.create_trust.return_value = mock_trust

        trust_manager.create_trustee_and_trust(self.osc, mock_cluster)

        mock_keystone.create_trustee.assert_called_once_with(
            '%s_%s' % (mock_cluster.uuid, mock_cluster.project_id),
            mock_password,
        )
        mock_keystone.create_trust.assert_called_once_with(
            mock_trustee.id,
        )
        self.assertEqual(mock_trustee.name, mock_cluster.trustee_username)
        self.assertEqual(mock_trustee.id, mock_cluster.trustee_user_id)
        self.assertEqual(mock_password, mock_cluster.trustee_password)
        self.assertEqual(mock_trust.id, mock_cluster.trust_id)

    @patch('magnum.common.utils.generate_password')
    def test_create_trustee_and_trust_with_error(self, mock_generate_password):
        mock_cluster = mock.MagicMock()
        mock_generate_password.side_effect = exception.MagnumException()

        self.assertRaises(exception.TrusteeOrTrustToClusterFailed,
                          trust_manager.create_trustee_and_trust,
                          self.osc,
                          mock_cluster)

    def test_delete_trustee_and_trust(self):
        mock_cluster = mock.MagicMock()
        mock_cluster.trust_id = 'trust_id'
        mock_cluster.trustee_user_id = 'trustee_user_id'
        mock_keystone = mock.MagicMock()
        self.osc.keystone.return_value = mock_keystone
        context = mock.MagicMock()

        trust_manager.delete_trustee_and_trust(self.osc, context,
                                               mock_cluster)

        mock_keystone.delete_trust.assert_called_once_with(
            context, mock_cluster
        )
        mock_keystone.delete_trustee.assert_called_once_with(
            'trustee_user_id',
        )

    def test_delete_trustee_and_trust_without_trust_id(self):
        mock_cluster = mock.MagicMock()
        mock_cluster.trust_id = None
        mock_cluster.trustee_user_id = 'trustee_user_id'
        mock_keystone = mock.MagicMock()
        self.osc.keystone.return_value = mock_keystone
        context = mock.MagicMock()

        trust_manager.delete_trustee_and_trust(self.osc, context,
                                               mock_cluster)

        self.assertEqual(0, mock_keystone.delete_trust.call_count)
        mock_keystone.delete_trustee.assert_called_once_with(
            'trustee_user_id',
        )

    def test_delete_trustee_and_trust_without_trustee_user_id(self):
        mock_cluster = mock.MagicMock()
        mock_cluster.trust_id = 'trust_id'
        mock_cluster.trustee_user_id = None
        mock_keystone = mock.MagicMock()
        self.osc.keystone.return_value = mock_keystone
        context = mock.MagicMock()

        trust_manager.delete_trustee_and_trust(self.osc, context, mock_cluster)

        mock_keystone.delete_trust.assert_called_once_with(
            context, mock_cluster
        )
        self.assertEqual(0, mock_keystone.delete_trustee.call_count)
