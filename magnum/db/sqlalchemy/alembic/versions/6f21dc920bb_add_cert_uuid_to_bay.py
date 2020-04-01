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
"""Add cert_uuuid to bay

Revision ID: 6f21dc920bb
Revises: 966a99e70ff
Create Date: 2015-08-19 13:57:14.863292

"""

# revision identifiers, used by Alembic.
revision = '6f21dc920bb'
down_revision = '966a99e70ff'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column(
        'bay',
        sa.Column('ca_cert_uuid', sa.String(length=36), nullable=True))
    op.add_column(
        'bay',
        sa.Column('magnum_cert_uuid', sa.String(length=36), nullable=True))
