# Copyright 2016 - Fujitsu, Ltd.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import mock

from magnum.cmd import api
from magnum.tests import base


class TestMagnumAPI(base.TestCase):

    # NOTE(hieulq): need to mock MagnumObject, otherwise other test cases
    # will be failed because of setting wrong ovo indirection api
    @mock.patch('magnum.objects.base.MagnumObject')
    @mock.patch('wsgiref.simple_server.make_server')
    @mock.patch.object(api, 'api_app')
    @mock.patch('magnum.common.service.prepare_service')
    def test_api(self, mock_prep, mock_app, mock_make, mock_base):
        api.main()

        app = mock_app.load_app.return_value
        server = mock_make.return_value
        mock_prep.assert_called_once_with(mock.ANY)
        mock_app.load_app.assert_called_once_with()
        mock_make.assert_called_once_with(base.CONF.api.host,
                                          base.CONF.api.port, app)
        server.serve_forever.assert_called_once_with()
