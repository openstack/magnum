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

"""add cluster distro

Revision ID: 4956f03cabad
Revises: 2d8657c0cdc
Create Date: 2015-04-25 02:17:51.486547

"""

# revision identifiers, used by Alembic.
revision = '4956f03cabad'
down_revision = '2d8657c0cdc'

from alembic import op  # noqa: E402

from sqlalchemy.types import String  # noqa: E402

import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('baymodel', sa.Column('cluster_distro',
                  String(255), nullable=True))
