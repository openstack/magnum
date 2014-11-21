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

import yaml


if hasattr(yaml, 'CSafeLoader'):
    yaml_loader = yaml.CSafeLoader
else:
    yaml_loader = yaml.SafeLoader


if hasattr(yaml, 'CSafeDumper'):
    yaml_dumper = yaml.CSafeDumper
else:
    yaml_dumper = yaml.SafeDumper


def load(s):
    try:
        yml_dict = yaml.load(s, yaml_loader)
    except yaml.YAMLError as exc:
        msg = 'An error occurred during YAML parsing.'
        if hasattr(exc, 'problem_mark'):
            msg += ' Error position: (%s:%s)' % (exc.problem_mark.line + 1,
                                                 exc.problem_mark.column + 1)
        raise ValueError(msg)
    if not isinstance(yml_dict, dict) and not isinstance(yml_dict, list):
        raise ValueError('The source is not a YAML mapping or list.')
    if isinstance(yml_dict, dict) and len(yml_dict) < 1:
        raise ValueError('Could not find any element in your YAML mapping.')
    return yml_dict


def dump(s):
    return yaml.dump(s, Dumper=yaml_dumper)
