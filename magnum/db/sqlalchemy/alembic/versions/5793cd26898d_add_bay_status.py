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
"""Add bay status

Revision ID: 5793cd26898d
Revises: 3bea56f25597
Create Date: 2015-02-09 12:54:09.449948

"""

# revision identifiers, used by Alembic.
revision = '5793cd26898d'
down_revision = '3bea56f25597'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('bay', sa.Column('status', sa.String(length=20),
                  nullable=True))
