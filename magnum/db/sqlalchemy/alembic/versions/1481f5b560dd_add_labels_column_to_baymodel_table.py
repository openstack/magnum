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
"""add labels column to baymodel table

Revision ID: 1481f5b560dd
Revises: 3be65537a94a
Create Date: 2015-09-02 22:34:07.590142

"""

# revision identifiers, used by Alembic.
revision = '1481f5b560dd'
down_revision = '3be65537a94a'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('baymodel', sa.Column('labels',
                                        sa.Text(), nullable=True))
