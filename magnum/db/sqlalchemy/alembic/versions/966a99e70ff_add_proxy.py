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
"""add-proxy

Revision ID: 966a99e70ff
Revises: 6f21dc998bb
Create Date: 2015-08-24 11:23:24.262921

"""

# revision identifiers, used by Alembic.
revision = '966a99e70ff'
down_revision = '6f21dc998bb'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('baymodel', sa.Column('http_proxy',
                                        sa.String(length=255), nullable=True))
    op.add_column('baymodel', sa.Column('https_proxy',
                                        sa.String(length=255), nullable=True))
    op.add_column('baymodel', sa.Column('no_proxy',
                                        sa.String(length=255), nullable=True))
