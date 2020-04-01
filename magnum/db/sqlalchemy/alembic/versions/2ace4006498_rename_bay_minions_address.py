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
"""rename-bay-minions-address

Revision ID: 2ace4006498
Revises: 29affeaa2bc2
Create Date: 2015-03-27 15:15:36.309601

"""

# revision identifiers, used by Alembic.
revision = '2ace4006498'
down_revision = '29affeaa2bc2'

from alembic import op  # noqa: E402

from magnum.db.sqlalchemy import models  # noqa: E402


def upgrade():
    op.alter_column('bay', 'minions_address',
                    new_column_name='node_addresses',
                    existing_type=models.JSONEncodedList())
