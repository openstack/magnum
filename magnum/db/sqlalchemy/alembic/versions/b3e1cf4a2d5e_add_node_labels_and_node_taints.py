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
"""add node_labels and node_taints to nodegroup

Revision ID: b3e1cf4a2d5e
Revises: d7e6a4d39fe4
Create Date: 2026-05-18 00:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = 'b3e1cf4a2d5e'
down_revision = 'd7e6a4d39fe4'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402

from magnum.db.sqlalchemy import models  # noqa: E402


def upgrade():
    op.add_column(
        'nodegroup',
        sa.Column('node_labels', models.JSONEncodedDict(), nullable=True),
    )
    op.add_column(
        'nodegroup',
        sa.Column('node_taints', models.JSONEncodedList(), nullable=True),
    )
