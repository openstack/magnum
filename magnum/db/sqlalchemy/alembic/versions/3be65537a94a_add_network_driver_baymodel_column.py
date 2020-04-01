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

"""add_network_driver_baymodel_column

Revision ID: 3be65537a94a
Revises: 4e263f236334
Create Date: 2015-09-03 20:51:54.229436

"""

# revision identifiers, used by Alembic.
revision = '3be65537a94a'
down_revision = '4e263f236334'

from alembic import op  # noqa: E402

from oslo_db.sqlalchemy.types import String  # noqa: E402

import sqlalchemy as sa  # noqa: E402

from sqlalchemy.dialects.mysql import TINYTEXT  # noqa: E402


def upgrade():
    op.add_column('baymodel', sa.Column('network_driver',
                  String(255, mysql_ndb_type=TINYTEXT), nullable=True))
