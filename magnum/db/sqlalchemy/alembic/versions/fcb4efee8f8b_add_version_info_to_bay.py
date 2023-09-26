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
"""add version info to bay

Revision ID: fcb4efee8f8b
Revises: b1f612248cab
Create Date: 2016-08-22 15:04:32.256811

"""

# revision identifiers, used by Alembic.
revision = 'fcb4efee8f8b'
down_revision = 'b1f612248cab'

from alembic import op  # noqa: E402

from sqlalchemy.types import String  # noqa: E402

import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('bay',
                  sa.Column('coe_version', String(255),
                            nullable=True))
    op.add_column('bay',
                  sa.Column('container_version', String(255),
                            nullable=True))
