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
"""rename-bay-master-address

Revision ID: 29affeaa2bc2
Revises: 2d1354bbf76e
Create Date: 2015-03-25 16:06:08.148629

"""

# revision identifiers, used by Alembic.
revision = '29affeaa2bc2'
down_revision = '2d1354bbf76e'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.alter_column('bay', 'master_address',
                    new_column_name='api_address',
                    existing_type=sa.String(255))
