# Copyright 2015 Rackspace US, Inc.
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

"""add public column to baymodel table

Revision ID: 2ae93c9c6191
Revises: 5ad410481b88
Create Date: 2015-09-30 15:33:44.514290

"""

# revision identifiers, used by Alembic.
revision = '2ae93c9c6191'
down_revision = '5ad410481b88'

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade():
    op.add_column('baymodel', sa.Column('public',
                                        sa.Boolean(create_constraint=False),
                                        default=False))
