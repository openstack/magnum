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

"""Starter script for magnum-template-manage."""
import operator

from oslo_config import cfg
from oslo_log import log as logging

from magnum.conductor import template_definition as tdef
from magnum.openstack.common import cliutils

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def is_enabled(name):
    return name in CONF.bay.enabled_definitions


def print_rows(rows):
    fields = ['name', 'enabled']
    field_labels = ['Name', 'Enabled']

    if CONF.command.details:
        fields.extend(['server_type', 'os', 'coe'])
        field_labels.extend(['Server_Type', 'OS', 'COE'])
    if CONF.command.paths:
        fields.append('path')
        field_labels.append('Template Path')

    formatters = {key: operator.itemgetter(key) for key in fields}

    cliutils.print_list(rows, fields,
                        formatters=formatters,
                        field_labels=field_labels)


def list_templates():
    rows = []

    for entry_point, cls in tdef.TemplateDefinition.load_entry_points():
        name = entry_point.name
        if ((is_enabled(name) and not CONF.command.disabled) or
                (not is_enabled(name) and not CONF.command.enabled)):
            definition = cls()
            template = dict(name=name, enabled=is_enabled(name),
                            path=definition.template_path)

            if CONF.command.details:
                for bay_type in definition.provides:
                    row = dict()
                    row.update(template)
                    row.update(bay_type)
                    rows.append(row)
            else:
                rows.append(template)

    print_rows(rows)


def add_command_parsers(subparsers):
    parser = subparsers.add_parser('list-templates')
    parser.set_defaults(func=list_templates)

    parser.add_argument('-d', '--details', action='store_true',
                        help='display the bay types provided by each template')
    parser.add_argument('-p', '--paths', action='store_true',
                        help='display the path to each template file')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--enabled', action='store_true',
                       help="display only enabled templates")
    group.add_argument('--disabled', action='store_true',
                       help="display only disabled templates")


def main():
    command_opt = cfg.SubCommandOpt('command',
                                    title='Command',
                                    help='Available commands',
                                    handler=add_command_parsers)
    CONF.register_cli_opt(command_opt)

    CONF(project='magnum')
    CONF.command.func()
