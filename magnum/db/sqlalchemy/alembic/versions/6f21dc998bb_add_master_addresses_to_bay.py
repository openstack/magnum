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

"""Add master_addresses to bay

Revision ID: 6f21dc998bb
Revises: 421102d1f2d2
Create Date: 2015-08-20 13:57:14.863292

"""

# revision identifiers, used by Alembic.
revision = '6f21dc998bb'
down_revision = '421102d1f2d2'

from alembic import op  # noqa: E402
from magnum.db.sqlalchemy import models  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column(
        'bay',
        sa.Column('master_addresses',
                  models.JSONEncodedList(),
                  nullable=True)
    )
