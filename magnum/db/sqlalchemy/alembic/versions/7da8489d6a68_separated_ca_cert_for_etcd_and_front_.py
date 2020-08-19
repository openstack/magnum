# Copyright 2020 Catalyst IT LTD.  All rights reserved.
#
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

"""separated CA cert for etcd and front-proxy

Revision ID: 7da8489d6a68
Revises: f1d8b0ab8b8d
Create Date: 2020-08-19 17:18:27.634467

"""

# revision identifiers, used by Alembic.
revision = '7da8489d6a68'
down_revision = 'f1d8b0ab8b8d'

from alembic import op  # noqa: E402  # noqa: E402

from oslo_db.sqlalchemy.types import String  # noqa: E402

import sqlalchemy as sa  # noqa: E402

from sqlalchemy.dialects.mysql import TEXT  # noqa: E402


def upgrade():
    op.add_column('cluster', sa.Column('etcd_ca_cert_ref',
                  String(512, mysql_ndb_type=TEXT),
                  nullable=True))
    op.add_column('cluster', sa.Column('front_proxy_ca_cert_ref',
                  String(512, mysql_ndb_type=TEXT),
                  nullable=True))
