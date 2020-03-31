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
"""add-container-command

Revision ID: e772b2598d9
Revises: 4ea34a59a64c
Create Date: 2015-04-17 18:59:52.770329

"""

# revision identifiers, used by Alembic.
revision = 'e772b2598d9'
down_revision = '4ea34a59a64c'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('container',
                  sa.Column('command', sa.String(length=255),
                            nullable=True))
