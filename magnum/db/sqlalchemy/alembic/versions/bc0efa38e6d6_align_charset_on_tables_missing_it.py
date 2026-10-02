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

"""align charset on tables missing it

Revision ID: bc0efa38e6d6
Revises: b3e1cf4a2d5e
Create Date: 2026-10-01 00:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = 'bc0efa38e6d6'
down_revision = 'b3e1cf4a2d5e'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402

from magnum.i18n import _  # noqa: E402

# The 'nodegroup', 'federation' and 'magnum_service' tables were created
# without an explicit charset, unlike every other magnum table (and unlike
# magnum.db.sqlalchemy.models.table_args(), which has always declared
# mysql_charset='utf8' as the intended default for every table). Under
# devstack this goes unnoticed because the whole database is created with
# an explicit CHARACTER SET, so these tables inherit it anyway. Deployment
# tools that create the database without a charset (e.g. kolla-ansible)
# instead leave these three tables to inherit whatever the server's live
# default charset happens to be -- which, on MariaDB 11.6+, is utf8mb4,
# while 'cluster' (created by the very first migration) is permanently
# utf8mb3. Joining nodegroup.cluster_id against cluster.uuid across that
# mismatch raises "Illegal mix of collations".
#
# Rather than hardcoding a charset/collation literal here, align these
# tables to whatever 'cluster' is actually using at migration time

REFERENCE_TABLE = 'cluster'
TABLES_TO_ALIGN = ('nodegroup', 'federation', 'magnum_service')


def _table_collation(bind, table_name):
    row = bind.execute(sa.text(
        "SELECT table_collation FROM information_schema.tables "
        "WHERE table_schema = DATABASE() AND table_name = :table_name"
    ), {"table_name": table_name}).fetchone()
    return row[0] if row is not None else None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != 'mysql':
        # charset/collation are a MySQL/MariaDB-specific concept; sqlite
        # (used in unit tests) has no equivalent.
        return

    row = bind.execute(sa.text(
        "SELECT cs.character_set_name, t.table_collation "
        "FROM information_schema.tables t "
        "JOIN information_schema.collation_character_set_applicability cs "
        "ON t.table_collation = cs.collation_name "
        "WHERE t.table_schema = DATABASE() AND t.table_name = :table_name"
    ), {"table_name": REFERENCE_TABLE}).fetchone()
    if row is None:
        raise RuntimeError(
            _("Could not determine the charset/collation of the '%(ref)s' "
              "table; cannot align %(tables)s to it.") %
            {'ref': REFERENCE_TABLE, 'tables': ', '.join(TABLES_TO_ALIGN)})
    charset, collation = row

    for table in TABLES_TO_ALIGN:
        if _table_collation(bind, table) == collation:
            continue
        bind.execute(sa.text(  # nosec B608
            "ALTER TABLE %s CONVERT TO CHARACTER SET %s COLLATE %s" %
            (table, charset, collation)))
