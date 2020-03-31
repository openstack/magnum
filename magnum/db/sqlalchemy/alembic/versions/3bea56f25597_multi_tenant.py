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

"""Multi Tenant Support

Revision ID: 3bea56f25597
Revises: 2581ebaf0cb2
Create Date: 2015-01-22 22:22:22.150632

"""

# revision identifiers, used by Alembic.
revision = '3bea56f25597'
down_revision = '2581ebaf0cb2'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('bay', sa.Column('project_id', sa.String(length=255),
                  nullable=True))
    op.add_column('bay', sa.Column('user_id', sa.String(length=255),
                  nullable=True))
    op.add_column('baymodel', sa.Column('project_id', sa.String(length=255),
                  nullable=True))
    op.add_column('baymodel', sa.Column('user_id', sa.String(length=255),
                  nullable=True))
    op.add_column('container', sa.Column('project_id', sa.String(length=255),
                  nullable=True))
    op.add_column('container', sa.Column('user_id', sa.String(length=255),
                  nullable=True))
    op.add_column('node', sa.Column('project_id', sa.String(length=255),
                  nullable=True))
    op.add_column('node', sa.Column('user_id', sa.String(length=255),
                  nullable=True))
    op.add_column('pod', sa.Column('project_id', sa.String(length=255),
                  nullable=True))
    op.add_column('pod', sa.Column('user_id', sa.String(length=255),
                  nullable=True))
    op.add_column('service', sa.Column('project_id', sa.String(length=255),
                  nullable=True))
    op.add_column('service', sa.Column('user_id', sa.String(length=255),
                  nullable=True))
    op.add_column('replicationcontroller', sa.Column('project_id',
                  sa.String(length=255), nullable=True))
    op.add_column('replicationcontroller', sa.Column('user_id',
                  sa.String(length=255), nullable=True))
