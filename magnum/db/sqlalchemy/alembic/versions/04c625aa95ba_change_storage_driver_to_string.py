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
"""change storage driver to string

Revision ID: 04c625aa95ba
Revises: 52bcaf58fecb
Create Date: 2017-10-10 15:40:37.553288

"""

# revision identifiers, used by Alembic.
revision = '04c625aa95ba'
down_revision = '52bcaf58fecb'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.alter_column('cluster_template', 'docker_storage_driver',
                    existing_type=sa.Enum('devicemapper', 'overlay',
                                          name='docker_storage_driver'),
                    type_=sa.String(length=512),
                    nullable=True)
