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
"""added_tags_to_cluster_template

Revision ID: f1d8b0ab8b8d
Revises: 95096e2334ee
Create Date: 2020-08-26 08:38:11.567618

"""

# revision identifiers, used by Alembic.
revision = 'f1d8b0ab8b8d'
down_revision = '95096e2334ee'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('cluster_template',
                  sa.Column('tags',
                            sa.String(length=255), nullable=True))
