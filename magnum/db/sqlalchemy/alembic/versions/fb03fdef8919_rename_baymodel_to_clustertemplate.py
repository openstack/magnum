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
"""rename_baymodel_to_clustertemplate

Revision ID: fb03fdef8919
Revises: fcb4efee8f8b
Create Date: 2016-08-31 12:40:31.165817

"""

# revision identifiers, used by Alembic.
revision = 'fb03fdef8919'
down_revision = 'fcb4efee8f8b'

from alembic import op  # noqa: E402


def upgrade():
    op.rename_table('baymodel', 'cluster_template')
