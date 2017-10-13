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

"""Starter script for magnum-db-manage."""

from oslo_config import cfg
from oslo_log import log as logging

from magnum.db import migration


CONF = cfg.CONF


def do_version():
    print('Current DB revision is %s' % migration.version())


def do_upgrade():
    migration.upgrade(CONF.command.revision)


def do_stamp():
    migration.stamp(CONF.command.revision)


def do_revision():
    migration.revision(message=CONF.command.message,
                       autogenerate=CONF.command.autogenerate)


def add_command_parsers(subparsers):
    parser = subparsers.add_parser('version')
    parser.set_defaults(func=do_version)

    parser = subparsers.add_parser('upgrade')
    parser.add_argument('revision', nargs='?')
    parser.set_defaults(func=do_upgrade)

    parser = subparsers.add_parser('stamp')
    parser.add_argument('revision')
    parser.set_defaults(func=do_stamp)

    parser = subparsers.add_parser('revision')
    parser.add_argument('-m', '--message')
    parser.add_argument('--autogenerate', action='store_true')
    parser.set_defaults(func=do_revision)


command_opt = cfg.SubCommandOpt('command',
                                title='Command',
                                help='Available commands',
                                handler=add_command_parsers)


def main():
    logging.register_options(CONF)
    CONF.register_cli_opt(command_opt)

    CONF(project='magnum')
    CONF.command.func()
