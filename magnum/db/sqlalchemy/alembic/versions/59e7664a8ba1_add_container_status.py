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

"""add_container_status

Revision ID: 59e7664a8ba1
Revises: 2b5f24dd95de
Create Date: 2015-05-11 11:33:23.125790

"""

# revision identifiers, used by Alembic.
revision = '59e7664a8ba1'
down_revision = '2b5f24dd95de'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('container',
                  sa.Column('status', sa.String(length=20),
                            nullable=True))
