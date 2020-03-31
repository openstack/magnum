# Copyright 2016 Intel Technologies India Pvt. Ld.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""modify x509keypair table

Revision ID: d072f58ab240
Revises: e647f5931da8
Create Date: 2016-05-27 15:29:22.955268

"""

# revision identifiers, used by Alembic.
revision = 'd072f58ab240'
down_revision = 'ef08a5e057bd'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.drop_column('x509keypair', 'bay_uuid')
    op.drop_column('x509keypair', 'name')
    op.drop_column('x509keypair', 'ca_cert')
    op.add_column('x509keypair', sa.Column('intermediates',
                  sa.Text(), nullable=True))
    op.add_column('x509keypair', sa.Column('private_key_passphrase',
                  sa.Text(), nullable=True))
