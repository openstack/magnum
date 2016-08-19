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

from oslo_db.sqlalchemy.migration_cli import manager

import magnum.conf

CONF = magnum.conf.CONF
_MANAGER = None


def get_manager():
    global _MANAGER
    if not _MANAGER:
        alembic_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), 'alembic.ini'))
        migrate_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), 'alembic'))
        migration_config = {'alembic_ini_path': alembic_path,
                            'alembic_repo_path': migrate_path,
                            'db_url': CONF.database.connection}
        _MANAGER = manager.MigrationManager(migration_config)

    return _MANAGER


def version():
    """Current database version.

    :returns: Database version
    :rtype: string
    """
    return get_manager().version()


def upgrade(version):
    """Used for upgrading database.

    :param version: Desired database version
    :type version: string
    """
    version = version or 'head'

    get_manager().upgrade(version)


def stamp(revision):
    """Stamps database with provided revision.

    Don't run any migrations.

    :param revision: Should match one from repository or head - to stamp
                     database with most recent revision
    :type revision: string
    """
    get_manager().stamp(revision)


def revision(message=None, autogenerate=False):
    """Creates template for migration.

    :param message: Text that will be used for migration title
    :type message: string
    :param autogenerate: If True - generates diff based on current database
                         state
    :type autogenerate: bool
    """
    return get_manager().revision(message=message, autogenerate=autogenerate)
