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

"""add bay uuid

Revision ID: 2d8657c0cdc
Revises: e772b2598d9
Create Date: 2015-04-22 16:59:06.799384

"""

# revision identifiers, used by Alembic.
revision = '2d8657c0cdc'
down_revision = 'e772b2598d9'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('container', sa.Column('bay_uuid',
                  sa.String(length=255), nullable=True))
