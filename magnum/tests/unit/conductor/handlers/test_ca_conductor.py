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

from unittest import mock

from magnum.conductor.handlers import ca_conductor
from magnum.tests import base


class TestSignConductor(base.TestCase):
    def setUp(self):
        super(TestSignConductor, self).setUp()
        self.ca_handler = ca_conductor.Handler()

    @mock.patch.object(ca_conductor, 'cert_manager')
    def test_sign_certificate(self, mock_cert_manager):
        mock_cluster = mock.MagicMock()
        mock_certificate = mock.MagicMock()
        mock_certificate.csr = 'fake-csr'
        mock_certificate.ca_cert_type = 'kubernetes'
        mock_cert_manager.sign_node_certificate.return_value = 'fake-pem'

        actual_cert = self.ca_handler.sign_certificate(self.context,
                                                       mock_cluster,
                                                       mock_certificate)

        mock_cert_manager.sign_node_certificate.assert_called_once_with(
            mock_cluster, 'fake-csr', 'kubernetes', context=self.context
        )
        self.assertEqual('fake-pem', actual_cert.pem)

    @mock.patch.object(ca_conductor, 'cert_manager')
    def test_get_ca_certificate(self, mock_cert_manager):
        mock_cluster = mock.MagicMock()
        mock_cluster.uuid = 'cluster-uuid'
        mock_cluster.user_id = 'user-id'
        mock_cluster.project_id = 'project-id'
        mock_cert = mock.MagicMock()
        mock_cert.get_certificate.return_value = 'fake-pem'
        mock_cert_manager.get_cluster_ca_certificate.return_value = mock_cert

        actual_cert = self.ca_handler.get_ca_certificate(self.context,
                                                         mock_cluster)

        self.assertEqual(mock_cluster.uuid, actual_cert.cluster_uuid)
        self.assertEqual(mock_cluster.user_id, actual_cert.user_id)
        self.assertEqual(mock_cluster.project_id, actual_cert.project_id)
        self.assertEqual('fake-pem', actual_cert.pem)
