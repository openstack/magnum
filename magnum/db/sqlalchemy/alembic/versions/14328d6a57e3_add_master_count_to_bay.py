# Copyright 2015 Huawei Technologies Co.,LTD.
#
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
"""add master count to bay

Revision ID: 14328d6a57e3
Revises: 53882537ac57
Create Date: 2015-07-29 16:00:38.721016

"""

# revision identifiers, used by Alembic.
revision = '14328d6a57e3'
down_revision = '53882537ac57'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('bay',
                  sa.Column('master_count', sa.Integer(), nullable=True))
