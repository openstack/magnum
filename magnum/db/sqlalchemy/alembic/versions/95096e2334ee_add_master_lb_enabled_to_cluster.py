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

from alembic import op
import sqlalchemy as sa

"""add-master_lb_enabled-to-cluster

Revision ID: 95096e2334ee
Revises: c04e925e65c2
Create Date: 2020-06-26 14:33:05.529200

"""

# revision identifiers, used by Alembic.
revision = '95096e2334ee'
down_revision = 'c04e925e65c2'


def upgrade():
    op.add_column('cluster',
                  sa.Column('master_lb_enabled',
                            sa.Boolean(create_constraint=False),
                            default=False))
    # Populate existing cluster with the cluster template_id
    connection = op.get_bind()
    connection.execute(sa.text(
        "UPDATE cluster "
        "INNER JOIN cluster_template "
        "ON cluster_template.uuid=cluster.cluster_template_id "
        "SET cluster.master_lb_enabled=cluster_template.master_lb_enabled "
        "WHERE cluster_template.uuid=cluster.cluster_template_id and "
        "cluster.master_lb_enabled is NULL")
    )
