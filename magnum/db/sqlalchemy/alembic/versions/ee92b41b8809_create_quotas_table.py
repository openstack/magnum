# Copyright 2016 Yahoo! Inc. All rights reserved.
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

"""Introduce Quotas

Revision ID: ee92b41b8809
Revises: 5d4caa6e0a42
Create Date: 2016-02-26 18:32:08.992964

"""

# revision identifiers, used by Alembic.
revision = 'ee92b41b8809'
down_revision = '5d4caa6e0a42'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.create_table(
        'quotas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('project_id', sa.String(length=255), nullable=True),
        sa.Column('resource', sa.String(length=255), nullable=True),
        sa.Column('hard_limit', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_unique_constraint(
        "uniq_quotas0project_id0resource",
        "quotas", ["project_id", "resource"])
