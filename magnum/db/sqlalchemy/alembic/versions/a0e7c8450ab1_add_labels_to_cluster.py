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
"""add labels to cluster

Revision ID: a0e7c8450ab1
Revises: bc46ba6cf949
Create Date: 2017-06-12 10:08:05.501441

"""

# revision identifiers, used by Alembic.
revision = 'a0e7c8450ab1'
down_revision = 'aa0cc27839af'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('cluster', sa.Column('labels',
                                       sa.Text(), nullable=True))
