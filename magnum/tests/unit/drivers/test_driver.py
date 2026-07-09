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

from magnum.common import exception
from magnum.drivers.common import driver
from magnum.tests import base


class TestGetDefaultDriver(base.TestCase):

    def _make_entry_point(self, name):
        ep = mock.MagicMock()
        ep.name = name
        cls = mock.MagicMock()
        return ep, cls

    @mock.patch.object(driver.Driver, 'load_entry_points')
    def test_get_default_driver_from_config(self, mock_load):
        """Returns CONF.drivers.default_driver"""
        self.config(default_driver='heat-k8s', group='drivers')
        mock_load.return_value = iter([self._make_entry_point('heat-k8s')])
        result = driver.Driver.get_default_driver()
        self.assertEqual('heat-k8s', result)
        mock_load.assert_called_once()

    @mock.patch.object(driver.Driver, 'load_entry_points')
    def test_get_default_driver_from_config_not_registered(self, mock_load):
        """Raises ClusterDriverNotSupported when driver is absent."""
        self.config(default_driver='typo-driver', group='drivers')
        mock_load.return_value = iter([self._make_entry_point('heat-k8s')])
        self.assertRaises(exception.ClusterDriverNotSupported,
                          driver.Driver.get_default_driver)

    @mock.patch.object(driver.Driver, 'load_entry_points')
    def test_get_default_driver_first_sorted(self, mock_load):
        """Returns the alphabetically first driver when config is not set."""
        mock_load.return_value = iter([
            self._make_entry_point('zebra_driver'),
            self._make_entry_point('alpha_driver'),
            self._make_entry_point('mango_driver'),
        ])
        result = driver.Driver.get_default_driver()
        self.assertEqual('alpha_driver', result)

    @mock.patch.object(driver.Driver, 'load_entry_points')
    def test_get_default_driver_no_drivers(self, mock_load):
        """Returns None when no drivers are available and config is not set."""
        mock_load.return_value = iter([])
        result = driver.Driver.get_default_driver()
        self.assertIsNone(result)
