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

import mock
import yaml

from magnum.common import yamlutils
from magnum.tests import base


class TestYamlUtils(base.BaseTestCase):

    def test_load_yaml(self):
        yml_dict = yamlutils.load('a: x\nb: y\n')
        self.assertEqual({'a': 'x', 'b': 'y'}, yml_dict)

    def test_load_empty_yaml(self):
        self.assertRaises(ValueError, yamlutils.load, '{}')

    def test_load_empty_list(self):
        yml_dict = yamlutils.load('[]')
        self.assertEqual([], yml_dict)

    def test_load_invalid_yaml_syntax(self):
        self.assertRaises(ValueError, yamlutils.load, "}invalid: y'm'l3!")

    def test_load_invalid_yaml_type(self):
        self.assertRaises(ValueError, yamlutils.load, 'invalid yaml type')

    @mock.patch('magnum.common.yamlutils.yaml.dump')
    def test_dump_yaml(self, dump):
        if hasattr(yaml, 'CSafeDumper'):
            yaml_dumper = yaml.CSafeDumper
        else:
            yaml_dumper = yaml.SafeDumper
        yamlutils.dump('version: 1')
        dump.assert_called_with('version: 1', Dumper=yaml_dumper)
