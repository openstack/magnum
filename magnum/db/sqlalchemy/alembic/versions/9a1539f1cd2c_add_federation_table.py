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

""""add federation table

Revision ID: 9a1539f1cd2c
Revises: 041d9a0f1159
Create Date: 2017-08-07 11:47:29.865166

"""

# revision identifiers, used by Alembic.
revision = '9a1539f1cd2c'
down_revision = '041d9a0f1159'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402

from magnum.db.sqlalchemy import models  # noqa: E402


def upgrade():
    op.create_table(
        'federation',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.String(length=255), nullable=True),
        sa.Column('uuid', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('hostcluster_id', sa.String(length=255), nullable=True),
        sa.Column('member_ids', models.JSONEncodedList(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('status_reason', sa.Text(), nullable=True),
        sa.Column('properties', models.JSONEncodedList(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid', name='uniq_federation0uuid')
    )
