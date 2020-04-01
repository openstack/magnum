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

"""create x509keypair table

Revision ID: 421102d1f2d2
Revises: 14328d6a57e3
Create Date: 2015-07-17 13:12:12.653241

"""

# revision identifiers, used by Alembic.
revision = '421102d1f2d2'
down_revision = '14328d6a57e3'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.create_table(
        'x509keypair',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('uuid', sa.String(length=36), nullable=True),
        sa.Column('bay_uuid', sa.String(length=36), nullable=True),
        sa.Column('ca_cert', sa.Text()),
        sa.Column('certificate', sa.Text()),
        sa.Column('private_key', sa.Text()),
        sa.Column('project_id', sa.String(length=255), nullable=True),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_unique_constraint("uniq_x509keypair0uuid",
                                "x509keypair", ["uuid"])
