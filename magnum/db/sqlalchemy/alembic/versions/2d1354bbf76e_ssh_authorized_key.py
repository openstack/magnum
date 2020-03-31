# Copyright 2015 OpenStack Foundation
# All Rights Reserved.
#
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

"""ssh authorized key

Revision ID: 2d1354bbf76e
Revises: 1afee1db6cd0
Create Date: 2015-03-13 14:05:58.744652

"""

# revision identifiers, used by Alembic.
revision = '2d1354bbf76e'
down_revision = '1afee1db6cd0'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('baymodel', sa.Column('ssh_authorized_key',
                  sa.Text, nullable=True))
