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

"""change cluster to support nodegroups

Revision ID: 461d798132c7
Revises: ac92cbae311c
Create Date: 2019-02-06 14:32:40.316528

"""

# revision identifiers, used by Alembic.
revision = '461d798132c7'
down_revision = 'ac92cbae311c'

from alembic import op  # noqa: E402

import sqlalchemy as sa  # noqa: E402

from oslo_serialization import jsonutils  # noqa: E402
from oslo_utils import uuidutils  # noqa: E402
from sqlalchemy.types import String  # noqa: E402

from magnum.db.sqlalchemy import models  # noqa: E402


def _handle_json_columns(value, default=None):
    if value is not None:
        return jsonutils.loads(value)
    return default


def upgrade():

    nodegroup = sa.sql.table(
        'nodegroup',
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('uuid', String(length=36), nullable=False),
        sa.Column('name', String(length=255), nullable=False),
        sa.Column('cluster_id', String(length=255), nullable=False),
        sa.Column('project_id', String(length=255), nullable=False),
        sa.Column('docker_volume_size', sa.Integer(), nullable=True),
        sa.Column('labels', models.JSONEncodedDict, nullable=True),
        sa.Column('flavor_id', String(length=255), nullable=True),
        sa.Column('image_id', String(length=255), nullable=True),
        sa.Column('node_addresses', models.JSONEncodedList(), nullable=True),
        sa.Column('node_count', sa.Integer, nullable=True),
        sa.Column('max_node_count', sa.Integer, nullable=True),
        sa.Column('min_node_count', sa.Integer, nullable=True),
        sa.Column('role', String(length=255), nullable=True),
        sa.Column('is_default', sa.Boolean(create_constraint=False))
    )

    connection = op.get_bind()
    # Fetching all required info from existing cluster
    res = connection.execute(sa.text(
        "SELECT "
        "cluster.uuid, "
        "cluster.name, "
        "cluster.project_id, "
        "cluster.docker_volume_size, "
        "cluster.labels, "
        "cluster.master_flavor_id, "
        "cluster.flavor_id, "
        "cluster.node_count, "
        "cluster.master_count, "
        "cluster.node_addresses, "
        "cluster.master_addresses, "
        "cluster_template.master_flavor_id, "
        "cluster_template.flavor_id, "
        "cluster_template.image_id "
        "FROM cluster INNER JOIN cluster_template "
        "ON cluster.cluster_template_id=cluster_template.uuid")
    )

    results = res.fetchall()

    # Create a list containing populated master nodegroups
    master_ngs = [{
        'uuid': uuidutils.generate_uuid(),
        'name': 'default-master',
        'cluster_id': rs[0],
        'project_id': rs[2],
        'docker_volume_size': rs[3],
        'labels': _handle_json_columns(rs[4]),
        'flavor_id': rs[5] or rs[11],
        'image_id': rs[13],
        'node_addresses': _handle_json_columns(rs[10]),
        'node_count': rs[8],
        'role': 'master',
        'min_node_count': 1,
        'is_default': True
    } for rs in results]

    # Create a list containing populated worker nodegroups
    worker_ngs = [{
        'uuid': uuidutils.generate_uuid(),
        'name': 'default-worker',
        'cluster_id': rs[0],
        'project_id': rs[2],
        'docker_volume_size': rs[3],
        'labels': _handle_json_columns(rs[4]),
        'flavor_id': rs[6] or rs[12],
        'image_id': rs[13],
        'node_addresses': _handle_json_columns(rs[9]),
        'node_count': rs[7],
        'role': "worker",
        'min_node_count': 1,
        'is_default': True
    } for rs in results]

    # Insert the populated nodegroups
    op.bulk_insert(nodegroup, master_ngs)
    op.bulk_insert(nodegroup, worker_ngs)

    # Drop the columns from cluster table
    op.drop_column('cluster', 'node_count')
    op.drop_column('cluster', 'node_addresses')
    op.drop_column('cluster', 'master_count')
    op.drop_column('cluster', 'master_addresses')
