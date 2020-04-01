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

"""Add coe column to BayModel

Revision ID: 592131657ca1
Revises: 4956f03cabad
Create Date: 2015-04-17 14:20:17.620995

"""

# revision identifiers, used by Alembic.
revision = '592131657ca1'
down_revision = '4956f03cabad'

from alembic import op  # noqa: E402

from oslo_db.sqlalchemy.types import String  # noqa: E402

import magnum.conf  # noqa: E402
import sqlalchemy as sa  # noqa: E402

from sqlalchemy.dialects.mysql import TINYTEXT  # noqa: E402

CONF = magnum.conf.CONF


def upgrade():
    op.add_column('baymodel', sa.Column('coe', String(255,
                                        mysql_ndb_type=TINYTEXT),
                                        nullable=True))

    baymodel = sa.sql.table('baymodel',
                            sa.sql.column('coe', String(255,
                                          mysql_ndb_type=TINYTEXT)))

    op.execute(
        baymodel.update().values({
            'coe': op.inline_literal("kubernetes")})
    )
