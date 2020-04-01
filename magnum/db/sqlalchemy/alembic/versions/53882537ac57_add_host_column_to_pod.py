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
"""add host column to pod

Revision ID: 53882537ac57
Revises: 1c1ff5e56048
Create Date: 2015-06-25 16:52:47.159887

"""

# revision identifiers, used by Alembic.
revision = '53882537ac57'
down_revision = '1c1ff5e56048'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('pod',
                  sa.Column('host', sa.Text, nullable=True))
