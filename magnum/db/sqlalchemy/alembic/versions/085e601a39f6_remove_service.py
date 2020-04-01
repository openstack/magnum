#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
"""remove service object

Revision ID: 085e601a39f6
Revises: a1136d335540
Create Date: 2016-05-25 12:05:30.790282

"""

# revision identifiers, used by Alembic.
revision = '085e601a39f6'
down_revision = 'a1136d335540'

from alembic import op  # noqa: E402


def upgrade():
    op.drop_table('service')
