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
"""add flavor_id to cluster

Revision ID: 041d9a0f1159
Revises: 04c625aa95ba
Create Date: 2017-07-31 12:46:00.777841

"""

# revision identifiers, used by Alembic.
revision = '041d9a0f1159'
down_revision = '04c625aa95ba'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('cluster', sa.Column('flavor_id',
                                       sa.String(length=255), nullable=True))
