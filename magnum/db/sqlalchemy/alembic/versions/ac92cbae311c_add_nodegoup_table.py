# Copyright (c) 2018 European Organization for Nuclear Research.
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

"""add nodegoup table

Revision ID: ac92cbae311c
Revises: cbbc65a86986
Create Date: 2018-09-20 15:26:00.869885

"""

# revision identifiers, used by Alembic.
revision = 'ac92cbae311c'
down_revision = '87e62e3c7abc'

from alembic import op  # noqa: E402

import sqlalchemy as sa  # noqa: E402

from oslo_db.sqlalchemy.types import String  # noqa: E402

from magnum.db.sqlalchemy import models  # noqa: E402


def upgrade():
    op.create_table(
        'nodegroup',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', String(length=36), nullable=False),
        sa.Column('name', String(length=255), nullable=False),
        sa.Column('cluster_id', String(length=255), nullable=False),
        sa.Column('project_id', String(length=255), nullable=False),
        sa.Column('docker_volume_size', sa.Integer(), nullable=True),
        sa.Column('labels', models.JSONEncodedDict, nullable=True),
        sa.Column('flavor_id', String(length=255), nullable=True),
        sa.Column('image_id', String(length=255), nullable=True),
        sa.Column('node_addresses', models.JSONEncodedList(), nullable=True),
        sa.Column('node_count', sa.Integer(), nullable=True),
        sa.Column('max_node_count', sa.Integer(), nullable=True),
        sa.Column('min_node_count', sa.Integer(), nullable=True),
        sa.Column('role', String(length=255), nullable=True),
        sa.Column('is_default',
                  sa.Boolean(create_constraint=False),
                  default=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid', name='uniq_nodegroup0uuid'),
        sa.UniqueConstraint('cluster_id', 'name',
                            name='uniq_nodegroup0cluster_id0name'),
    )
