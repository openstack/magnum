# Copyright 2016 OpenStack Foundation
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

"""create trustee for each bay

Revision ID: 5d4caa6e0a42
Revises: bb42b7cad130
Create Date: 2016-02-17 14:16:12.927874

"""

# revision identifiers, used by Alembic.
revision = '5d4caa6e0a42'
down_revision = 'bb42b7cad130'

from alembic import op  # noqa: E402

from oslo_db.sqlalchemy.types import String  # noqa: E402

import sqlalchemy as sa  # noqa: E402

from sqlalchemy.dialects.mysql import TINYTEXT  # noqa: E402


def upgrade():
    op.alter_column('bay', 'registry_trust_id',
                    new_column_name='trust_id',
                    existing_type=sa.String(255))
    op.add_column('bay', sa.Column('trustee_username',
                  String(255, mysql_ndb_type=TINYTEXT),
                  nullable=True))
    op.add_column('bay', sa.Column('trustee_user_id',
                  sa.String(length=255), nullable=True))
    op.add_column('bay', sa.Column('trustee_password',
                  String(255, mysql_ndb_type=TINYTEXT),
                  nullable=True))
