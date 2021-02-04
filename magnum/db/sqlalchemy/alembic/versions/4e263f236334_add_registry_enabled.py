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
"""Add registry_enabled

Revision ID: 4e263f236334
Revises: 5518af8dbc21
Create Date: 2015-09-14 18:39:25.871218

"""

# revision identifiers, used by Alembic.
revision = '4e263f236334'
down_revision = '5518af8dbc21'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('baymodel', sa.Column('registry_enabled',
                  sa.Boolean(create_constraint=False), default=False))
