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

"""Starter script for magnum-driver-manage."""
import sys

from cliff import app
from cliff import commandmanager
from cliff import lister

import magnum.conf
from magnum.drivers.common import driver
from magnum import version

CONF = magnum.conf.CONF


class DriverList(lister.Lister):
    """List templates"""

    def _print_rows(self, parsed_args, rows):
        fields = ['name']
        field_labels = ['Name']

        if parsed_args.details:
            fields.extend(['server_type', 'os', 'coe'])
            field_labels.extend(['Server_Type', 'OS', 'COE'])
        if parsed_args.paths:
            fields.append('path')
            field_labels.append('Template Path')
        return field_labels, [tuple([row[field] for field in fields])
                              for row in rows]

    def get_parser(self, prog_name):
        parser = super(DriverList, self).get_parser(prog_name)
        parser.add_argument('-d', '--details',
                            action='store_true',
                            dest='details',
                            help=('display the cluster types provided by '
                                  'each template'))
        parser.add_argument('-p', '--paths',
                            action='store_true',
                            dest='paths',
                            help='display the path to each template file')

        return parser

    def take_action(self, parsed_args):
        rows = []

        for entry_point, cls in driver.Driver.load_entry_points():
            name = entry_point.name
            definition = cls().get_template_definition()
            template = dict(name=name, path=definition.template_path)

            if parsed_args.details:
                for cluster_type in cls().provides:
                    row = dict()
                    row.update(template)
                    row.update(cluster_type)
                    rows.append(row)
            else:
                rows.append(template)
        return self._print_rows(parsed_args, rows)


class DriverCommandManager(commandmanager.CommandManager):
    COMMANDS = {
        "list-drivers": DriverList,
    }

    def load_commands(self, namespace):
        for name, command_class in self.COMMANDS.items():
            self.add_command(name, command_class)


class DriverManager(app.App):
    def __init__(self):
        super(DriverManager, self).__init__(
            description='Magnum Driver Manager',
            version=version.version_info,
            command_manager=DriverCommandManager('magnum'),
            deferred_help=True)


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    CONF([],
         project='magnum',
         version=version.version_info.release_string())
    return DriverManager().run(args)
