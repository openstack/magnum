# Copyright 2015 NEC Corporation.  All rights reserved.
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
"""add private network to baymodel

Revision ID: 35cff7c86221
Revises: 3a938526b35d
Create Date: 2015-02-26 05:02:34.260099

"""

# revision identifiers, used by Alembic.
revision = '35cff7c86221'
down_revision = '3a938526b35d'

from alembic import op  # noqa: E402

from sqlalchemy.types import String  # noqa: E402

import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('baymodel', sa.Column('fixed_network',
                  String(255), nullable=True))
