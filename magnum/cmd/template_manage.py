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
import sys

from cliff import app
from cliff import commandmanager
from cliff import lister
from oslo_config import cfg

from magnum.conductor import template_definition as tdef
from magnum import version

CONF = cfg.CONF


def is_enabled(name):
    return name in CONF.bay.enabled_definitions


class TemplateList(lister.Lister):
    """List templates"""

    def _print_rows(self, parsed_args, rows):
        fields = ['name', 'enabled']
        field_labels = ['Name', 'Enabled']

        if parsed_args.details:
            fields.extend(['server_type', 'os', 'coe'])
            field_labels.extend(['Server_Type', 'OS', 'COE'])
        if parsed_args.paths:
            fields.append('path')
            field_labels.append('Template Path')
        return field_labels, [tuple([row[field] for field in fields])
                              for row in rows]

    def get_parser(self, prog_name):
        parser = super(TemplateList, self).get_parser(prog_name)
        parser.add_argument('-d', '--details',
                            action='store_true',
                            dest='details',
                            help=('display the bay types provided by '
                                  'each template'))
        parser.add_argument('-p', '--paths',
                            action='store_true',
                            dest='paths',
                            help='display the path to each template file')

        group = parser.add_mutually_exclusive_group()
        group.add_argument('--enabled', action='store_true', dest='enabled',
                           help="display only enabled templates")
        group.add_argument('--disabled', action='store_true', dest='disabled',
                           help="display only disabled templates")

        return parser

    def take_action(self, parsed_args):
        rows = []

        for entry_point, cls in tdef.TemplateDefinition.load_entry_points():
            name = entry_point.name
            if ((is_enabled(name) and not parsed_args.disabled) or
                    (not is_enabled(name) and not parsed_args.enabled)):
                definition = cls()
                template = dict(name=name, enabled=is_enabled(name),
                                path=definition.template_path)

                if parsed_args.details:
                    for bay_type in definition.provides:
                        row = dict()
                        row.update(template)
                        row.update(bay_type)
                        rows.append(row)
                else:
                    rows.append(template)

        return self._print_rows(parsed_args, rows)


class TemplateCommandManager(commandmanager.CommandManager):
    COMMANDS = {
        "list-templates": TemplateList,
    }

    def load_commands(self, namespace):
        for name, command_class in self.COMMANDS.items():
            self.add_command(name, command_class)


class TemplateManager(app.App):
    def __init__(self):
        super(TemplateManager, self).__init__(
            description='Magnum Template Manager',
            version=version.version_info,
            command_manager=TemplateCommandManager(None),
            deferred_help=True)


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    return TemplateManager().run(args)
