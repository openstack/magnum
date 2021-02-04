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

"""adding magnum_service functionality

Revision ID: 27ad304554e2
Revises: 1d045384b966
Create Date: 2015-09-01 18:27:14.371860

"""

# revision identifiers, used by Alembic.
revision = '27ad304554e2'
down_revision = '1d045384b966'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.create_table(
        'magnum_service',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('report_count', sa.Integer(), nullable=False),
        sa.Column('host', sa.String(length=255), nullable=True),
        sa.Column('binary', sa.String(length=255), nullable=True),
        sa.Column('disabled',
                  sa.Boolean(create_constraint=False),
                  nullable=True),
        sa.Column('disabled_reason', sa.String(length=255), nullable=True),
        # 'last_seen_up' has different purpose than 'updated_at'.
        # 'updated_at' refers to any modification of the entry, which can
        # be administrative too, whereas 'last_seen_up' is more related to
        # magnum_service. Modeled after nova/servicegroup
        sa.Column('last_seen_up', sa.DateTime(), nullable=True),
        sa.Column('forced_down',
                  sa.Boolean(create_constraint=False),
                  nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('host', 'binary',
                            name='uniq_magnum_service0host0binary')
    )
