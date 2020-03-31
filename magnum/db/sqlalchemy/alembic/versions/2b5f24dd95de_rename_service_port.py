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
"""rename service port

Revision ID: 2b5f24dd95de
Revises: 592131657ca1
Create Date: 2015-04-29 05:52:52.204095

"""

# revision identifiers, used by Alembic.
revision = '2b5f24dd95de'
down_revision = '3b6c4c42adb4'

from alembic import op  # noqa: E402

from magnum.db.sqlalchemy import models  # noqa: E402


def upgrade():
    op.alter_column('service', 'port',
                    new_column_name='ports',
                    existing_type=models.JSONEncodedList())
