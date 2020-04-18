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

from magnum.cmd import driver_manage
from magnum.tests import base


class TestMagnumDriverManage(base.TestCase):

    # Fake entrypoints method
    @staticmethod
    def _fake_entry(num_of_entries):
        while num_of_entries:
            fake_entry = mock.MagicMock()
            fake_entry.name = 'magnum_' + 'test_' + \
                              'foo_' + 'bar'*num_of_entries
            fake_cls = mock.MagicMock()
            fake_definition = fake_cls()
            fake_definition.provides = [{'coe': 'foo', 'os': 'bar',
                                         'server_type': 'test'}]
            fake_definition.get_template_definition.return_value = \
                mock.MagicMock(template_path='fake_path')
            yield fake_entry, fake_cls
            num_of_entries -= 1

    @mock.patch.object(driver_manage.DriverManager, 'run')
    @mock.patch('sys.argv', ['foo', 'bar'])
    def test_none_arg(self, mock_run):
        args = None
        driver_manage.main(args)
        mock_run.assert_called_once_with(['bar'])

    # NOTE(hieulq): we fake the entrypoints then we need to mock the cliff
    # produce_output in order to assert with fake value
    @mock.patch('magnum.cmd.driver_manage.DriverList.produce_output')
    @mock.patch('magnum.drivers.common.driver.Driver')
    def test_correct_arg_with_details_and_path(self, mock_driver,
                                               mock_produce):
        args = ['list-drivers', '-d', '-p']
        mock_driver.load_entry_points.return_value = self._fake_entry(1)
        driver_manage.main(args)
        mock_driver.load_entry_points.assert_called_once_with()
        mock_produce.assert_called_once_with(mock.ANY, mock.ANY,
                                             [('magnum_test_foo_bar',
                                               'test',
                                               'bar', 'foo', 'fake_path')])

    # NOTE(hieulq): we fake the entrypoints then we need to mock the cliff
    # produce_output in order to assert with fake value
    @mock.patch('magnum.cmd.driver_manage.DriverList.produce_output')
    @mock.patch('magnum.drivers.common.driver.Driver')
    def test_correct_arg_without_details_and_path(self, mock_driver,
                                                  mock_produce):
        args = ['list-drivers']
        mock_driver.load_entry_points.return_value = self._fake_entry(1)
        driver_manage.main(args)
        mock_driver.load_entry_points.assert_called_once_with()
        mock_produce.assert_called_once_with(mock.ANY, mock.ANY,
                                             [('magnum_test_foo_bar',)])
