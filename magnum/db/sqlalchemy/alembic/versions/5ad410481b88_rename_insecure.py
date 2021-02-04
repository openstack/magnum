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
"""rename-insecure

Revision ID: 5ad410481b88
Revises: 27ad304554e2
Create Date: 2015-09-29 17:51:10.195121

"""

# revision identifiers, used by Alembic.
revision = '5ad410481b88'
down_revision = '27ad304554e2'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.alter_column('baymodel', 'insecure',
                    new_column_name='tls_disabled',
                    existing_type=sa.Boolean(create_constraint=False))
