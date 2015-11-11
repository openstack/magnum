# Copyright 2015 NEC Corporation.  All rights reserved.
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

from magnum.common import k8s_manifest
from magnum.tests import base


class K8sManifestTestCase(base.TestCase):

    def test_parse_with_json(self):
        port = 6379
        containerPort = 6380
        json_str = '''
        {
          "id": "redis-master",
          "kind": "Service",
          "apiVersion": "v1",
          "port": %d,
          "containerPort": %d,
          "selector": {
            "name": "redis-master"
          },
          "labels": {
            "name": "redis-master"
          }
        }
        ''' % (port, containerPort)

        manifest = k8s_manifest.parse(json_str)
        self.assertIsInstance(manifest, dict)
        self.assertEqual(port, manifest['port'])
        self.assertEqual(containerPort, manifest['containerPort'])

    def test_parse_with_yaml(self):
        port = 6389
        containerPort = 6380
        yaml_str = '''
        id: redis-master
        kind: Service
        port: %d
        containerPort: %d
        selector:
            name: redis-master
        labels:
            name: redis-master
        ''' % (port, containerPort)

        manifest = k8s_manifest.parse(yaml_str)
        self.assertIsInstance(manifest, dict)
        self.assertEqual(port, manifest['port'])
        self.assertEqual(containerPort, manifest['containerPort'])

    def test_parse_invalid_value(self):
        invalid_str = 'aoa89**'

        self.assertRaises(ValueError, k8s_manifest.parse, invalid_str)

    def test_parse_empty_value(self):
        empty_str = ''

        self.assertRaises(ValueError, k8s_manifest.parse, empty_str)

    def test_parse_empty_yaml_response(self):
        blank_str = ' '

        self.assertRaises(ValueError, k8s_manifest.parse, blank_str)

    def test_parse_yaml_error(self):
        invalid_str = "}invalid: y'm'l3!"

        self.assertRaises(ValueError, k8s_manifest.parse, invalid_str)
