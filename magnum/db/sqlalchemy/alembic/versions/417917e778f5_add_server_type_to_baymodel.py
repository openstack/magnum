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

"""Add server_type column to baymodel

Revision ID: 417917e778f5
Revises: 33ef79969018
Create Date: 2015-10-14 16:21:57.229436

"""

# revision identifiers, used by Alembic.
revision = '417917e778f5'
down_revision = '33ef79969018'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('baymodel', sa.Column('server_type',
                  sa.String(length=255), nullable=True,
                  server_default='vm'))
