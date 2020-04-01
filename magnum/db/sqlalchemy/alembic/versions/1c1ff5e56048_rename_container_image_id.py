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
"""rename_container_image_id

Revision ID: 1c1ff5e56048
Revises: 156ceb17fb0a
Create Date: 2015-06-18 10:21:40.991734

"""

# revision identifiers, used by Alembic.
revision = '1c1ff5e56048'
down_revision = '156ceb17fb0a'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.alter_column('container', 'image_id',
                    new_column_name='image',
                    existing_type=sa.String(255))
