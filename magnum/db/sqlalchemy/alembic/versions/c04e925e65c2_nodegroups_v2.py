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

"""nodegroups_v2

Revision ID: c04e925e65c2
Revises: 47380964133d
Create Date: 2019-06-14 09:29:58.288671

"""

# revision identifiers, used by Alembic.
revision = 'c04e925e65c2'
down_revision = '47380964133d'

from alembic import op  # noqa: E402

import sqlalchemy as sa  # noqa: E402

from sqlalchemy.types import String  # noqa: E402


def upgrade():
    op.add_column('nodegroup', sa.Column('stack_id', String(255)))
    op.add_column('nodegroup', sa.Column('status', String(20)))
    op.add_column('nodegroup', sa.Column('status_reason', sa.Text()))
    op.add_column('nodegroup', sa.Column('version', String(20)))

    # Populate existing nodegroups with the cluster stack_id
    connection = op.get_bind()

    connection.execute(sa.text(
        "UPDATE nodegroup "
        "INNER JOIN cluster ON nodegroup.cluster_id=cluster.uuid "
        "SET nodegroup.stack_id=cluster.stack_id, "
        "nodegroup.status=cluster.status, nodegroup.version=0 "
        "WHERE nodegroup.cluster_id=cluster.uuid")
    )
