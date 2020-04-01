#
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

"""add keypair to cluster

Revision ID: bc46ba6cf949
Revises: 720f640f43d1
Create Date: 2016-10-03 10:47:08.584635

"""

# revision identifiers, used by Alembic.
revision = 'bc46ba6cf949'
down_revision = '720f640f43d1'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('cluster', sa.Column('keypair', sa.String(length=255),
                                       nullable=True))
