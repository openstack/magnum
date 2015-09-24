#
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

import json

import six
import yaml

from magnum.i18n import _


if hasattr(yaml, 'CSafeDumper'):
    yaml_dumper = yaml.CSafeDumper
else:
    yaml_dumper = yaml.SafeDumper


def _construct_yaml_str(self, node):
    # Override the default string handling function
    # to always return unicode objects
    return self.construct_scalar(node)


def parse(manifest_str):
    '''Takes a string and returns a dict containing the parsed structure.

    This includes determination of whether the string is using the
    JSON or YAML format.
    '''
    if not manifest_str:
        msg = _("'manifest' can't be empty")
        raise ValueError(msg)
    if manifest_str.startswith('{'):
        manifest = json.loads(manifest_str)
    else:
        try:
            manifest = yaml.safe_load(manifest_str)
        except yaml.YAMLError as yea:
            yea = six.text_type(yea)
            msg = _('Error parsing manifest: %s') % yea
            raise ValueError(msg)
        else:
            if manifest is None:
                msg = _("'manifest' can't be empty")
                raise ValueError(msg)

    if not isinstance(manifest, dict):
        raise ValueError(_('The manifest is not a JSON object '
                           'or YAML mapping.'))
    # TODO(yuanying): check manifest version
    return manifest
