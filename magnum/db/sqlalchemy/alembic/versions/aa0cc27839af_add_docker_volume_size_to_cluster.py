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
"""add docker_volume_size to cluster

Revision ID: aa0cc27839af
Revises: bc46ba6cf949
Create Date: 2017-06-07 13:08:02.853105

"""

# revision identifiers, used by Alembic.
revision = 'aa0cc27839af'
down_revision = 'bc46ba6cf949'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    pass
    op.add_column('cluster', sa.Column('docker_volume_size',
                                       sa.Integer(), nullable=True))
