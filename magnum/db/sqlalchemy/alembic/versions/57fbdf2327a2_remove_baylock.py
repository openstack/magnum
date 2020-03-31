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

"""remove baylock

Revision ID: 57fbdf2327a2
Revises: adc3b7679ae
Create Date: 2015-12-17 09:27:18.429773

"""

# revision identifiers, used by Alembic.
revision = '57fbdf2327a2'
down_revision = 'adc3b7679ae'

from alembic import op  # noqa: E402


def upgrade():
    op.drop_table('baylock')
