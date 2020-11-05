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
"""add-insecure-baymodel-attr

Revision ID: 1d045384b966
Revises: 1481f5b560dd
Create Date: 2015-09-23 18:17:10.195121

"""

# revision identifiers, used by Alembic.
revision = '1d045384b966'
down_revision = '1481f5b560dd'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    insecure_column = sa.Column('insecure',
                                sa.Boolean(create_constraint=False),
                                default=False)
    op.add_column('baymodel', insecure_column)
    baymodel = sa.sql.table('baymodel',
                            sa.Column('insecure',
                                      sa.Boolean(create_constraint=False),
                                      default=False))
    op.execute(
        baymodel.update().values({'insecure': True})
    )
