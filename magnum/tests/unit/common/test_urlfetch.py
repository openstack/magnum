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

from oslo_config import cfg

from magnum.common import urlfetch
from magnum.tests import base


class TestUrlFetch(base.BaseTestCase):

    def test_get_unsupported_scheme(self):
        self.assertRaises(urlfetch.URLFetchError,
                          urlfetch.get,
                          'https://example.com',
                          ('http'))

    @patch('requests.get')
    def test_get(self,
                 mock_request_get):
        mock_reader = mock.MagicMock()
        mock_reader.__iter__.return_value = ['a', 'b', 'c']
        mock_response = mock.MagicMock()
        mock_response.iter_content.return_value = mock_reader
        mock_request_get.return_value = mock_response

        self.assertEqual('abc', urlfetch.get('http://example.com'))

    @patch('requests.get')
    def test_get_exceed_manifest_size(self,
                                      mock_request_get):
        cfg.CONF.set_override("max_manifest_size", 1)

        mock_reader = mock.MagicMock()
        mock_reader.__iter__.return_value = ['a', 'b']
        mock_response = mock.MagicMock()
        mock_response.iter_content.return_value = mock_reader
        mock_request_get.return_value = mock_response

        self.assertRaises(urlfetch.URLFetchError,
                          urlfetch.get,
                          'http://example.com')
