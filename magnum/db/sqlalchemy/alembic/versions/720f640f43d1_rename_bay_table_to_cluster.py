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
"""rename bay table to cluster

Revision ID: 720f640f43d1
Revises: fb03fdef8919
Create Date: 2016-09-02 09:43:41.485934

"""

# revision identifiers, used by Alembic.
revision = '720f640f43d1'
down_revision = 'fb03fdef8919'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.alter_column('bay', 'baymodel_id',
                    new_column_name='cluster_template_id',
                    existing_type=sa.String(255))
    op.alter_column('bay', 'bay_create_timeout',
                    new_column_name='create_timeout',
                    existing_type=sa.Integer())
    op.rename_table('bay', 'cluster')
