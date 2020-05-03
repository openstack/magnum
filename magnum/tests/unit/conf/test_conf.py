# Copyright 2016 Fujitsu Ltd.
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

import collections
from unittest import mock

from oslo_config import cfg
import six

from magnum.conf import opts
from magnum.tests import base


class ConfTestCase(base.TestCase):

    def test_list_opts(self):
        for group, opt_list in opts.list_opts():
            if isinstance(group, six.string_types):
                self.assertEqual(group, 'DEFAULT')
            else:
                self.assertIsInstance(group, cfg.OptGroup)
            for opt in opt_list:
                self.assertIsInstance(opt, cfg.Opt)

    def test_list_module_name_invalid_mods(self):
        with mock.patch('pkgutil.iter_modules') as mock_mods:
            mock_mods.return_value = [(None, 'foo', True),
                                      (None, 'opts', False)]
            self.assertEqual([], opts._list_module_names())

    def test_list_module_name_valid_mods(self):
        with mock.patch('pkgutil.iter_modules') as mock_mods:
            mock_mods.return_value = [(None, 'foo', False)]
            self.assertEqual(['foo'], opts._list_module_names())

    def test_import_mods_no_func(self):
        modules = ['foo', 'bar']
        with mock.patch('importlib.import_module') as mock_import:
            mock_import.return_value = mock.sentinel.mods
            self.assertRaises(AttributeError, opts._import_modules, modules)
            mock_import.assert_called_once_with('magnum.conf.foo')

    def test_import_mods_valid_func(self):
        modules = ['foo', 'bar']
        with mock.patch('importlib.import_module') as mock_import:
            mock_mod = mock.MagicMock()
            mock_import.return_value = mock_mod
            self.assertEqual([mock_mod, mock_mod],
                             opts._import_modules(modules))
            mock_import.assert_has_calls([mock.call('magnum.conf.foo'),
                                          mock.call('magnum.conf.bar')])

    def test_append_config(self):
        opt = collections.defaultdict(list)
        mock_module = mock.MagicMock()
        mock_conf = mock.MagicMock()
        mock_module.list_opts.return_value = mock_conf
        mock_conf.items.return_value = [('foo', 'bar')]
        opts._append_config_options([mock_module], opt)
        self.assertEqual({'foo': ['b', 'a', 'r']}, opt)
