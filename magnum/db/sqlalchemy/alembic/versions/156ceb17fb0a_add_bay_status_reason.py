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
"""add_bay_status_reason

Revision ID: 156ceb17fb0a
Revises: 59e7664a8ba1
Create Date: 2015-05-30 11:34:57.847071

"""

# revision identifiers, used by Alembic.
revision = '156ceb17fb0a'
down_revision = '59e7664a8ba1'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('bay',
                  sa.Column('status_reason', sa.Text, nullable=True))
