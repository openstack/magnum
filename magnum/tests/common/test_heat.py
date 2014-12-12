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

from heatclient import client as heatclient
import mock

from magnum.common import heat
from magnum.common import keystone
from magnum.tests import base


class HeatTestCase(base.TestCase):

    @mock.patch.object(heatclient, 'Client')
    @mock.patch.object(keystone, 'get_service_url')
    @mock.patch.object(keystone, 'get_keystone_url')
    def test_heat(self, mock_auth, mock_url, mock_call):
        mock_auth.return_value = "keystone_url"
        con = mock.MagicMock()
        con.tenant = "b363706f891f48019483f8bd6503c54b"
        con.auth_token = "3bcc3d3a03f44e3d8377f9247b0ad155"
        con.auth_url = "keystone_url"
        mock_url.return_value = "url_from_keystone"

        heat.get_client(con)
        mock_call.assert_called_once_with(
            '1', 'url_from_keystone', username=None,
            cert_file=None, token='3bcc3d3a03f44e3d8377f9247b0ad155',
            auth_url='keystone_url', ca_file=None, key_file=None,
            password=None, insecure=False)
        mock_url.assert_called_once_with(service_type='orchestration',
                                         endpoint_type='publicURL')