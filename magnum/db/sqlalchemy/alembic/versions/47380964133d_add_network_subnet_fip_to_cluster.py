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

"""add-network-subnet-fip-to-cluster

Revision ID: 47380964133d
Revises: 461d798132c7
Create Date: 2019-07-17 13:17:58.760452

"""

# revision identifiers, used by Alembic.
revision = '47380964133d'
down_revision = '461d798132c7'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402
from sqlalchemy.types import String  # noqa: E402


def upgrade():
    op.add_column('cluster', sa.Column('fixed_network',
                  String(255), nullable=True))
    op.add_column('cluster', sa.Column('fixed_subnet',
                  String(255), nullable=True))
    op.add_column('cluster', sa.Column('floating_ip_enabled',
                  sa.Boolean(create_constraint=False),
                  default=False))
