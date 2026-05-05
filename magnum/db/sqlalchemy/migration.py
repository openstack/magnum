# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
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

import os

from alembic import command as alembic_command
from alembic import config as alembic_config
from alembic import migration as alembic_migration
from oslo_db.sqlalchemy import enginefacade


def _get_alembic_config():
    ini_path = os.path.join(os.path.dirname(__file__), 'alembic.ini')
    cfg = alembic_config.Config(ini_path)
    cfg.set_main_option(
        'script_location',
        os.path.join(os.path.dirname(__file__), 'alembic'))
    return cfg


def version():
    """Current database version.

    :returns: Database version
    :rtype: string
    """
    engine = enginefacade.writer.get_engine()
    with engine.connect() as conn:
        ctx = alembic_migration.MigrationContext.configure(conn)
        return ctx.get_current_revision()


def upgrade(version):
    """Used for upgrading database.

    :param version: Desired database version
    :type version: string
    """
    version = version or 'head'
    alembic_command.upgrade(_get_alembic_config(), version)


def stamp(revision):
    """Stamps database with provided revision.

    Don't run any migrations.

    :param revision: Should match one from repository or head - to stamp
                     database with most recent revision
    :type revision: string
    """
    alembic_command.stamp(_get_alembic_config(), revision)


def revision(message=None, autogenerate=False):
    """Creates template for migration.

    :param message: Text that will be used for migration title
    :type message: string
    :param autogenerate: If True - generates diff based on current database
                         state
    :type autogenerate: bool
    """
    return alembic_command.revision(
        _get_alembic_config(), message=message, autogenerate=autogenerate)
