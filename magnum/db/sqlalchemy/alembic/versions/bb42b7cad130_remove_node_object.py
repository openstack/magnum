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

"""remove node object

Revision ID: bb42b7cad130
Revises: 05d3e97de9ee
Create Date: 2016-02-02 16:04:36.501547

"""

# revision identifiers, used by Alembic.
revision = 'bb42b7cad130'
down_revision = '05d3e97de9ee'

from alembic import op  # noqa: E402


def upgrade():
    op.drop_table('node')
