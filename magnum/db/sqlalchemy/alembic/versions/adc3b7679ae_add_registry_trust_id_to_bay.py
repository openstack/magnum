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

"""add registry_trust_id to bay

Revision ID: adc3b7679ae
Revises: 40f325033343
Create Date: 2015-12-07 15:49:07.622122

"""

# revision identifiers, used by Alembic.
revision = 'adc3b7679ae'
down_revision = '40f325033343'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('bay', sa.Column('registry_trust_id',
                  sa.String(length=255), nullable=True))
