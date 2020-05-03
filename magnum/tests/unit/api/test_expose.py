#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from unittest import mock

from magnum.api import expose
from magnum.tests import base


class TestExpose(base.BaseTestCase):

    @mock.patch('wsmeext.pecan.wsexpose')
    def test_expose_with_rest_content_types(self, mock_pecan):
        self.assertTrue(expose.expose(rest_content_types='json'))
        mock_pecan.assert_called_with(rest_content_types='json')

    @mock.patch('wsmeext.pecan.wsexpose')
    def test_expose_without_rest_content_types(self, mock_pecan):
        self.assertTrue(expose.expose())
        mock_pecan.assert_called_once_with(rest_content_types=('json',))
