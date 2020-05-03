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

from unittest import mock

from oslo_concurrency import processutils

from magnum.cmd import api
from magnum.tests import base


# NOTE(hieulq): need to mock MagnumObject, otherwise other test cases
# will be failed because of setting wrong ovo indirection api
@mock.patch('magnum.objects.base.MagnumObject')
class TestMagnumAPI(base.TestCase):

    @mock.patch('werkzeug.serving.run_simple')
    @mock.patch.object(api, 'api_app')
    @mock.patch('magnum.common.service.prepare_service')
    def test_api_http(self, mock_prep, mock_app, mock_run, mock_base):
        api.main()

        app = mock_app.load_app.return_value
        mock_prep.assert_called_once_with(mock.ANY)
        mock_app.load_app.assert_called_once_with()
        workers = processutils.get_worker_count()
        mock_run.assert_called_once_with(base.CONF.api.host,
                                         base.CONF.api.port,
                                         app, processes=workers,
                                         ssl_context=None)

    @mock.patch('werkzeug.serving.run_simple')
    @mock.patch.object(api, 'api_app')
    @mock.patch('magnum.common.service.prepare_service')
    def test_api_http_config_workers(self, mock_prep, mock_app,
                                     mock_run, mock_base):
        fake_workers = 8
        self.config(workers=fake_workers, group='api')
        api.main()

        app = mock_app.load_app.return_value
        mock_prep.assert_called_once_with(mock.ANY)
        mock_app.load_app.assert_called_once_with()
        mock_run.assert_called_once_with(base.CONF.api.host,
                                         base.CONF.api.port,
                                         app, processes=fake_workers,
                                         ssl_context=None)

    @mock.patch('os.path.exists')
    @mock.patch('werkzeug.serving.run_simple')
    @mock.patch.object(api, 'api_app')
    @mock.patch('magnum.common.service.prepare_service')
    def test_api_https_no_cert(self, mock_prep, mock_app, mock_run,
                               mock_exist, mock_base):
        self.config(enabled_ssl=True,
                    ssl_cert_file='tmp_crt',
                    group='api')
        mock_exist.return_value = False

        self.assertRaises(RuntimeError, api.main)
        mock_prep.assert_called_once_with(mock.ANY)
        mock_app.load_app.assert_called_once_with()
        mock_run.assert_not_called()
        mock_exist.assert_called_once_with('tmp_crt')

    @mock.patch('os.path.exists')
    @mock.patch('werkzeug.serving.run_simple')
    @mock.patch.object(api, 'api_app')
    @mock.patch('magnum.common.service.prepare_service')
    def test_api_https_no_key(self, mock_prep, mock_app, mock_run,
                              mock_exist, mock_base):
        self.config(enabled_ssl=True,
                    ssl_cert_file='tmp_crt',
                    ssl_key_file='tmp_key',
                    group='api')
        mock_exist.side_effect = [True, False]

        self.assertRaises(RuntimeError, api.main)
        mock_prep.assert_called_once_with(mock.ANY)
        mock_app.load_app.assert_called_once_with()
        mock_run.assert_not_called()
        mock_exist.assert_has_calls([mock.call('tmp_crt'),
                                     mock.call('tmp_key')])

    @mock.patch('os.path.exists')
    @mock.patch('werkzeug.serving.run_simple')
    @mock.patch.object(api, 'api_app')
    @mock.patch('magnum.common.service.prepare_service')
    def test_api_https(self, mock_prep, mock_app, mock_run,
                       mock_exist, mock_base):
        self.config(enabled_ssl=True,
                    ssl_cert_file='tmp_crt',
                    ssl_key_file='tmp_key',
                    group='api')
        mock_exist.side_effect = [True, True]

        api.main()

        app = mock_app.load_app.return_value
        mock_prep.assert_called_once_with(mock.ANY)
        mock_app.load_app.assert_called_once_with()
        mock_exist.assert_has_calls([mock.call('tmp_crt'),
                                     mock.call('tmp_key')])
        workers = processutils.get_worker_count()
        mock_run.assert_called_once_with(base.CONF.api.host,
                                         base.CONF.api.port, app,
                                         processes=workers,
                                         ssl_context=('tmp_crt', 'tmp_key'))
