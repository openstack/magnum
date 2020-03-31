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
"""Add fixed_subnet column to baymodel table

Revision ID: e0653b2d5271
Revises: 68ce16dfd341
Create Date: 2016-06-29 14:14:37.862594

"""

# revision identifiers, used by Alembic.
revision = 'e0653b2d5271'
down_revision = '68ce16dfd341'

from alembic import op  # noqa: E402

from oslo_db.sqlalchemy.types import String  # noqa: E402

import sqlalchemy as sa  # noqa: E402

from sqlalchemy.dialects.mysql import TINYTEXT  # noqa: E402


def upgrade():
    op.add_column('baymodel', sa.Column('fixed_subnet',
                                        String(255, mysql_ndb_type=TINYTEXT),
                                        nullable=True))
