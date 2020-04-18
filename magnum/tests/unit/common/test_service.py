# Copyright (c) 2016 OpenStack Foundation
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

from oslo_log import log as logging

from magnum.common import service
from magnum.tests import base


class TestMagnumService(base.BaseTestCase):

    @mock.patch.object(logging, 'register_options')
    @mock.patch.object(logging, 'setup')
    @mock.patch('magnum.common.config.set_config_defaults')
    @mock.patch('magnum.common.config.parse_args')
    def test_prepare_service_with_argv_not_none(self, mock_parse, mock_set,
                                                mock_setup, mock_reg):
        argv = 'foo'
        mock_parse.side_effect = lambda *args, **kwargs: None

        service.prepare_service(argv)

        mock_parse.assert_called_once_with(argv)
        mock_setup.assert_called_once_with(base.CONF, 'magnum')
        mock_reg.assert_called_once_with(base.CONF)
        mock_set.assert_called_once_with()

    @mock.patch.object(logging, 'register_options')
    @mock.patch.object(logging, 'setup')
    @mock.patch('magnum.common.config.set_config_defaults')
    @mock.patch('magnum.common.config.parse_args')
    def test_prepare_service_with_argv_none(self, mock_parse, mock_set,
                                            mock_setup, mock_reg):
        argv = None
        mock_parse.side_effect = lambda *args, **kwargs: None

        service.prepare_service(argv)

        mock_parse.assert_called_once_with([])
        mock_setup.assert_called_once_with(base.CONF, 'magnum')
        mock_reg.assert_called_once_with(base.CONF)
        mock_set.assert_called_once_with()
