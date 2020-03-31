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
"""Add docker storage driver column

Revision ID: a1136d335540
Revises: d072f58ab240
Create Date: 2016-03-07 19:00:28.738486

"""

# revision identifiers, used by Alembic.
revision = 'a1136d335540'
down_revision = 'd072f58ab240'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


docker_storage_driver_enum = sa.Enum('devicemapper', 'overlay',
                                     name='docker_storage_driver')


def upgrade():
    docker_storage_driver_enum.create(op.get_bind(), checkfirst=True)
    op.add_column('baymodel', sa.Column('docker_storage_driver',
                                        docker_storage_driver_enum,
                                        nullable=True))
