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

"""add volume driver

Revision ID: 05d3e97de9ee
Revises: 57fbdf2327a2
Create Date: 2016-01-12 06:21:24.880838

"""

# revision identifiers, used by Alembic.
revision = '05d3e97de9ee'
down_revision = '57fbdf2327a2'

from alembic import op  # noqa: E402

from sqlalchemy.types import String  # noqa: E402

import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('baymodel', sa.Column('volume_driver',
                  String(255), nullable=True))
