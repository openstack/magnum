# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""Add floating_ip_enabled column to baymodel table

Revision ID: b1f612248cab
Revises: 859fb45df249
Create Date: 2016-08-05 15:31:46.203266

"""

# revision identifiers, used by Alembic.
revision = 'b1f612248cab'
down_revision = '859fb45df249'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('baymodel',
                  sa.Column('floating_ip_enabled',
                            sa.Boolean(create_constraint=False),
                            default=True))
